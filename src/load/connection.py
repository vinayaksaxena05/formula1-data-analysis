import psycopg2
from dotenv import load_dotenv
import os
from pathlib import Path

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

def get_connection():
    conn = psycopg2.connect(
        host = os.getenv("PG_HOST"),
        port = os.getenv("PG_PORT"),
        database = os.getenv("PG_DATABASE"),
        user = os.getenv("PG_USER"),
        password = os.getenv("PG_PASSWORD")
    )

    return conn

if __name__ == "__main__":
    conn = get_connection()
    print("PostGres connected")
    conn.close()
