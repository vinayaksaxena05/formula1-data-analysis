import sys
from pathlib import Path

import pandas as pd
from psycopg2.extras import execute_values


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))


# ============================================================
# DATABASE CONNECTION / SHARED HELPERS
# ============================================================

from src.load.connection import get_connection
from src.load.io import get_csv, nan_to_none, to_native
from src.load.schema import FACT_CONFLICT_KEYS as CONFLICT_COLUMNS, FACT_TABLES
from src.utils.cli import get_year


# ============================================================
# TARGET SEASON
#
# Which season's yearwise CSVs to load. The PostgreSQL fact tables
# themselves are NOT yearwise -- this only controls which CSV files
# get read and which season_key gets stamped onto every row. Set from
# argv[1] in __main__.
# ============================================================

YEAR = 2025


# ============================================================
# CSV -> POSTGRES COLUMN MAPPING
#
# Source CSVs are PascalCase (FastF1/pandas convention); Postgres
# columns are snake_case. "Race", "Driver", "Abbreviation" and
# "TeamName" are NOT listed here -- they're natural keys resolved to
# surrogate keys (race_key/driver_key/team_key) by add_dimension_keys,
# not renamed in place.
# ============================================================

COLUMN_RENAMES = {

    "fact_braking_metrics": {
        "NumBrakingEvents": "num_braking_events",
        "AvgBrakeDistance": "avg_brake_distance",
        "AvgEntrySpeed": "avg_entry_speed",
        "AvgExitSpeed": "avg_exit_speed",
        "AvgSpeedReduction": "avg_speed_reduction",
    },

    "fact_championship_standings": {
        "Round": "round",
        "Position": "position",
        "Points": "points",
        "CumulativePoints": "cumulative_points",
        "ChampionshipPosition": "championship_position",
    },

    "fact_driver_race_metrics": {
        "RepresentativePace": "representative_pace",
        "RelativePace": "relative_pace",
        "FastestLapDelta": "fastest_lap_delta",
        "PaceStdDev": "pace_std_dev",
    },

    "fact_driver_race_telemetry_metrics": {
        "AvgBrakeDistance": "avg_brake_distance",
        "AvgEntrySpeed": "avg_entry_speed",
        "AvgExitSpeed": "avg_exit_speed",
        "AvgSpeedReduction": "avg_speed_reduction",
        "FullThrottleRatio": "full_throttle_ratio",
        "BrakeUsageRatio": "brake_usage_ratio",
        "GearChangeRate": "gear_change_rate",
        "DRSUsageRatio": "drs_usage_ratio",
    },

    "fact_driver_stints": {
        "Stint": "stint",
        "Compound": "compound",
        "Laps": "laps",
        "AvgLapTime": "avg_lap_time",
        "FastestLap": "fastest_lap",
    },

    "fact_driver_style_metrics": {
        "FullThrottleRatio": "full_throttle_ratio",
        "BrakeUsageRatio": "brake_usage_ratio",
        "AvgBrake": "avg_brake",
        "AvgGear": "avg_gear",
        "GearChangeRate": "gear_change_rate",
        "AvgSpeed": "avg_speed",
        "TopSpeed": "top_speed",
        "DRSUsageRatio": "drs_usage_ratio",
    },

    "fact_pitstops": {
        "Stint": "stint",
        "PitLap": "pit_lap",
        "Compound": "compound",
    },

    "fact_tire_degradation": {
        "Compound": "compound",
        "Stint": "stint",
        "StintLength": "stint_length",
        "AvgPace": "avg_pace",
        "FirstThreeAvg": "first_three_avg",
        "LastThreeAvg": "last_three_avg",
        "PaceDropoff": "pace_dropoff",
        "DegradationRate": "degradation_rate",
    },
}

# fact_driver_stints.csv's AvgLapTime/FastestLap are pandas Timedelta
# columns serialized as "0 days 00:01:31.937000" strings -- they need
# converting to seconds (float) before they can go into a DOUBLE
# PRECISION column. Keyed by the ORIGINAL (pre-rename) CSV column name.
TIMEDELTA_COLUMNS = {
    "fact_driver_stints": ["AvgLapTime", "FastestLap"],
}

# Columns that must land as INTEGER, keyed by the POST-rename Postgres
# column name. pandas reads these as float64 (e.g. 1.0) since the CSV
# columns are floats; cast explicitly rather than relying on an
# implicit Postgres assignment cast.
INT_COLUMNS = {
    "fact_braking_metrics": ["num_braking_events"],
    "fact_championship_standings": ["round", "position", "championship_position"],
    "fact_driver_stints": ["stint", "laps"],
    "fact_pitstops": ["stint", "pit_lap"],
    "fact_tire_degradation": ["stint", "stint_length"],
}

