from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from src.load.connection import get_connection


DIMENSION_TABLES = [
    "dim_seasons",
    "dim_teams",
    "dim_drivers",
    "dim_races",
]

FACT_TABLES = [
    "fact_braking_metrics",
    "fact_championship_standings",
    "fact_driver_race_metrics",
    "fact_driver_race_telemetry_metrics",
    "fact_driver_stints",
    "fact_driver_style_metrics",
    "fact_pitstops",
    "fact_tire_degradation",
]

VIEWS = [
    "vw_championship",
    "vw_driver_race_performance",
    "vw_driver_style",
    "vw_driver_telemetry",
    "vw_pitstops",
    "vw_tire_degradation",
]


def check_table_has_rows(cursor, table):
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]

    if count == 0:
        raise ValueError(f"{table} is empty")

    print(f"✓ {table}: {count:,} rows")


def check_view_has_rows(cursor, view):
    cursor.execute(f"SELECT COUNT(*) FROM {view}")
    count = cursor.fetchone()[0]

    if count == 0:
        raise ValueError(f"{view} is empty")

    print(f"✓ {view}: {count:,} rows")


def check_null_keys(cursor, table, columns):
    for column in columns:

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM {table}
            WHERE {column} IS NULL
            """
        )

        count = cursor.fetchone()[0]

        if count > 0:
            raise ValueError(
                f"{table}.{column} contains {count:,} NULL values"
            )

        print(f"✓ {table}.{column}: no NULL values")


def check_foreign_keys(cursor):
    checks = [
        (
            "fact_driver_race_metrics",
            "driver_key",
            "dim_drivers",
            "driver_key",
        ),
        (
            "fact_driver_race_metrics",
            "race_key",
            "dim_races",
            "race_key",
        ),
        (
            "fact_driver_race_metrics",
            "season_key",
            "dim_seasons",
            "season_key",
        ),
        (
            "fact_championship_standings",
            "driver_key",
            "dim_drivers",
            "driver_key",
        ),
        (
            "fact_championship_standings",
            "race_key",
            "dim_races",
            "race_key",
        ),
        (
            "fact_championship_standings",
            "season_key",
            "dim_seasons",
            "season_key",
        ),
    ]

    for fact, fact_key, dimension, dimension_key in checks:

        query = f"""
            SELECT COUNT(*)
            FROM {fact} f
            LEFT JOIN {dimension} d
                ON f.{fact_key} = d.{dimension_key}
            WHERE f.{fact_key} IS NOT NULL
              AND d.{dimension_key} IS NULL
        """

        cursor.execute(query)

        count = cursor.fetchone()[0]

        if count > 0:
            raise ValueError(
                f"{fact}.{fact_key} has {count:,} orphaned keys"
            )

        print(
            f"✓ {fact}.{fact_key} → "
            f"{dimension}.{dimension_key}"
        )


def check_expected_season(cursor):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM dim_seasons
        WHERE season = 2025
        """
    )

    count = cursor.fetchone()[0]

    if count != 1:
        raise ValueError(
            f"Expected exactly one 2025 season, found {count}"
        )

    print("✓ 2025 season exists")


def check_race_coverage(cursor):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM dim_races
        """
    )

    race_count = cursor.fetchone()[0]

    if race_count != 24:
        raise ValueError(
            f"Expected 24 races, found {race_count}"
        )

    print("✓ Race coverage: 24 races")


def check_driver_race_grain(cursor):
    checks = [
        "fact_driver_race_metrics",
        "fact_driver_race_telemetry_metrics",
        "fact_driver_style_metrics",
        "vw_driver_race_performance",
        "vw_driver_telemetry",
        "vw_driver_style",
    ]

    for table in checks:

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT race_key, driver_key
                FROM {table}
                GROUP BY race_key, driver_key
                HAVING COUNT(*) > 1
            ) duplicates
            """
        )

        duplicate_count = cursor.fetchone()[0]

        if duplicate_count > 0:
            raise ValueError(
                f"{table} contains "
                f"{duplicate_count:,} duplicate race/driver groups"
            )

        print(
            f"✓ {table}: unique race/driver grain"
        )


def validate_pipeline():

    print("=" * 60)
    print("FORMULA 1 DATA QUALITY VALIDATION")
    print("=" * 60)

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        # --------------------------------------------------
        # DIMENSIONS
        # --------------------------------------------------

        print("\nDIMENSION TABLES")
        print("-" * 60)

        for table in DIMENSION_TABLES:
            check_table_has_rows(cursor, table)

        # --------------------------------------------------
        # FACTS
        # --------------------------------------------------

        print("\nFACT TABLES")
        print("-" * 60)

        for table in FACT_TABLES:
            check_table_has_rows(cursor, table)

        # --------------------------------------------------
        # VIEWS
        # --------------------------------------------------

        print("\nVISUALIZATION VIEWS")
        print("-" * 60)

        for view in VIEWS:
            check_view_has_rows(cursor, view)

        # --------------------------------------------------
        # NULL KEYS
        # --------------------------------------------------

        print("\nKEY VALIDATION")
        print("-" * 60)

        for table in FACT_TABLES:

            check_null_keys(
                cursor,
                table,
                [
                    "season_key",
                    "race_key",
                    "driver_key",
                ],
            )

        # --------------------------------------------------
        # FOREIGN KEYS
        # --------------------------------------------------

        print("\nFOREIGN KEY VALIDATION")
        print("-" * 60)

        check_foreign_keys(cursor)

        # --------------------------------------------------
        # SEASON
        # --------------------------------------------------

        print("\nSEASON VALIDATION")
        print("-" * 60)

        check_expected_season(cursor)

        # --------------------------------------------------
        # RACES
        # --------------------------------------------------

        print("\nRACE VALIDATION")
        print("-" * 60)

        check_race_coverage(cursor)

        # --------------------------------------------------
        # GRAIN
        # --------------------------------------------------

        print("\nGRAIN VALIDATION")
        print("-" * 60)

        check_driver_race_grain(cursor)

        cursor.close()

        print()
        print("=" * 60)
        print("ALL DATA QUALITY CHECKS PASSED")
        print("=" * 60)

    except Exception:

        print()
        print("=" * 60)
        print("DATA QUALITY VALIDATION FAILED")
        print("=" * 60)

        raise

    finally:

        if conn:
            conn.close()

        print("PostgreSQL connection closed")


if __name__ == "__main__":
    validate_pipeline()