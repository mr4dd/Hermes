from utilities import load_env, init_sql
from sys import argv
import sqlite3
import argparse

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

    def save_classifications(self, filename: str, hash: str, description: str):
        pass

def main(args: argparse.Namespace):
    if not args.database:
        raise ValueError
    sql_ctx = ContextManager(args.database)


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
    except ValueError:
        print("database argument not provided")
        exit()