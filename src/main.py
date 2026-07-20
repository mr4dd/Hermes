from utilities import load_env, init_sql, find_files, ollama_helper, embeddings_helper
import argparse
import logging
import sqlite3
import traceback
from hashlib import sha256
from os.path import exists

import tqdm

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
            logger.info("Saved classification for %s", filename)
        except Exception as e:
            logger.exception("Failed to save classification for %s", filename)
            return False
        return True


def embed_descriptions(sql_ctx: ContextManager):
    logger.info("Starting embedding step for stored descriptions")
    sql_ctx.cur.execute("SELECT COUNT(*) FROM classifications")
    total: int = sql_ctx.cur.fetchone()[0]
    logger.info("Found %s classifications to embed", total)
    write_cursor: sqlite3.Cursor = sql_ctx.con.cursor()

    sql_ctx.cur.execute("SELECT id, description FROM classifications")

    embedded_count = 0
    for classification_id, description in tqdm.tqdm(sql_ctx.cur, total=total):
        logger.debug("Embedding description for classification id %s", classification_id)
        embedding: bytes = embeddings_helper.generate_embedding(description=description)
        write_cursor.execute("INSERT INTO embeddings(classification_id, embedding) VALUES(?,?)", (classification_id, embedding,))
        sql_ctx.con.commit()
        embedded_count += 1

    write_cursor.close()
    logger.info("Completed embedding step for %s classifications", embedded_count)


def main(args: argparse.Namespace):
    if not args.database:
        logger.error("Database argument was not provided")
        raise ValueError("database argument not provided")
    if not args.dir:
        logger.error("Image directory argument was not provided")
        raise ValueError("Image directory argument not provided")

    sql_ctx = ContextManager(args.database)
    env_vars: dict = load_env.get_env()
    logger.info("Initializing SQL schema")
    init_sql.init(sql_ctx.cur)

    logger.info("Priming Ollama model")
    ollama_helper.test_and_prime_model(
        env_vars.get("system_prompt") or "describe what's in the image in as much detail as possible",
        args.model,
    )

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
            logger.exception("Unexpected error while processing %s", file)
    sql_ctx.cur.execute("commit")
    logger.info("Committed database transaction. Processed %s files", processed_count)

    embed_descriptions(sql_ctx)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Hermes",
        description="Image classifier based on python and ollama",
    )
    parser.add_argument("--database")
    parser.add_argument("--dir")
    parser.add_argument("--model", default="llama3.2-vision:11b")
    args: argparse.Namespace = parser.parse_args()

    try:
        main(args)
    except Exception as e:
        logger.exception("Unhandled exception during classifier run")
        exit(1)