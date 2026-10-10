import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))

from src.load.connection import get_connection
from src.load.schema import FACT_CONFLICT_KEYS, assert_schema_current


def create_facts():

    conn = get_connection()
    cursor = conn.cursor()

    # ------------------------------------------------------------
    # CREATE (idempotent)
    #
    # Every fact table is season-agnostic: one table holds every
    # season's rows, distinguished by season_key -> dim_seasons.
    # CREATE TABLE IF NOT EXISTS so re-running the pipeline for a new
    # season adds to the tables rather than dropping prior seasons'
    # data. A schema change here does NOT reshape an existing table --
    # run rebuild_schema.py first for that.
    # ------------------------------------------------------------

    create_queries = [

        # ---------------------------------
        # FACT BRAKING METRICS
        # Grain: 1 driver x 1 race
        # ---------------------------------
        """
        CREATE TABLE IF NOT EXISTS fact_braking_metrics (
            braking_metric_key SERIAL PRIMARY KEY,

            season_key INTEGER NOT NULL
                REFERENCES dim_seasons(season_key),
            race_key INTEGER NOT NULL
                REFERENCES dim_races(race_key),
            driver_key INTEGER NOT NULL
                REFERENCES dim_drivers(driver_key),

            num_braking_events INTEGER,
            avg_brake_distance DOUBLE PRECISION,
            avg_entry_speed DOUBLE PRECISION,
            avg_exit_speed DOUBLE PRECISION,
            avg_speed_reduction DOUBLE PRECISION,

            CONSTRAINT uq_braking_metrics
                UNIQUE (race_key, driver_key)
        );
        """,

        # ---------------------------------
        # FACT CHAMPIONSHIP STANDINGS
        # Grain: 1 driver x 1 race
        # ---------------------------------
        """
        CREATE TABLE IF NOT EXISTS fact_championship_standings (
            championship_standing_key SERIAL PRIMARY KEY,

            season_key INTEGER NOT NULL
                REFERENCES dim_seasons(season_key),
            race_key INTEGER NOT NULL
                REFERENCES dim_races(race_key),
            driver_key INTEGER NOT NULL
                REFERENCES dim_drivers(driver_key),
            team_key INTEGER NOT NULL
                REFERENCES dim_teams(team_key),

            round INTEGER,
            position INTEGER,
            points DOUBLE PRECISION,
            cumulative_points DOUBLE PRECISION,
            championship_position INTEGER,

            CONSTRAINT uq_championship_standings
                UNIQUE (race_key, driver_key)
        );
        """,

        # ---------------------------------
        # FACT DRIVER RACE METRICS
        # Grain: 1 driver x 1 race
        # ---------------------------------
        """
        CREATE TABLE IF NOT EXISTS fact_driver_race_metrics (
            driver_race_metric_key SERIAL PRIMARY KEY,

            season_key INTEGER NOT NULL
                REFERENCES dim_seasons(season_key),
            race_key INTEGER NOT NULL
                REFERENCES dim_races(race_key),
            driver_key INTEGER NOT NULL
                REFERENCES dim_drivers(driver_key),

            representative_pace DOUBLE PRECISION,
            relative_pace DOUBLE PRECISION,
            fastest_lap_delta DOUBLE PRECISION,
            pace_std_dev DOUBLE PRECISION,

            CONSTRAINT uq_driver_race_metrics
                UNIQUE (race_key, driver_key)
        );
        """,

        # ---------------------------------
        # FACT DRIVER RACE TELEMETRY METRICS
        # Grain: 1 driver x 1 race
        # ---------------------------------
        """
        CREATE TABLE IF NOT EXISTS fact_driver_race_telemetry_metrics (
            driver_race_telemetry_metric_key SERIAL PRIMARY KEY,

            season_key INTEGER NOT NULL
                REFERENCES dim_seasons(season_key),
            race_key INTEGER NOT NULL
                REFERENCES dim_races(race_key),
            driver_key INTEGER NOT NULL
                REFERENCES dim_drivers(driver_key),

            avg_brake_distance DOUBLE PRECISION,
            avg_entry_speed DOUBLE PRECISION,
            avg_exit_speed DOUBLE PRECISION,
            avg_speed_reduction DOUBLE PRECISION,
            full_throttle_ratio DOUBLE PRECISION,
            brake_usage_ratio DOUBLE PRECISION,
            gear_change_rate DOUBLE PRECISION,
            drs_usage_ratio DOUBLE PRECISION,

            CONSTRAINT uq_driver_race_telemetry_metrics
                UNIQUE (race_key, driver_key)
        );
        """,

        # ---------------------------------
        # FACT DRIVER STINTS
        # Grain: 1 driver x race x stint
        # ---------------------------------
        """
        CREATE TABLE IF NOT EXISTS fact_driver_stints (
            driver_stint_key SERIAL PRIMARY KEY,

            season_key INTEGER NOT NULL
                REFERENCES dim_seasons(season_key),
            race_key INTEGER NOT NULL
                REFERENCES dim_races(race_key),
            driver_key INTEGER NOT NULL
                REFERENCES dim_drivers(driver_key),

            stint INTEGER,
            compound VARCHAR(50),
            laps INTEGER,
            avg_lap_time DOUBLE PRECISION,
            fastest_lap DOUBLE PRECISION,

            CONSTRAINT uq_driver_stints
                UNIQUE (race_key, driver_key, stint)
        );
        """,

        # ---------------------------------
        # FACT DRIVER STYLE METRICS
        # Grain: 1 driver x 1 race
        # ---------------------------------
        """
        CREATE TABLE IF NOT EXISTS fact_driver_style_metrics (
            driver_style_metric_key SERIAL PRIMARY KEY,

            season_key INTEGER NOT NULL
                REFERENCES dim_seasons(season_key),
            race_key INTEGER NOT NULL
                REFERENCES dim_races(race_key),
            driver_key INTEGER NOT NULL
                REFERENCES dim_drivers(driver_key),

            full_throttle_ratio DOUBLE PRECISION,
            brake_usage_ratio DOUBLE PRECISION,
            avg_brake DOUBLE PRECISION,
            avg_gear DOUBLE PRECISION,
            gear_change_rate DOUBLE PRECISION,
            avg_speed DOUBLE PRECISION,
            top_speed DOUBLE PRECISION,
            drs_usage_ratio DOUBLE PRECISION,

            CONSTRAINT uq_driver_style_metrics
                UNIQUE (race_key, driver_key)
        );
        """,

        # ---------------------------------
        # FACT PITSTOPS
        # Grain: 1 driver x race x stint
        # ---------------------------------
        """
        CREATE TABLE IF NOT EXISTS fact_pitstops (
            pitstop_key SERIAL PRIMARY KEY,

            season_key INTEGER NOT NULL
                REFERENCES dim_seasons(season_key),
            race_key INTEGER NOT NULL
                REFERENCES dim_races(race_key),
            driver_key INTEGER NOT NULL
                REFERENCES dim_drivers(driver_key),

            stint INTEGER,
            pit_lap INTEGER,
            compound VARCHAR(50),

            CONSTRAINT uq_pitstops
                UNIQUE (race_key, driver_key, stint)
        );
        """,

        # ---------------------------------
        # FACT TIRE DEGRADATION
        # Grain: 1 driver x race x stint
        # ---------------------------------
        """
        CREATE TABLE IF NOT EXISTS fact_tire_degradation (
            tire_degradation_key SERIAL PRIMARY KEY,

            season_key INTEGER NOT NULL
                REFERENCES dim_seasons(season_key),
            race_key INTEGER NOT NULL
                REFERENCES dim_races(race_key),
            driver_key INTEGER NOT NULL
                REFERENCES dim_drivers(driver_key),

            compound VARCHAR(50),
            stint INTEGER,
            stint_length INTEGER,

            avg_pace DOUBLE PRECISION,
            first_three_avg DOUBLE PRECISION,
            last_three_avg DOUBLE PRECISION,
            pace_dropoff DOUBLE PRECISION,
            degradation_rate DOUBLE PRECISION,

            CONSTRAINT uq_tire_degradation
                UNIQUE (race_key, driver_key, stint)
        );
        """,
    ]

    try:

        # Stop with an actionable message if an existing fact table has
        # drifted from the shape below (a stale UNIQUE key, etc.).
        assert_schema_current(cursor, FACT_CONFLICT_KEYS)

        for query in create_queries:
            cursor.execute(query)

        conn.commit()

        print("All fact tables ready")

    except Exception as e:

        conn.rollback()

        print("Error creating fact tables:")
        print(e)

        raise

    finally:

        cursor.close()
        conn.close()


if __name__ == "__main__":
    create_facts()
