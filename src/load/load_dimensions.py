import sys
import pandas as pd
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))


# ============================================================
# DATABASE CONNECTION
# ============================================================

from connection import get_connection
from src.utils.cli import get_year


# ============================================================
# PATHS
# ============================================================

PROCESSED_FOLDER = (
    ROOT_DIR
    / "data"
    / "processed"
)

YEAR = 2025


# ============================================================
# CSV HELPER
# ============================================================

def get_csv(filename):

    file = PROCESSED_FOLDER / filename

    if not file.exists():

        raise FileNotFoundError(
            f"\nRequired file not found:\n{file}"
        )

    return pd.read_csv(file)


# ============================================================
# SEASONS
# ============================================================

def load_seasons(conn):

    file = "dim_seasons.csv"

    df = get_csv(file)

    print("Loading dim_seasons...")
    print(f"Rows found: {len(df)}")

    required = [
        "SeasonYear"
    ]

    for column in required:

        if column not in df.columns:

            raise KeyError(
                f"{column} missing from {file}. "
                f"Available columns: {list(df.columns)}"
            )

    df = df[
        required
    ].drop_duplicates()

    query = """
        INSERT INTO dim_seasons (
            season
        )
        VALUES %s
        ON CONFLICT (season)
        DO NOTHING
    """

    rows = [
        (
            int(row["SeasonYear"]),
        )
        for _, row in df.iterrows()
    ]

    with conn.cursor() as cursor:

        execute_values(
            cursor,
            query,
            rows
        )

    conn.commit()

    print("dim_seasons loaded")


# ============================================================
# TEAMS
# ============================================================

def load_teams(conn):

    file = "dim_teams.csv"

    df = get_csv(file)

    print("Loading dim_teams...")
    print(f"Rows found: {len(df)}")

    if "TeamName" not in df.columns:

        raise KeyError(
            f"TeamName missing from {file}. "
            f"Available columns: {list(df.columns)}"
        )

    df = df[
        ["TeamName"]
    ].drop_duplicates()

    rows = [
        (
            row["TeamName"],
        )
        for _, row in df.iterrows()
    ]

    query = """
        INSERT INTO dim_teams (
            team_name
        )
        VALUES %s
        ON CONFLICT (team_name)
        DO NOTHING
    """

    with conn.cursor() as cursor:

        execute_values(
            cursor,
            query,
            rows
        )

    conn.commit()

    print("dim_teams loaded")


# ============================================================
# DRIVERS
# ============================================================

def load_drivers(conn):

    file = f"dim_drivers_{YEAR}.csv"

    df = get_csv(file)

    print("Loading dim_drivers...")
    print(f"Rows found: {len(df)}")

    required = [
        "DriverNumber",
        "Abbreviation",
        "FirstName",
        "LastName",
        "FullName",
        "CountryCode"
    ]

    for column in required:

        if column not in df.columns:

            raise KeyError(
                f"{column} missing from {file}. "
                f"Available columns: {list(df.columns)}"
            )

    df = df[
        required
    ].drop_duplicates(
        subset=["Abbreviation"]
    )

    rows = [
        (
            row["DriverNumber"],
            row["Abbreviation"],
            row["FirstName"],
            row["LastName"],
            row["FullName"],
            row["CountryCode"]
        )
        for _, row in df.iterrows()
    ]

    query = """
        INSERT INTO dim_drivers (
            driver_number,
            abbreviation,
            first_name,
            last_name,
            full_name,
            country_code
        )
        VALUES %s
        ON CONFLICT (abbreviation)
        DO NOTHING
    """

    with conn.cursor() as cursor:

        execute_values(
            cursor,
            query,
            rows
        )

    conn.commit()

    print("dim_drivers loaded")


# ============================================================
# RACES
# ============================================================

def load_races(conn):

    file = f"dim_races_{YEAR}.csv"

    df = get_csv(file)

    print("Loading dim_races...")
    print(f"Rows found: {len(df)}")

    required = [
        "RoundNumber",
        "Country",
        "Location",
        "OfficialEventName",
        "EventDate",
        "EventFormat",
        "SprintWeekend",
        "Race"
    ]

    for column in required:

        if column not in df.columns:

            raise KeyError(
                f"{column} missing from {file}. "
                f"Available columns: {list(df.columns)}"
            )

    df = df[
        required
    ].drop_duplicates(
        subset=["Race"]
    )

    # dim_races belongs to exactly one season (dim_seasons -> dim_races),
    # so season_key must be resolved and included here -- without it,
    # races are inserted with no link back to dim_seasons at all.
    with conn.cursor() as cursor:

        cursor.execute(
            "SELECT season_key FROM dim_seasons WHERE season = %s",
            (YEAR,)
        )

        result = cursor.fetchone()

    if result is None:
        raise ValueError(
            f"{YEAR} was not found in dim_seasons. Run load_seasons() first."
        )

    season_key = result[0]

    rows = [
        (
            season_key,
            int(row["RoundNumber"]),
            row["Country"],
            row["Location"],
            row["OfficialEventName"],
            row["EventDate"],
            row["EventFormat"],
            row["SprintWeekend"],
            row["Race"]
        )
        for _, row in df.iterrows()
    ]

    query = """
        INSERT INTO dim_races (
            season_key,
            round_number,
            country,
            location,
            official_event_name,
            event_date,
            event_format,
            sprint_weekend,
            race
        )
        VALUES %s
        ON CONFLICT (season_key, round_number)
        DO NOTHING
    """

    with conn.cursor() as cursor:

        execute_values(
            cursor,
            query,
            rows
        )

    conn.commit()

    print("dim_races loaded")


# ============================================================
# MAIN
# ============================================================

def main():

    conn = None

    try:

        print("\n========================================")
        print("Loading Dimension Tables")
        print("========================================")

        conn = get_connection()

        print("PostgreSQL connection successful\n")

        load_seasons(conn)

        load_teams(conn)

        load_drivers(conn)

        load_races(conn)

        print("\n========================================")
        print("All dimensions loaded successfully")
        print("========================================")

    except Exception as e:

        if conn is not None:
            conn.rollback()

        print("\n========================================")
        print("Dimension loading failed")
        print("========================================")

        print(e)

        raise

    finally:

        if conn is not None:
            conn.close()

            print("\nPostgreSQL connection closed")


if __name__ == "__main__":

    YEAR = get_year(default=2025)

    main()