# CONFLICT_COLUMNS (the per-table ON CONFLICT target that keeps re-runs
# idempotent) is imported from schema.py as FACT_CONFLICT_KEYS -- the
# same declaration create_facts.py checks the live tables against.

# FACT_TABLES (import order) is the authoritative list; every entry
# must have a column mapping here. Loading YEAR = 2026 later reads
# fact_..._2026.csv but inserts into these same tables, keyed by
# season_key.
_unmapped = set(FACT_TABLES) - set(COLUMN_RENAMES)

if _unmapped:
    raise RuntimeError(
        f"FACT_TABLES entries missing a COLUMN_RENAMES mapping: {sorted(_unmapped)}"
    )


# ============================================================
# GET DIMENSION MAPS
# ============================================================

def get_dimension_maps(conn):

    print("\nLoading dimension mappings...")

    dimensions = {}

    with conn.cursor() as cursor:

        # ----------------------------------------------------
        # SEASONS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                season_key,
                season
            FROM dim_seasons
        """)

        dimensions["seasons"] = {
            row[1]: row[0]
            for row in cursor.fetchall()
        }

        # ----------------------------------------------------
        # TEAMS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                team_key,
                team_name
            FROM dim_teams
        """)

        dimensions["teams"] = {
            row[1]: row[0]
            for row in cursor.fetchall()
        }

        # ----------------------------------------------------
        # DRIVERS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                driver_key,
                abbreviation
            FROM dim_drivers
        """)

        dimensions["drivers"] = {
            row[1]: row[0]
            for row in cursor.fetchall()
        }

        # ----------------------------------------------------
        # RACES
        # ----------------------------------------------------

        # dim_races is keyed on (season_key, race) -- a race token
        # repeats every season -- so the lookup is too.
        cursor.execute("""
            SELECT
                race_key,
                race,
                season_key
            FROM dim_races
        """)

        dimensions["races"] = {
            (row[2], row[1]): row[0]
            for row in cursor.fetchall()
        }

    print(
        f"Seasons: {len(dimensions['seasons'])}"
    )

    print(
        f"Teams: {len(dimensions['teams'])}"
    )

    print(
        f"Drivers: {len(dimensions['drivers'])}"
    )

    print(
        f"Races: {len(dimensions['races'])}"
    )

    return dimensions


# ============================================================
# GET SEASON KEY
# ============================================================

def get_season_key(dimensions):

    if YEAR not in dimensions["seasons"]:

        raise ValueError(
            f"Season {YEAR} not found in dim_seasons."
        )

    return dimensions["seasons"][YEAR]


# ============================================================
# VALIDATE VALUES
# ============================================================

def validate_dimension_values(
    df,
    dimensions,
    column,
    dimension_name
):

    if column not in df.columns:

        return

    values = set(
        df[column].dropna().unique()
    )

    known_values = set(
        dimensions[dimension_name].keys()
    )

    unknown_values = values - known_values

    if unknown_values:

        raise ValueError(
            f"\nUnknown {column} values found:\n"
            f"{sorted(unknown_values)}"
        )


# ============================================================
# ADD FOREIGN KEYS
# ============================================================

def add_dimension_keys(
    df,
    dimensions,
    season_key
):

    df = df.copy()

    # --------------------------------------------------------
    # Season
    # --------------------------------------------------------

    df.insert(
        0,
        "season_key",
        season_key
    )

    # --------------------------------------------------------
    # Race
    # --------------------------------------------------------

    if "Race" in df.columns:

        # dimensions["races"] is keyed (season_key, race); narrow it to
        # this season before validating/mapping the race tokens.
        season_races = {
            race: race_key
            for (race_season_key, race), race_key in dimensions["races"].items()
            if race_season_key == season_key
        }

        unknown_races = (
            set(df["Race"].dropna().unique())
            - set(season_races)
        )

        if unknown_races:

            raise ValueError(
                f"\nUnknown Race values for season_key={season_key}:\n"
                f"{sorted(unknown_races)}"
            )

        df["race_key"] = df["Race"].map(season_races)

        df.drop(
            columns=["Race"],
            inplace=True
        )

    # --------------------------------------------------------
    # Driver
    # --------------------------------------------------------

    if "Driver" in df.columns:

        validate_dimension_values(
            df,
            dimensions,
            "Driver",
            "drivers"
        )

        df["driver_key"] = (
            df["Driver"]
            .map(dimensions["drivers"])
        )

        df.drop(
            columns=["Driver"],
            inplace=True
        )

    # --------------------------------------------------------
    # Championship standings uses Abbreviation
    # --------------------------------------------------------

    if "Abbreviation" in df.columns:

        validate_dimension_values(
            df,
            dimensions,
            "Abbreviation",
            "drivers"
        )

        df["driver_key"] = (
            df["Abbreviation"]
            .map(dimensions["drivers"])
        )

        df.drop(
            columns=["Abbreviation"],
            inplace=True
        )

    # --------------------------------------------------------
    # Championship standings uses TeamName
    # --------------------------------------------------------

    if "TeamName" in df.columns:

        validate_dimension_values(
            df,
            dimensions,
            "TeamName",
            "teams"
        )

        df["team_key"] = (
            df["TeamName"]
            .map(dimensions["teams"])
        )

        df.drop(
            columns=["TeamName"],
            inplace=True
        )

    return df


# ============================================================
# CONVERT TIMEDELTA COLUMNS TO SECONDS
# ============================================================

def convert_timedelta_columns(df, table_name):

    df = df.copy()

    for column in TIMEDELTA_COLUMNS.get(table_name, []):

        if column in df.columns:

            df[column] = (
                pd.to_timedelta(df[column], errors="coerce")
                .dt.total_seconds()
            )

    return df


# ============================================================
# RENAME CSV COLUMNS TO POSTGRES COLUMNS
# ============================================================

def rename_columns(df, table_name):

    return df.rename(
        columns=COLUMN_RENAMES.get(table_name, {})
    )


# ============================================================
# CAST INTEGER COLUMNS
# ============================================================

def cast_integer_columns(df, table_name):

    df = df.copy()

    for column in INT_COLUMNS.get(table_name, []):

        if column in df.columns:

            df[column] = df[column].apply(
                lambda value: int(value) if pd.notna(value) else None
            )

    return df


# NaN -> None and numpy-scalar -> native-Python coercion both live in
# src/load/io.py (nan_to_none, to_native), shared with load_dimensions.


# ============================================================
# GET POSTGRES TABLE COLUMNS
# ============================================================

def get_table_columns(
    conn,
    table_name
):

    with conn.cursor() as cursor:

        cursor.execute("""
            SELECT
                column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))

        return [
            row[0]
            for row in cursor.fetchall()
        ]


