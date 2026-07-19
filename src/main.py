from utilities import load_env, init_sql, find_files, ollama_helper
from sys import argv
import sqlite3
import argparse
from hashlib import sha256
import tqdm
from os.path import exists

class ContextManager():
    def __init__(self, database_file: str):
        self.database_file = database_file
        self.con = self.__establish_connection()
        self.cur = self.__obtain_cursor()
    
    def __establish_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_file)
    
    def __obtain_cursor(self) -> sqlite3.Cursor:
        return self.con.cursor()
    
    def __exit__(self):
        self.con.close()

    def save_classifications(self, path: str, hash: str, description: str) -> bool:
        if not path or not description or not hash:
            raise ValueError
        
        filename: str = path.split("/")[-1]
        try:
            self.cur.execute("INSERT INTO classifications(filename, hash, description) VALUES(?, ?, ?)", (filename, hash, description))
        except Exception as e:
            print(f"an error occured while processing file {filename}: ", e)
            return False
        return True


def main(args: argparse.Namespace):
    if not args.database:
        raise ValueError
    
    sql_ctx = ContextManager(args.database)
    env_vars: dict = load_env.get_env()
    init_sql.init(sql_ctx.cur)
    ollama_helper.test_and_prime_model(
        env_vars.get("system_prompt") or "describe what's in the image in as much detail as possible",
        "gemma4:12b")

    files = find_files.files(args.dir)
    pbar = tqdm.tqdm(files)
    sql_ctx.cur.execute("begin transaction")
    for file in pbar:
        if not exists(file):
            print(f"file {file} does not exist")
            continue 
        hash: str = ""
        try:
            with open(file, "rb") as fd:
                hash = str(sha256(fd.read()).digest())
        except PermissionError:
            print(f"Unable to open file {file} due to insufficient permissions")

        response: str = ollama_helper.query_model_with_image(
            env_vars.get("system_prompt") or "describe what's in the image in as much detail as possible",
            "Describe this image",
            file,
            "gemma4:12b"
            )
        
        sql_ctx.save_classifications(file, hash, response)
    sql_ctx.cur.execute("commit")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Prometheus",
        description="Image classifier based on python and ollama"
    )
    parser.add_argument("--database")
    parser.add_argument("--dir")
    args: argparse.Namespace = parser.parse_args()


    try:
        main(args)
    except Exception as e:
        print("Unknown exception occured: ", e)
        exit()