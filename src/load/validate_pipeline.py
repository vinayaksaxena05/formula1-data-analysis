from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from psycopg2 import sql

from src.load.connection import get_connection
from src.load.schema import DIMENSION_TABLES, FACT_TABLES, VIEWS
from src.utils.cli import get_year


# Facts that share the 1-driver-x-1-race grain (used for the grain check
# and its matching views).
DRIVER_RACE_GRAIN_OBJECTS = [
    "fact_driver_race_metrics",
    "fact_driver_race_telemetry_metrics",
    "fact_driver_style_metrics",
    "vw_driver_race_performance",
    "vw_driver_telemetry",
    "vw_driver_style",
]

# Every fact table carries these three FK columns (enforced by
# check_null_keys below), so the FK check applies uniformly to all of
# FACT_TABLES instead of a hand-maintained per-table list that silently
# stops covering new fact tables.
FK_DIMENSIONS = [
    ("driver_key", "dim_drivers", "driver_key"),
    ("race_key", "dim_races", "race_key"),
    ("season_key", "dim_seasons", "season_key"),
]


def _count(cursor, query, params=None):
    cursor.execute(query, params or ())
    return cursor.fetchone()[0]


def check_table_has_rows(cursor, table):

    count = _count(
        cursor,
        sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)),
    )

    if count == 0:
        raise ValueError(f"{table} is empty")

    print(f"✓ {table}: {count:,} rows")


def check_null_keys(cursor, table, columns):

    for column in columns:

        count = _count(
            cursor,
            sql.SQL("SELECT COUNT(*) FROM {} WHERE {} IS NULL").format(
                sql.Identifier(table),
                sql.Identifier(column),
            ),
        )

        if count > 0:
            raise ValueError(
                f"{table}.{column} contains {count:,} NULL values"
            )

        print(f"✓ {table}.{column}: no NULL values")


def check_foreign_keys(cursor):

    for fact in FACT_TABLES:
        for fact_key, dimension, dimension_key in FK_DIMENSIONS:

            query = sql.SQL(
                """
                SELECT COUNT(*)
                FROM {fact} f
                LEFT JOIN {dimension} d
                    ON f.{fact_key} = d.{dimension_key}
                WHERE f.{fact_key} IS NOT NULL
                  AND d.{dimension_key} IS NULL
                """
            ).format(
                fact=sql.Identifier(fact),
                dimension=sql.Identifier(dimension),
                fact_key=sql.Identifier(fact_key),
                dimension_key=sql.Identifier(dimension_key),
            )

            count = _count(cursor, query)

            if count > 0:
                raise ValueError(
                    f"{fact}.{fact_key} has {count:,} orphaned keys"
                )

            print(f"✓ {fact}.{fact_key} → {dimension}.{dimension_key}")


def check_expected_season(cursor, year):

    count = _count(
        cursor,
        "SELECT COUNT(*) FROM dim_seasons WHERE season = %s",
        (year,),
    )

    if count != 1:
        raise ValueError(
            f"Expected exactly one {year} season row, found {count}"
        )

    print(f"✓ {year} season exists")


def check_race_coverage(cursor, year):

    race_count = _count(
        cursor,
        """
        SELECT COUNT(*)
        FROM dim_races r
        JOIN dim_seasons s ON r.season_key = s.season_key
        WHERE s.season = %s
        """,
        (year,),
    )

    if race_count == 0:
        raise ValueError(f"No races found in dim_races for season {year}")

    duplicate_rounds = _count(
        cursor,
        """
        SELECT COUNT(*) FROM (
            SELECT r.round_number
            FROM dim_races r
            JOIN dim_seasons s ON r.season_key = s.season_key
            WHERE s.season = %s
            GROUP BY r.round_number
            HAVING COUNT(*) > 1
        ) d
        """,
        (year,),
    )

    if duplicate_rounds > 0:
        raise ValueError(
            f"season {year} has {duplicate_rounds} duplicate round_number(s) "
            f"in dim_races"
        )

    print(f"✓ {year}: {race_count} races, no duplicate rounds")


def check_season_has_facts(cursor, year):

    for table in FACT_TABLES:

        count = _count(
            cursor,
            sql.SQL(
                """
                SELECT COUNT(*)
                FROM {} f
                JOIN dim_seasons s ON f.season_key = s.season_key
                WHERE s.season = %s
                """
            ).format(sql.Identifier(table)),
            (year,),
        )

        if count == 0:
            raise ValueError(f"{table} has no rows for season {year}")

        print(f"✓ {table}: {count:,} rows for {year}")


def check_driver_race_grain(cursor):

    for obj in DRIVER_RACE_GRAIN_OBJECTS:

        duplicate_count = _count(
            cursor,
            sql.SQL(
                """
                SELECT COUNT(*) FROM (
                    SELECT race_key, driver_key
                    FROM {}
                    GROUP BY race_key, driver_key
                    HAVING COUNT(*) > 1
                ) duplicates
                """
            ).format(sql.Identifier(obj)),
        )

        if duplicate_count > 0:
            raise ValueError(
                f"{obj} contains {duplicate_count:,} duplicate race/driver groups"
            )

        print(f"✓ {obj}: unique race/driver grain")


def validate_pipeline(year):

    print("=" * 60)
    print(f"FORMULA 1 DATA QUALITY VALIDATION — season {year}")
    print("=" * 60)

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        print("\nDIMENSION TABLES")
        print("-" * 60)
        for table in DIMENSION_TABLES:
            check_table_has_rows(cursor, table)

        print("\nFACT TABLES")
        print("-" * 60)
        for table in FACT_TABLES:
            check_table_has_rows(cursor, table)

        print("\nVISUALIZATION VIEWS")
        print("-" * 60)
        for view in VIEWS:
            check_table_has_rows(cursor, view)

        print("\nKEY VALIDATION")
        print("-" * 60)
        for table in FACT_TABLES:
            check_null_keys(
                cursor,
                table,
                ["season_key", "race_key", "driver_key"],
            )

        print("\nFOREIGN KEY VALIDATION")
        print("-" * 60)
        check_foreign_keys(cursor)

        print("\nSEASON VALIDATION")
        print("-" * 60)
        check_expected_season(cursor, year)

        print("\nRACE VALIDATION")
        print("-" * 60)
        check_race_coverage(cursor, year)

        print("\nLOADED-SEASON FACT COVERAGE")
        print("-" * 60)
        check_season_has_facts(cursor, year)

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
    validate_pipeline(get_year(default=2025))