# ============================================================
# INSERT FACT
# ============================================================

def insert_fact(
    conn,
    df,
    table_name
):

    if df.empty:

        print(
            f"{table_name}: no rows"
        )

        return 0

    postgres_columns = get_table_columns(
        conn,
        table_name
    )

    if not postgres_columns:

        raise ValueError(
            f"PostgreSQL table "
            f"'{table_name}' does not exist."
        )

    # --------------------------------------------------------
    # Keep only columns that exist in PostgreSQL
    # --------------------------------------------------------

    missing_columns = [
        column
        for column in df.columns
        if column not in postgres_columns
    ]

    if missing_columns:

        raise ValueError(
            f"\n{table_name} contains columns "
            f"not present in PostgreSQL:\n"
            f"{missing_columns}"
        )

    insert_columns = [
        column
        for column in postgres_columns
        if column in df.columns
    ]

    if not insert_columns:

        raise ValueError(
            f"No matching columns found "
            f"for {table_name}"
        )

    df = df[
        insert_columns
    ]

    columns_sql = ", ".join(
        f'"{column}"'
        for column in insert_columns
    )

    values = [
        tuple(
            to_native(value)
            for value in row
        )
        for row in df.itertuples(
            index=False,
            name=None
        )
    ]

    conflict_columns = CONFLICT_COLUMNS.get(table_name)

    update_columns = [
        column
        for column in insert_columns
        if column not in (conflict_columns or [])
    ]

    if conflict_columns and update_columns:

        # DO UPDATE, not DO NOTHING: now that create_facts.py no longer
        # drops tables every run, a season re-run after fixing a
        # transform bug has to overwrite the stale metric values already
        # in Postgres, not silently skip them.
        conflict_sql = ", ".join(conflict_columns)

        update_sql = ", ".join(
            f'"{column}" = EXCLUDED."{column}"'
            for column in update_columns
        )

        query = f"""
            INSERT INTO {table_name}
            ({columns_sql})
            VALUES %s
            ON CONFLICT ({conflict_sql})
            DO UPDATE SET {update_sql}
            RETURNING 1
        """

    elif conflict_columns:

        # Every insertable column is part of the conflict key -- there
        # is nothing left to update, so DO UPDATE SET would be empty.
        query = f"""
            INSERT INTO {table_name}
            ({columns_sql})
            VALUES %s
            ON CONFLICT ({conflict_sql})
            DO NOTHING
            RETURNING 1
        """

    else:

        query = f"""
            INSERT INTO {table_name}
            ({columns_sql})
            VALUES %s
            RETURNING 1
        """

    # fetch=True aggregates RETURNING rows across every page, so this
    # counts every row written -- inserted or (with DO UPDATE) updated.
    with conn.cursor() as cursor:

        written = execute_values(
            cursor,
            query,
            values,
            page_size=1000,
            fetch=True,
        )

    return len(written)


