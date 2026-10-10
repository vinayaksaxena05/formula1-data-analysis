"""Canonical names of every warehouse object, plus a drop helper.

Kept in one place so ``create_dimensions``, ``create_facts``,
``load_facts`` and ``validate_pipeline`` do not each carry their own
copy of these lists (they previously did, and drifted).
"""

from psycopg2 import sql


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


# ON CONFLICT target columns per table -- the unique key each loader
# relies on for idempotent re-runs, and what assert_schema_current()
# checks actually exists on the live table.
DIMENSION_CONFLICT_KEYS = {
    "dim_seasons": ["season"],
    "dim_teams": ["team_id"],
    "dim_drivers": ["abbreviation"],
    "dim_races": ["season_key", "race"],
}

FACT_CONFLICT_KEYS = {
    "fact_braking_metrics": ["race_key", "driver_key"],
    "fact_championship_standings": ["race_key", "driver_key"],
    "fact_driver_race_metrics": ["race_key", "driver_key"],
    "fact_driver_race_telemetry_metrics": ["race_key", "driver_key"],
    "fact_driver_stints": ["race_key", "driver_key", "stint"],
    "fact_driver_style_metrics": ["race_key", "driver_key"],
    "fact_pitstops": ["race_key", "driver_key", "stint"],
    "fact_tire_degradation": ["race_key", "driver_key", "stint"],
}


def drop_all(cursor):
    """Drop every view and table, in FK-safe order.

    Used by ``rebuild_schema.py`` when a schema change means the
    ``CREATE TABLE IF NOT EXISTS`` statements in the create scripts can
    no longer reshape the live tables. This is destructive; the CSVs in
    ``data/processed/`` are the source of truth and a subsequent
    ``run_pipeline.py <year> --force`` recreates and reloads everything.
    """

    for view in VIEWS:

        cursor.execute(
            sql.SQL("DROP VIEW IF EXISTS {} CASCADE").format(
                sql.Identifier(view)
            )
        )

    for table in FACT_TABLES + DIMENSION_TABLES:

        cursor.execute(
            sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                sql.Identifier(table)
            )
        )


def _table_exists(cursor, table):

    cursor.execute("SELECT to_regclass(%s)", (f"public.{table}",))

    return cursor.fetchone()[0] is not None


def _unique_key_column_sets(cursor, table):
    """Every PK / UNIQUE constraint on ``table`` as a set of column names."""

    cursor.execute(
        """
        SELECT c.conname, array_agg(a.attname)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_attribute a
            ON a.attrelid = t.oid
           AND a.attnum = ANY(c.conkey)
           AND NOT a.attisdropped
        WHERE n.nspname = 'public'
          AND t.relname = %s
          AND c.contype IN ('p', 'u')
        GROUP BY c.conname
        """,
        (table,),
    )

    return [frozenset(cols) for _name, cols in cursor.fetchall()]


def assert_schema_current(cursor, conflict_keys):
    """Fail early, with a fix instruction, if a live table has drifted.

    For every table in ``conflict_keys`` that already exists, verify it
    carries a PK / UNIQUE constraint over exactly the expected key
    columns. A table that does not exist yet is fine -- the caller's
    ``CREATE TABLE`` statement will build it correctly. This turns a
    cryptic mid-load ``ON CONFLICT`` error into an actionable one.
    """

    stale = []

    for table, key_columns in conflict_keys.items():

        if not _table_exists(cursor, table):
            continue

        if frozenset(key_columns) not in _unique_key_column_sets(cursor, table):
            stale.append(
                f"{table}: expected UNIQUE {sorted(key_columns)}"
            )

    if stale:

        raise RuntimeError(
            "PostgreSQL schema is out of date:\n  "
            + "\n  ".join(stale)
            + "\n\nCREATE TABLE IF NOT EXISTS cannot reshape an existing "
            "table. Rebuild from the processed CSVs:\n"
            "    python src/load/rebuild_schema.py\n"
            "    python run_pipeline.py <year> --force"
        )
