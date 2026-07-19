import sqlite3

def init(cur: sqlite3.Cursor) -> bool:
    with open("schema.sql", "r") as sqf:
        try:
            cur.execute(sqf.read())
        except Exception as e:
            print(e)
            return False
    return True