from utilities import (
    load_env,
    init_sql,
    find_files,
    ollama_helper,
    embeddings_helper,
    search_result_print,
)
import argparse
import logging
import sqlite3
from hashlib import sha256
from os.path import exists, isfile
from pathlib import Path

import tqdm

import fastapi
from fastapi.staticfiles import StaticFiles
import uvicorn


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("classifier")


class ContextManager():
    def __init__(self, database_file: str):
        logger.info("Initializing database context for %s", database_file)
        self.database_file = database_file
        self.con = self.__establish_connection()
        self.cur = self.__obtain_cursor()

    def __establish_connection(self) -> sqlite3.Connection:
        logger.debug("Connecting to database %s", self.database_file)
        return sqlite3.connect(self.database_file)

    def __obtain_cursor(self) -> sqlite3.Cursor:
        logger.debug("Creating cursor for database %s", self.database_file)
        return self.con.cursor()

    def __exit__(self):
        logger.debug("Closing database connection for %s", self.database_file)
        self.con.close()

    def save_classifications(self, path: str, hash: str, description: str) -> bool:
        if not path or not description or not hash:
            logger.error("Missing required values for classification save. path=%s hash_present=%s description_present=%s", bool(path), bool(hash), bool(description))
            raise ValueError("missing required classification values")

        filename: str = path.split("/")[-1]
        logger.debug("Saving classification for file %s", filename)
        try:
            self.cur.execute("INSERT INTO classifications(filename, hash, description) VALUES(?, ?, ?)", (filename, hash, description))
            #logger.info("Saved classification for %s", filename)
        except Exception as e:
            logger.exception("Failed to save classification for %s", filename)
            return False
        return True


def embed_descriptions(sql_ctx: ContextManager):
    logger.info("Starting embedding step for stored descriptions")
    sql_ctx.cur.execute(
        """
        SELECT COUNT(*)
        FROM classifications c
        WHERE NOT EXISTS (
            SELECT 1
            FROM embeddings e
            WHERE e.classification_id = c.id
        )
        """
    )
    total: int = sql_ctx.cur.fetchone()[0]
    logger.info("Found %s classifications to embed", total)
    write_cursor: sqlite3.Cursor = sql_ctx.con.cursor()

    sql_ctx.cur.execute(
        """
        SELECT id, description
        FROM classifications c
        WHERE NOT EXISTS (
            SELECT 1
            FROM embeddings e
            WHERE e.classification_id = c.id
        )
        """
    )

    embedded_count = 0
    helper = embeddings_helper.Helper()

    for classification_id, description in tqdm.tqdm(sql_ctx.cur, total=total):
        chunks = description.split(".")
        for chunk in chunks:
            embedding: bytes = helper.generate_embedding(chunk)
            write_cursor.execute("INSERT INTO embeddings(classification_id, embedding) VALUES(?,?)", (classification_id, embedding,))
        embedded_count += 1
    sql_ctx.con.commit()

    write_cursor.close()
    logger.info("Completed embedding step for %s classifications", embedded_count)


def main(args: argparse.Namespace):
    if not args.database:
        logger.error("Database argument was not provided")
        raise ValueError("database argument not provided")
    if not args.dir and not args.file:
        logger.error("Image directory or file argument was not provided")
        raise ValueError("Image directory or file argument not provided")

    sql_ctx = ContextManager(args.database)
    env_vars: dict = load_env.get_env()
    logger.info("Initializing SQL schema")
    init_sql.init(sql_ctx.cur)

    logger.info("Priming Ollama model")
    ollama_helper.test_and_prime_model(
        env_vars.get("system_prompt") or "describe what's in the image in as much detail as possible",
        args.model,
    )
    files: list = []
    if args.file and isfile(args.file):
        files.append(args.file)
    else:
        files = find_files.files(args.dir)
    logger.info("Discovered %s files to process from %s", len(files), args.dir)
    pbar = tqdm.tqdm(files)
    sql_ctx.cur.execute("begin transaction")
    logger.info("Started database transaction")

    processed_count = 0
    for file in pbar:
        if not exists(file):
            logger.warning("File does not exist, skipping: %s", file)
            continue

        hash: str = ""
        try:
            with open(file, "rb") as fd:
                hash = str(sha256(fd.read()).digest())
        except PermissionError:
            logger.exception("Unable to open file due to insufficient permissions: %s", file)
            continue

        sql_ctx.cur.execute("SELECT 1 FROM classifications WHERE hash = ? LIMIT 1", (hash,))
        if sql_ctx.cur.fetchone():
            logger.info("Skipping %s because its hash already exists in the database", file)
            continue

        try:
            response: str = ollama_helper.query_model_with_image(
                env_vars.get("system_prompt") or "describe what's in the image in as much detail as possible",
                "Describe this image",
                file,
                args.model,
            )
            logger.debug("Received model response length %s for %s", len(response), file)

            saved = sql_ctx.save_classifications(file, hash, response)
            if saved:
                processed_count += 1
            else:
                logger.warning("Classification save failed for %s", file)
            
        except Exception as e:
            logger.exception("Unexpected error while processing %s, saving with empty description", file)
            saved = sql_ctx.save_classifications(file, hash, '')

        if processed_count == 20:
            sql_ctx.cur.execute("commit")
            sql_ctx.cur.execute("begin transaction")
            logger.info("Committed 20 entries to database.")
            processed_count = 0

    sql_ctx.cur.execute("commit")
    logger.info("Committed database transaction. Processed %s files", processed_count)

    embed_descriptions(sql_ctx)

