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

# Which season's yearwise CSVs to load. The PostgreSQL fact tables
# themselves are NOT yearwise -- this only controls which CSV files
# get read and which season_key gets stamped onto every row.
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

# Unique constraint columns per table (see create_facts.py) -- used as
# the ON CONFLICT target so re-running the loader for a season that's
# already loaded does not create duplicate fact rows.
CONFLICT_COLUMNS = {
    "fact_braking_metrics": ["race_key", "driver_key"],
    "fact_championship_standings": ["race_key", "driver_key"],
    "fact_driver_race_metrics": ["race_key", "driver_key"],
    "fact_driver_race_telemetry_metrics": ["race_key", "driver_key"],
    "fact_driver_stints": ["race_key", "driver_key", "stint"],
    "fact_driver_style_metrics": ["race_key", "driver_key"],
    "fact_pitstops": ["race_key", "driver_key", "stint"],
    "fact_tire_degradation": ["race_key", "driver_key", "stint"],
}

# One PostgreSQL table per fact, sourced from that season's yearwise
# CSV (fact_braking_metrics -> fact_braking_metrics_2025.csv for
# YEAR = 2025). Loading YEAR = 2026 later reads fact_..._2026.csv but
# inserts into these exact same tables, distinguished by season_key.
FACT_TABLES = list(COLUMN_RENAMES.keys())


# ============================================================
# GET CSV
# ============================================================

def get_csv(filename):

    file = PROCESSED_FOLDER / filename

    if not file.exists():

        raise FileNotFoundError(
            f"\nRequired file not found:\n{file}"
        )

    return pd.read_csv(file)


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

        cursor.execute("""
            SELECT
                race_key,
                race
            FROM dim_races
        """)

        dimensions["races"] = {
            row[1]: row[0]
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

        validate_dimension_values(
            df,
            dimensions,
            "Race",
            "races"
        )

        df["race_key"] = (
            df["Race"]
            .map(dimensions["races"])
        )

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


# ============================================================
# CLEAN DATAFRAME
# ============================================================

def clean_dataframe(df):

    df = df.copy()

    # Convert NaN to None
    df = df.where(
        pd.notna(df),
        None
    )

    return df


# ============================================================
# CONVERT NUMPY SCALARS TO NATIVE PYTHON TYPES
#
# psycopg2 cannot adapt numpy.float64/int64 directly -- pandas leaves
# these in every numeric column read from CSV.
# ============================================================

def to_native(value):

    if value is None:

        return None

    if hasattr(value, "item"):

        return value.item()

    return value


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

    if conflict_columns:

        conflict_sql = ", ".join(conflict_columns)

        query = f"""
            INSERT INTO {table_name}
            ({columns_sql})
            VALUES %s
            ON CONFLICT ({conflict_sql})
            DO NOTHING
        """

    else:

        query = f"""
            INSERT INTO {table_name}
            ({columns_sql})
            VALUES %s
        """

    with conn.cursor() as cursor:

        execute_values(
            cursor,
            query,
            values,
            page_size=1000
        )

    return len(values)


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

    df = clean_dataframe(df)

    # --------------------------------------------------------
    # Insert
    # --------------------------------------------------------

    rows_inserted = insert_fact(
        conn,
        df,
        table_name
    )

    print(
        f"{table_name} loaded: "
        f"{rows_inserted} rows"
    )

    return rows_inserted


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
            f"Total rows inserted: "
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
