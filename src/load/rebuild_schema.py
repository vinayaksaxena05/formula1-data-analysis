"""Drop every warehouse table and view so the create scripts can rebuild them.

Run this once when a schema change (a new column, a changed constraint)
means ``CREATE TABLE IF NOT EXISTS`` in ``create_dimensions.py`` /
``create_facts.py`` can no longer reshape the existing tables. Afterwards
re-run the pipeline with ``--force`` to recreate and reload everything
from ``data/processed/``:

    python src/load/rebuild_schema.py
    python run_pipeline.py 2025 --force

This is destructive: every row in the warehouse is removed. The CSVs in
``data/processed/`` are the source of truth and are not touched.
"""

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))

from src.load.connection import get_connection
from src.load.schema import drop_all


def rebuild_schema():

    conn = None

    try:

        conn = get_connection()

        print("PostgreSQL connection successful")

        with conn.cursor() as cursor:

            drop_all(cursor)

        conn.commit()

        print("\nAll warehouse tables and views dropped.")
        print("Next: python run_pipeline.py <year> --force")

    except Exception as error:

        if conn is not None:
            conn.rollback()

        print("\nSchema rebuild failed")
        print(error)

        raise

    finally:

        if conn is not None:

            conn.close()

            print("\nPostgreSQL connection closed")


if __name__ == "__main__":

    rebuild_schema()