def search(args: argparse.Namespace):
    if not args.database:
        logger.error("Database argument was not provided")
        raise ValueError("database argument not provided")

    sql_ctx = ContextManager(args.database)
    helper = embeddings_helper.Helper()
    embedding: bytes = helper.generate_embedding(args.search)
    stored_embeddings: list = sql_ctx.cur.execute("SELECT * FROM embeddings").fetchall()
    best_scores: dict[int, float] = {}

    for embed in stored_embeddings:
        similarity: float = helper.cosign_similarity_compare(embedding, embed[2])
        if similarity >= 0.4:
            classification_id = embed[1]
            best_scores[classification_id] = max(
                best_scores.get(classification_id, 0.0),
                similarity,
            )

    results = sorted(best_scores.items(), key=lambda item: item[1], reverse=True)

    files: list[tuple[str, str, float]] = []
    if results:
        classification_ids = [classification_id for classification_id, _ in results]
        placeholders = ",".join("?" for _ in classification_ids)
        files_by_id = {
            classification_id: (filename, description)
            for classification_id, filename, description in sql_ctx.cur.execute(
                f"SELECT id, filename, description FROM classifications WHERE id IN ({placeholders})",
                classification_ids,
            ).fetchall()
        }
        files = [
            (*files_by_id[classification_id], similarity)
            for classification_id, similarity in results
            if classification_id in files_by_id
        ]

    deduped_files: list[tuple[str, str, float]] = []
    files_by_filename: dict[str, tuple[str, float]] = {}
    for filename, description, similarity in files:
        if filename in files_by_filename:
            existing_description, existing_similarity = files_by_filename[filename]
            if description and existing_description:
                description = f"{existing_description} | {description}"
            elif description:
                description = description
            else:
                description = existing_description
            files_by_filename[filename] = (
                description,
                max(existing_similarity, similarity),
            )
        else:
            files_by_filename[filename] = (description or "", similarity)

    deduped_files = [
        (filename, description, similarity)
        for filename, (description, similarity) in files_by_filename.items()
    ]
    deduped_files.sort(key=lambda item: item[2], reverse=True)

    sql_ctx.cur.close()
    sql_ctx.con.close()


    return deduped_files


def serve_api(args: argparse.Namespace):
    if not args.database:
        logger.error("Database argument was not provided")
        raise ValueError("database argument not provided")

    sql_ctx: ContextManager = ContextManager(args.database)

    app = fastapi.FastAPI()
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/api/search")
    async def search_endpoint(query: str):
        results = search(argparse.Namespace(database=args.database, search=query))
        images = [
            {"filename": filename, "description": description, "similarity": similarity}
            for filename, description, similarity in results
        ]
        return {"images": images}

    @app.get("/api/images")
    async def get_images(query: str | None = '0'):
        sql_ctx.cur.execute("SELECT * FROM classifications WHERE id > ? LIMIT 20", (query,))
        images = sql_ctx.cur.fetchall()
        images = [{"id": img[0], "filename": img[1], "description": img[3]} for img in images]
        return {"images": images}

    @app.get("/")
    async def root():
        return fastapi.responses.FileResponse(static_dir / "index.html")

    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Hermes",
        description="Image classifier based on python and ollama",
    )
    parser.add_argument("--database", help="database file to store descriptions and embeddings")
    parser.add_argument("--dir", help="directory to index")
    parser.add_argument("--model", default="llama3.2-vision:11b")
    parser.add_argument("--search", help="search for a specific file, only works after running the indexer")
    parser.add_argument("--file", help="single file to be processed")
    parser.add_argument("--serve", action="store_true", help="run the API server")
    args: argparse.Namespace = parser.parse_args()

    try:
        if args.search:
            search_result_print.print_search_results(search(args))
        elif args.serve:
            serve_api(args)
        else:
            main(args)
    except Exception as e:
        logger.exception("Unhandled exception during classifier run")
        exit(1)
