from dotenv import load_dotenv
from os import getenv

def get_env() -> dict:
    load_dotenv()
    variables = {"system_prompt": getenv("SYSTEM_PROMPT")}
    return variables