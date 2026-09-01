import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from src.utils.pipeline_cache import (
    is_completed,
    mark_completed,
)


ROOT_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(ROOT_DIR))

from src.utils.cli import get_year


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def extract_force_flag():
    """
    Pull --force out of sys.argv before src.utils.cli.get_year() parses
    the remaining args. get_year() expects argv[1] to be a bare year (or
    absent, for an interactive prompt), so --force has to be stripped
    out first or it gets passed to int() and blows up.
    """

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--force", action="store_true")

    args, remaining = parser.parse_known_args()

    sys.argv = sys.argv[:1] + remaining

    return args.force


def run_script(script_path, stage, year=2025, force=False):
    """
    Run a pipeline script unless the stage has already completed.
    """

    if not force and is_completed(stage, year):
        log(f"SKIPPING {stage}: already completed for {year}")
        return

    script = ROOT_DIR / script_path

    if not script.exists():
        raise FileNotFoundError(
            f"Pipeline script not found: {script}"
        )

    log(f"Running: {script_path}")

    result = subprocess.run(
        [sys.executable, str(script), str(year)],
        cwd=ROOT_DIR,
        check=False
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Pipeline failed while running {script_path}"
        )

    mark_completed(stage, year)

    log(f"Completed: {stage}")

def main():

    start_time = datetime.now()

    print("=" * 60)
    print("FORMULA 1 DATA PIPELINE")
    print("=" * 60)

    force = extract_force_flag()

    year = get_year(default=2025)

    log(f"Running pipeline for season {year}")

    if force:
        log("Force mode enabled: all stages will re-run regardless of cache")

    try:

        # --------------------------------------------------
        # 1. EXTRACT
        # --------------------------------------------------

        log("STEP 1: Extraction")

        run_script(
            "src/extract/race_data.py",
            "extract_race_data",
            year,
            force=force
        )

        run_script(
            "src/extract/driver_telemetry.py",
            "extract_driver_telemetry",
            year,
            force=force
        )


        # --------------------------------------------------
        # 2. TRANSFORM
        # --------------------------------------------------

        log("STEP 2: Transformation")

        transform_stages = [
            ("src/transform/build_season_dimension.py", "transform_season"),
            ("src/transform/build_team_dimension.py", "transform_teams"),
            ("src/transform/build_driver_dimension.py", "transform_drivers"),
            ("src/transform/build_race_dimension.py", "transform_races"),

            ("src/transform/build_championship_standings.py", "transform_championship"),
            ("src/transform/build_driver_braking_metrics.py", "transform_braking"),
            ("src/transform/build_driver_pace_metrics.py", "transform_pace"),
            ("src/transform/build_driver_race_telemetry_metrics.py", "transform_race_telemetry"),
            ("src/transform/build_driver_stints.py", "transform_stints"),
            ("src/transform/build_pitstop_summary.py", "transform_pitstops"),
            ("src/transform/build_tire_degradation_analysis.py", "transform_tire_degradation"),
        ]

        for script, stage in transform_stages:
            run_script(script, stage, year, force=force)


        # --------------------------------------------------
        # 3. CREATE / LOAD DIMENSIONS
        # --------------------------------------------------

        log("STEP 3: Loading dimensions")

        run_script(
            "src/load/create_dimensions.py",
            "create_dimensions",
            year,
            force=force
        )

        run_script(
            "src/load/load_dimensions.py",
            "load_dimensions",
            year,
            force=force
        )


        # --------------------------------------------------
        # 4. CREATE / LOAD FACTS
        # --------------------------------------------------

        log("STEP 4: Loading facts")

        run_script(
            "src/load/create_facts.py",
            "create_facts",
            year,
            force=force
        )

        run_script(
            "src/load/load_facts.py",
            "load_facts",
            year,
            force=force
        )


        # --------------------------------------------------
        # 5. VISUALIZATION VIEWS
        # --------------------------------------------------

        log("STEP 5: Creating visualization views")

        run_script(
            "src/load/create_views.py",
            "create_views",
            year,
            force=force
        )

        # --------------------------------------------------
        # 6. DATA QUALITY VALIDATION
        # --------------------------------------------------

        log("STEP 6: Data quality validation")

        run_script(
            "src/load/validate_pipeline.py",
            "validation",
            year,
            force=force
        )


        # View creation will be automated in the next step.
        # For now, PostgreSQL views remain managed by SQL files.


        # --------------------------------------------------
        # COMPLETE
        # --------------------------------------------------

        elapsed = datetime.now() - start_time

        print()
        print("=" * 60)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Execution time: {elapsed}")
        print("=" * 60)


    except Exception as error:

        print()
        print("=" * 60)
        print("PIPELINE FAILED")
        print("=" * 60)
        print(error)
        print("=" * 60)

        sys.exit(1)



if __name__ == "__main__":
    main()
