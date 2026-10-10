import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from src.utils.pipeline_cache import (
    is_completed,
    mark_completed,
    get_file_fingerprint,
)


ROOT_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(ROOT_DIR))

from src.utils.cli import get_year


# Every src/load/ entry script imports some subset of these shared
# helpers. Fingerprinting only the entry script would let a bug fix in
# one of these go undetected, leaving the stage wrongly marked "cache
# valid" and skipped. Fingerprinting the full set for every src/load/
# stage over-includes a little (e.g. create_views.py doesn't use io.py)
# but never under-invalidates, which is the failure mode that matters.
SHARED_LOAD_FILES = [
    "src/load/connection.py",
    "src/load/schema.py",
    "src/load/io.py",
]


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


def run_script(
    script_path,
    stage,
    year=2025,
    force=False,
    dependencies=None,
    extra_fingerprint_files=None
):
    """
    Run a pipeline script unless the stage has already completed
    and its dependencies are still valid.
    """

    script = ROOT_DIR / script_path

    if not script.exists():
        raise FileNotFoundError(
            f"Pipeline script not found: {script}"
        )

    fingerprint_paths = [script] + [
        ROOT_DIR / extra_file
        for extra_file in (extra_fingerprint_files or [])
    ]

    fingerprint = get_file_fingerprint(fingerprint_paths)

    if not force and is_completed(
        stage,
        year,
        fingerprint=fingerprint,
        dependencies=dependencies
    ):
        log(f"SKIPPING {stage}: cache valid for {year}")
        return

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

    mark_completed(
        stage,
        year,
        fingerprint=fingerprint,
        dependencies=dependencies
    )

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
        log(
            "Force mode enabled: all stages will re-run "
            "regardless of cache"
        )

    try:

        # --------------------------------------------------
        # 1. EXTRACT
        # --------------------------------------------------

        log("STEP 1: Extraction")

        run_script(
            "src/extract/race_data.py",
            "extract_race_data",
            year,
            force=force,
            dependencies=[]
        )

        run_script(
            "src/extract/driver_telemetry.py",
            "extract_driver_telemetry",
            year,
            force=force,
            dependencies=[]
        )


        # --------------------------------------------------
        # 2. TRANSFORM
        # --------------------------------------------------

        log("STEP 2: Transformation")

        transform_stages = [

            (
                "src/transform/build_season_dimension.py",
                "transform_season",
                ["extract_race_data"]
            ),

            (
                "src/transform/build_team_dimension.py",
                "transform_teams",
                ["extract_race_data"]
            ),

            (
                "src/transform/build_driver_dimension.py",
                "transform_drivers",
                ["extract_race_data"]
            ),

            (
                "src/transform/build_race_dimension.py",
                "transform_races",
                ["extract_race_data"]
            ),

            (
                "src/transform/build_championship_standings.py",
                "transform_championship",
                [
                    "transform_season",
                    "transform_teams",
                    "transform_drivers",
                    "transform_races"
                ]
            ),

            (
                "src/transform/build_driver_braking_metrics.py",
                "transform_braking",
                ["extract_driver_telemetry"]
            ),

            (
                "src/transform/build_driver_pace_metrics.py",
                "transform_pace",
                ["extract_race_data"]
            ),

            (
                "src/transform/build_driver_race_telemetry_metrics.py",
                "transform_race_telemetry",
                ["extract_driver_telemetry"]
            ),

            (
                "src/transform/build_driver_stints.py",
                "transform_stints",
                ["extract_race_data"]
            ),

            (
                "src/transform/build_pitstop_summary.py",
                "transform_pitstops",
                ["extract_race_data"]
            ),

            (
                "src/transform/build_tire_degradation_analysis.py",
                "transform_tire_degradation",
                ["transform_stints"]
            ),
        ]

        for script, stage, dependencies in transform_stages:

            run_script(
                script,
                stage,
                year,
                force=force,
                dependencies=dependencies
            )


        # --------------------------------------------------
        # 3. CREATE / LOAD DIMENSIONS
        # --------------------------------------------------

        log("STEP 3: Loading dimensions")

        run_script(
            "src/load/create_dimensions.py",
            "create_dimensions",
            year,
            force=force,
            dependencies=[
                "transform_season",
                "transform_teams",
                "transform_drivers",
                "transform_races"
            ],
            extra_fingerprint_files=SHARED_LOAD_FILES
        )

        run_script(
            "src/load/load_dimensions.py",
            "load_dimensions",
            year,
            force=force,
            dependencies=[
                "create_dimensions"
            ],
            extra_fingerprint_files=SHARED_LOAD_FILES
        )


        # --------------------------------------------------
        # 4. CREATE / LOAD FACTS
        # --------------------------------------------------

        log("STEP 4: Loading facts")

        run_script(
            "src/load/create_facts.py",
            "create_facts",
            year,
            force=force,
            dependencies=[
                "transform_championship",
                "transform_braking",
                "transform_pace",
                "transform_race_telemetry",
                "transform_stints",
                "transform_pitstops",
                "transform_tire_degradation"
            ],
            extra_fingerprint_files=SHARED_LOAD_FILES
        )

        run_script(
            "src/load/load_facts.py",
            "load_facts",
            year,
            force=force,
            dependencies=[
                "create_facts",
                "load_dimensions"
            ],
            extra_fingerprint_files=SHARED_LOAD_FILES
        )


        # --------------------------------------------------
        # 5. VISUALIZATION VIEWS
        # --------------------------------------------------

        log("STEP 5: Creating visualization views")

        run_script(
            "src/load/create_views.py",
            "create_views",
            year,
            force=force,
            dependencies=[
                "load_dimensions",
                "load_facts"
            ],
            extra_fingerprint_files=SHARED_LOAD_FILES
        )


        # --------------------------------------------------
        # 6. DATA QUALITY VALIDATION
        # --------------------------------------------------

        log("STEP 6: Data quality validation")

        run_script(
            "src/load/validate_pipeline.py",
            "validation",
            year,
            force=force,
            dependencies=[
                "create_views"
            ],
            extra_fingerprint_files=SHARED_LOAD_FILES
        )


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