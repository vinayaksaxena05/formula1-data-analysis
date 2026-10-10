import sys
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))


# ============================================================
# DATABASE CONNECTION
# ============================================================

from src.load.connection import get_connection
from src.load.schema import DIMENSION_CONFLICT_KEYS, assert_schema_current


# ============================================================
# CREATE DIMENSION TABLES
# ============================================================

def create_dimensions(conn):
    """Ensure the dimension tables exist.

    This is DDL only -- it creates tables if they are absent and reports
    how many rows each already holds. Populating them is the job of
    load_dimensions.py, which runs next in the pipeline. A schema change
    here does NOT reshape an existing table; run rebuild_schema.py first
    for that.
    """

    with conn.cursor() as cursor:

        # Stop with an actionable message if an existing table has
        # drifted from the shape below (a stale UNIQUE key, etc.).
        assert_schema_current(cursor, DIMENSION_CONFLICT_KEYS)

        # ====================================================
        # DIM SEASONS
        # ====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_seasons (

                season_key SERIAL PRIMARY KEY,

                season INTEGER NOT NULL UNIQUE

            );
        """)

        print("dim_seasons ready")


        # ====================================================
        # DIM TEAMS
        # ====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_teams (

                team_key SERIAL PRIMARY KEY,

                team_name VARCHAR(100) NOT NULL UNIQUE

            );
        """)

        cursor.execute("""
            SELECT COUNT(*)
            FROM dim_teams;
        """)

        team_count = cursor.fetchone()[0]

        print(f"dim_teams ready ({team_count} rows)")


        # ====================================================
        # DIM DRIVERS
        # ====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_drivers (

                driver_key SERIAL PRIMARY KEY,

                driver_number INTEGER,

                abbreviation VARCHAR(10) NOT NULL UNIQUE,

                first_name VARCHAR(100),

                last_name VARCHAR(100),

                full_name VARCHAR(200),

                country_code VARCHAR(10)

            );
        """)

        cursor.execute("""
            SELECT COUNT(*)
            FROM dim_drivers;
        """)

        driver_count = cursor.fetchone()[0]

        print(f"dim_drivers ready ({driver_count} rows)")


        # ====================================================
        # DIM RACES
        # ====================================================

        # A race token ("monaco", "bahrain", ...) repeats every season, so
        # the natural key is (season_key, race), not race alone -- otherwise
        # loading a second season silently collides with the first.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_races (

                race_key SERIAL PRIMARY KEY,

                season_key INTEGER NOT NULL
                    REFERENCES dim_seasons(season_key),

                round_number INTEGER NOT NULL,

                country VARCHAR(100),

                location VARCHAR(100),

                official_event_name VARCHAR(200),

                event_date DATE,

                event_format VARCHAR(50),

                sprint_weekend BOOLEAN,

                race VARCHAR(100) NOT NULL,

                CONSTRAINT uq_dim_races UNIQUE (season_key, race)

            );
        """)

        cursor.execute("""
            SELECT COUNT(*)
            FROM dim_races;
        """)

        race_count = cursor.fetchone()[0]

        print(f"dim_races ready ({race_count} rows)")


        # ====================================================
        # COMMIT
        # ====================================================

        conn.commit()


# ============================================================
# MAIN
# ============================================================

def main():

    conn = None

    try:

        conn = get_connection()

        print("Connected to PostgreSQL\n")

        create_dimensions(conn)

        print("\n========================================")
        print("All dimension tables ready")
        print("========================================")

    except Exception as e:

        if conn is not None:
            conn.rollback()

        print("\n========================================")
        print("Dimension creation failed")
        print("========================================")

        print(e)

        raise

    finally:

        if conn is not None:

            conn.close()

            print(
                "\nPostgreSQL connection closed"
            )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()