import sys
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))


# ============================================================
# DATABASE CONNECTION / SHARED HELPERS
# ============================================================

from src.load.connection import get_connection
from src.load.io import get_csv, to_native, run_insert
from src.utils.cli import get_year


# ============================================================
# TARGET SEASON
#
# Set from argv[1] in __main__ (matching load_facts.py) so the
# orchestrator's per-year invocation is honoured. The module-level
# default keeps the loaders importable/testable.
# ============================================================

YEAR = 2025


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

    run_insert(conn, query, rows)

    print("dim_seasons loaded")


# ============================================================
# TEAMS
# ============================================================

def load_teams(conn):

    file = "dim_teams.csv"

    df = get_csv(file)

    print("Loading dim_teams...")
    print(f"Rows found: {len(df)}")

    required = [
        "TeamId",
        "TeamName",
        "TeamColor"
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
        subset=["TeamId"]
    )

    rows = [
        (
            to_native(row["TeamId"]),
            to_native(row["TeamName"]),
            to_native(row["TeamColor"]),
        )
        for _, row in df.iterrows()
    ]

    # TeamName / TeamColor are SCD1 attributes (see build_team_dimension.py)
    # -- a re-run with a renamed sponsor/livery must overwrite the stored
    # row, not silently keep whichever values were loaded first.
    query = """
        INSERT INTO dim_teams (
            team_id,
            team_name,
            team_color
        )
        VALUES %s
        ON CONFLICT (team_id)
        DO UPDATE SET
            team_name = EXCLUDED.team_name,
            team_color = EXCLUDED.team_color
    """

    run_insert(conn, query, rows)

    print("dim_teams loaded")


# ============================================================
# DRIVERS
# ============================================================

def load_drivers(conn):

    file = "dim_drivers.csv"

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
            to_native(row["DriverNumber"]),
            to_native(row["Abbreviation"]),
            to_native(row["FirstName"]),
            to_native(row["LastName"]),
            to_native(row["FullName"]),
            to_native(row["CountryCode"]),
        )
        for _, row in df.iterrows()
    ]

    # DriverNumber is the SCD1 attribute that actually varies season to
    # season (see build_driver_dimension.py); the rest are stable
    # identity attributes, but updating all of them keeps a re-run from
    # ever silently diverging from the CSV, the source of truth.
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
        DO UPDATE SET
            driver_number = EXCLUDED.driver_number,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            full_name = EXCLUDED.full_name,
            country_code = EXCLUDED.country_code
    """

    run_insert(conn, query, rows)

    print("dim_drivers loaded")


# ============================================================
# RACES
# ============================================================

def get_season_key(conn, year):
    """Resolve a season year to its dim_seasons surrogate key.

    load_seasons must have run first (it does, in main()).
    """

    with conn.cursor() as cursor:

        cursor.execute(
            "SELECT season_key FROM dim_seasons WHERE season = %s",
            (year,),
        )

        row = cursor.fetchone()

    if row is None:

        raise ValueError(
            f"Season {year} not in dim_seasons -- load_seasons must run first."
        )

    return row[0]


def load_races(conn):

    file = "dim_races.csv"

    df = get_csv(file)

    print("Loading dim_races...")
    print(f"Rows found: {len(df)}")

    required = [
        "Season",
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
        subset=["Season", "Race"]
    )

    # A race token repeats every season, so dim_races is keyed on
    # (season_key, race). The CSV is now cumulative across seasons, so
    # each row resolves its own season_key from its own Season value
    # rather than a single run-wide one.
    season_keys = {
        season: get_season_key(conn, int(season))
        for season in df["Season"].unique()
    }

    rows = [
        (
            season_keys[row["Season"]],
            int(row["RoundNumber"]),
            to_native(row["Country"]),
            to_native(row["Location"]),
            to_native(row["OfficialEventName"]),
            to_native(row["EventDate"]),
            to_native(row["EventFormat"]),
            to_native(row["SprintWeekend"]),
            to_native(row["Race"]),
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
        ON CONFLICT (season_key, race)
        DO UPDATE SET
            round_number = EXCLUDED.round_number,
            country = EXCLUDED.country,
            location = EXCLUDED.location,
            official_event_name = EXCLUDED.official_event_name,
            event_date = EXCLUDED.event_date,
            event_format = EXCLUDED.event_format,
            sprint_weekend = EXCLUDED.sprint_weekend
    """

    run_insert(conn, query, rows)

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

        # Single transaction across all four tables: a failure in any
        # one (e.g. load_races) leaves none of them partially committed.
        load_seasons(conn)

        load_teams(conn)

        load_drivers(conn)

        load_races(conn)

        conn.commit()

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