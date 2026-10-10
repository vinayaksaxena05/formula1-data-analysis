import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

load_dotenv(ENV_PATH)


# host / database / user are always needed; port falls back to the libpq
# default (5432) and password may legitimately be empty for local trust
# auth, so neither is required here.
_REQUIRED_VARS = ("PG_HOST", "PG_DATABASE", "PG_USER")


def get_connection():
    """Open a PostgreSQL connection from the PG_* variables in the project .env."""

    missing = [name for name in _REQUIRED_VARS if not os.getenv(name)]

    if missing:
        raise RuntimeError(
            "Missing required PostgreSQL environment variable(s): "
            f"{', '.join(missing)}. Expected them in {ENV_PATH}."
        )

    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        database=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
    )


if __name__ == "__main__":
    conn = get_connection()
    print("PostgreSQL connection successful")
    conn.close()
