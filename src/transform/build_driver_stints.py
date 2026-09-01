import sys
import pandas as pd
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))

from src.utils.cli import get_year


def build_driver_stints(year=2025):

    print(f"Project root: {ROOT_DIR}")

    raw_folder = (
        ROOT_DIR
        / "data"
        / "raw"
        / str(year)
    )

    print(f"Raw folder: {raw_folder}")

    if not raw_folder.exists():

        raise FileNotFoundError(
            f"Could not find {raw_folder}"
        )

    races = [
        race
        for race in raw_folder.iterdir()
        if race.is_dir()
    ]

    print(f"Found {len(races)} races")

    all_stints = []

    for race_folder in races:

        race_name = race_folder.name

        print("\n--------------------------------")
        print(f"Processing {race_name}")

        laps_file = race_folder / "laps.csv"

        if not laps_file.exists():

            print(
                f"Skipping {race_name} "
                f"(laps.csv not found)"
            )

            continue

        laps = pd.read_csv(laps_file)

        print(
            f"Loaded {len(laps)} lap records"
        )

        required_columns = [
            "Driver",
            "Stint",
            "Compound",
            "LapNumber",
            "LapTime"
        ]

        missing_columns = [
            col
            for col in required_columns
            if col not in laps.columns
        ]

        if missing_columns:

            print(
                f"Missing columns: "
                f"{missing_columns}"
            )

            continue

        before_rows = len(laps)

        laps = laps[
            laps["LapTime"].notna()
        ]

        after_rows = len(laps)

        print(
            f"Removed "
            f"{before_rows - after_rows} "
            f" rows with missing LapTime"
        )

        if laps.empty:

            print(
                f"No valid lap data "
                f"for {race_name}"
            )

            continue

        # Convert LapTime to timedelta
        laps["LapTime"] = pd.to_timedelta(
            laps["LapTime"],
            errors="coerce"
        )

        laps = laps[
            laps["LapTime"].notna()
        ]

        stints = (
            laps
            .groupby(
                [
                    "Driver",
                    "Stint",
                    "Compound"
                ]
            )
            .agg(
                Laps=(
                    "LapNumber",
                    "count"
                ),
                AvgLapTime=(
                    "LapTime",
                    "mean"
                ),
                FastestLap=(
                    "LapTime",
                    "min"
                )
            )
            .reset_index()
        )

        stints["Race"] = race_name

        stints = stints[
            [
                "Race",
                "Driver",
                "Stint",
                "Compound",
                "Laps",
                "AvgLapTime",
                "FastestLap"
            ]
        ]

        print(
            f"Created "
            f"{len(stints)} stint records"
        )

        all_stints.append(stints)

    if len(all_stints) == 0:

        raise ValueError(
            "No stint data generated"
        )

    driver_stints = pd.concat(
        all_stints,
        ignore_index=True
    )

    print("\nPreview:")
    print(driver_stints.head())

    output_folder = (
        ROOT_DIR
        / "data"
        / "processed"
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_folder
        / f"fact_driver_stints_{year}.csv"
    )

    driver_stints.to_csv(
        output_file,
        index=False
    )

    print("\n--------------------------------")
    print("Transformation complete")
    print(
        f"Created {len(driver_stints)} records"
    )
    print(
        f"Saved to {output_file}"
    )


if __name__ == "__main__":
    year = get_year(default=2025)
    build_driver_stints(year=year)
