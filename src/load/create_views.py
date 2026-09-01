from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8")

# Project Root
ROOT_DIR = Path(__file__).resolve().parents[2]

# Allow imports from project root
sys.path.insert(0, str(ROOT_DIR))

from src.load.connection import get_connection

VISUALIZATION_DIR = ROOT_DIR / "src" / "visualization"
def load_sql_file(cursor, sql_file):
    """Execute a single SQL file."""

    print(f"Creating view from: {sql_file.name}")

    sql = sql_file.read_text(encoding="utf-8")

    if not sql.strip():
        raise ValueError(
            f"SQL file is empty: {sql_file}"
        )

    cursor.execute(sql)

    print(f"✓ {sql_file.name} completed")


def create_views():
    """Create or replace all visualization views."""

    if not VISUALIZATION_DIR.exists():
        raise FileNotFoundError(
            f"Visualization directory not found: {VISUALIZATION_DIR}"
        )

    sql_files = sorted(
        VISUALIZATION_DIR.glob("*.sql")
    )

    if not sql_files:
        raise FileNotFoundError(
            f"No SQL files found in {VISUALIZATION_DIR}"
        )

    print("=" * 60)
    print("Creating Visualization Views")
    print("=" * 60)

    print(f"Found {len(sql_files)} SQL files")

    conn = None

    try:
        conn = get_connection()

        cursor = conn.cursor()

        for sql_file in sql_files:
            load_sql_file(
                cursor,
                sql_file
            )

        conn.commit()

        cursor.close()

        print()
        print("=" * 60)
        print("All visualization views created successfully")
        print("=" * 60)

    except Exception:

        if conn:
            conn.rollback()

        print()
        print("=" * 60)
        print("Visualization view creation failed")
        print("=" * 60)

        raise

    finally:

        if conn:
            conn.close()

        print("PostgreSQL connection closed")


if __name__ == "__main__":
    create_views()