# ============================================================
# LOAD ONE FACT
# ============================================================

def load_fact(
    conn,
    table_name,
    filename,
    dimensions,
    season_key
):

    print()
    print("----------------------------------------")
    print(f"Loading {table_name}")
    print("----------------------------------------")

    df = get_csv(filename)

    print(
        f"File: {filename}"
    )

    print(
        f"Rows found: {len(df)}"
    )

    print(
        f"Columns: {list(df.columns)}"
    )

    # --------------------------------------------------------
    # Timedelta -> seconds (must run on the original CSV column
    # names, before rename)
    # --------------------------------------------------------

    df = convert_timedelta_columns(df, table_name)

    # --------------------------------------------------------
    # Rename CSV (PascalCase) columns to Postgres (snake_case)
    # columns. Race/Driver/Abbreviation/TeamName are untouched
    # here -- add_dimension_keys resolves and drops those.
    # --------------------------------------------------------

    df = rename_columns(df, table_name)

    # --------------------------------------------------------
    # Add foreign keys
    # --------------------------------------------------------

    df = add_dimension_keys(
        df,
        dimensions,
        season_key
    )

    # --------------------------------------------------------
    # Check FK resolution
    # --------------------------------------------------------

    for column in [
        "race_key",
        "driver_key",
        "team_key"
    ]:

        if column in df.columns:

            if df[column].isna().any():

                raise ValueError(
                    f"{table_name}: "
                    f"NULL values found in "
                    f"{column} after mapping."
                )

    # --------------------------------------------------------
    # Cast integer columns, then convert remaining NaN -> None
    # --------------------------------------------------------

    df = cast_integer_columns(df, table_name)

    df = nan_to_none(df)

    # --------------------------------------------------------
    # Insert
    # --------------------------------------------------------

    rows_written = insert_fact(
        conn,
        df,
        table_name
    )

    print(
        f"{table_name}: {rows_written} rows written "
        f"(inserted or updated; {len(df)} rows in file)"
    )

    return rows_written


# ============================================================
# MAIN
# ============================================================

def main():

    conn = None

    try:

        print("=" * 60)
        print("Loading Fact Tables")
        print("=" * 60)

        # ----------------------------------------------------
        # Connect
        # ----------------------------------------------------

        conn = get_connection()

        print(
            "PostgreSQL connection successful"
        )

        # ----------------------------------------------------
        # Dimension mappings
        # ----------------------------------------------------

        dimensions = get_dimension_maps(
            conn
        )

        # ----------------------------------------------------
        # Season
        # ----------------------------------------------------

        season_key = get_season_key(
            dimensions
        )

        print(
            f"\nSeason {YEAR} "
            f"mapped to season_key={season_key}"
        )

        # ----------------------------------------------------
        # Load all facts
        # ----------------------------------------------------

        total_rows = 0

        for table_name in FACT_TABLES:

            filename = f"{table_name}_{YEAR}.csv"

            rows = load_fact(
                conn,
                table_name,
                filename,
                dimensions,
                season_key
            )

            total_rows += rows

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        conn.commit()

        print()
        print("=" * 60)
        print("ALL FACT TABLES LOADED SUCCESSFULLY")
        print("=" * 60)

        print(
            f"Total rows written: "
            f"{total_rows}"
        )

    except Exception as e:

        print()
        print("=" * 60)
        print("FACT LOADING FAILED")
        print("=" * 60)

        print(e)

        if conn is not None:

            conn.rollback()

            print(
                "\nTransaction rolled back."
            )

        raise

    finally:

        if conn is not None:

            conn.close()

            print(
                "\nPostgreSQL connection closed."
            )


if __name__ == "__main__":

    YEAR = get_year(default=2025)

    main()
