import sys
from pathlib import Path

import psycopg2


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))


# ============================================================
# DATABASE CONNECTION
# ============================================================

from connection import get_connection


# ============================================================
# CREATE DIMENSION TABLES
# ============================================================

def create_dimensions(conn):

    with conn.cursor() as cursor:

        # ====================================================
        # DIM SEASONS
        # ====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_seasons (

                season_key SERIAL PRIMARY KEY,

                season INTEGER NOT NULL UNIQUE

            );
        """)

        print("dim_seasons loaded")


        # ====================================================
        # DIM TEAMS
        # ====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_teams (

                team_key SERIAL PRIMARY KEY,

                team_name VARCHAR(100) NOT NULL UNIQUE

            );
        """)

        print("Loading dim_teams...")

        cursor.execute("""
            SELECT COUNT(*)
            FROM dim_teams;
        """)

        team_count = cursor.fetchone()[0]

        print(
            f"Rows found: {team_count}"
        )

        print("dim_teams loaded")


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

        print("Loading dim_drivers...")

        cursor.execute("""
            SELECT COUNT(*)
            FROM dim_drivers;
        """)

        driver_count = cursor.fetchone()[0]

        print(
            f"Rows found: {driver_count}"
        )

        print("dim_drivers loaded")


        # ====================================================
        # DIM RACES
        # ====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_races (

                race_key SERIAL PRIMARY KEY,

                round_number INTEGER NOT NULL,

                country VARCHAR(100),

                location VARCHAR(100),

                official_event_name VARCHAR(200),

                event_date DATE,

                event_format VARCHAR(50),

                sprint_weekend BOOLEAN,

                race VARCHAR(100) NOT NULL UNIQUE

            );
        """)

        print("Loading dim_races...")

        cursor.execute("""
            SELECT COUNT(*)
            FROM dim_races;
        """)

        race_count = cursor.fetchone()[0]

        print(
            f"Rows found: {race_count}"
        )

        print("dim_races loaded")


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
        print("All dimensions loaded successfully")
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