import sys
import pandas as pd
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))

from src.utils.cli import get_year


def build_braking_metrics(year=2025):

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

    all_braking_metrics = []

    for race_folder in races:

        race_name = race_folder.name

        print("\n--------------------------------")
        print(f"Processing {race_name}")

        telemetry_folder = (
            race_folder
            / "telemetry"
        )

        if not telemetry_folder.exists():

            print(
                f"Skipping {race_name} "
                f"(telemetry folder not found)"
            )

            continue

        drivers = [
            driver
            for driver in telemetry_folder.iterdir()
            if driver.suffix == ".csv"
        ]

        print(
            f"Found {len(drivers)} "
            f"driver telemetry files"
        )

        for driver_file in drivers:

            driver_name = (
                driver_file.stem
            )

            telemetry = pd.read_csv(
                driver_file
            )

            required_columns = [
                "Brake",
                "Speed",
                "Distance"
            ]

            missing_columns = [
                col
                for col in required_columns
                if col not in telemetry.columns
            ]

            if missing_columns:

                print(
                    f"Skipping {driver_name} "
                    f"(missing columns: "
                    f"{missing_columns})"
                )

                continue

            telemetry = telemetry[
                telemetry["Distance"].notna()
            ].copy()

            telemetry = telemetry.reset_index(
                drop=True
            )

            braking_events = []

            in_braking_zone = False
            start_idx = None

            for idx, row in telemetry.iterrows():

                brake_active = (
                    row["Brake"] > 0
                )

                if (
                    brake_active
                    and not in_braking_zone
                ):

                    start_idx = idx
                    in_braking_zone = True

                elif (
                    not brake_active
                    and in_braking_zone
                ):

                    end_idx = idx - 1

                    if (
                        start_idx is not None
                        and end_idx > start_idx
                    ):

                        braking_events.append(
                            (
                                start_idx,
                                end_idx
                            )
                        )

                    in_braking_zone = False

            if len(braking_events) == 0:

                continue

            braking_distances = []
            entry_speeds = []
            exit_speeds = []
            speed_reductions = []

            for (
                start_idx,
                end_idx
            ) in braking_events:

                start_row = telemetry.iloc[
                    start_idx
                ]

                end_row = telemetry.iloc[
                    end_idx
                ]

                braking_distance = (
                    end_row["Distance"]
                    - start_row["Distance"]
                )

                entry_speed = (
                    start_row["Speed"]
                )

                exit_speed = (
                    end_row["Speed"]
                )

                speed_reduction = (
                    entry_speed
                    - exit_speed
                )

                braking_distances.append(
                    braking_distance
                )

                entry_speeds.append(
                    entry_speed
                )

                exit_speeds.append(
                    exit_speed
                )

                speed_reductions.append(
                    speed_reduction
                )

            all_braking_metrics.append(
                {
                    "Race": race_name,
                    "Driver": driver_name,
                    "NumBrakingEvents":
                        len(braking_events),
                    "AvgBrakeDistance":
                        sum(
                            braking_distances
                        )
                        / len(
                            braking_distances
                        ),
                    "AvgEntrySpeed":
                        sum(
                            entry_speeds
                        )
                        / len(
                            entry_speeds
                        ),
                    "AvgExitSpeed":
                        sum(
                            exit_speeds
                        )
                        / len(
                            exit_speeds
                        ),
                    "AvgSpeedReduction":
                        sum(
                            speed_reductions
                        )
                        / len(
                            speed_reductions
                        )
                }
            )

        print(
            f"Finished {race_name}"
        )

    if len(all_braking_metrics) == 0:

        raise ValueError(
            "No braking metrics generated"
        )

    braking_metrics = pd.DataFrame(
        all_braking_metrics
    )

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
        / f"fact_braking_metrics_{year}.csv"
    )

    braking_metrics.to_csv(
        output_file,
        index=False
    )

    print("\n--------------------------------")
    print("Transformation complete")
    print(
        f"Created "
        f"{len(braking_metrics)} "
        f"records"
    )
    print(
        f"Saved to "
        f"{output_file}"
    )


if __name__ == "__main__":
    year = get_year(default=2025)
    build_braking_metrics(year=year)
