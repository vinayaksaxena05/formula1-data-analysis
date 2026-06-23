import pandas as pd
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]


def build_tire_degradation_metrics(year=2025):

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

    all_degradation_metrics = []

    for race_folder in races:

        race_name = race_folder.name

        print("\n--------------------------------")
        print(f"Processing {race_name}")

        laps_file = (
            race_folder
            / "laps.csv"
        )

        if not laps_file.exists():

            print(
                f"Skipping {race_name} "
                f"(laps.csv not found)"
            )

            continue

        laps = pd.read_csv(
            laps_file
        )

        print(
            f"Loaded "
            f"{len(laps)} lap records"
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
        ].copy()

        after_rows = len(laps)

        print(
            f"Removed "
            f"{before_rows - after_rows} "
            f"rows with missing LapTime"
        )

        if laps.empty:

            print(
                f"No valid lap data "
                f"for {race_name}"
            )

            continue

        laps["LapTime"] = (
            pd.to_timedelta(
                laps["LapTime"]
            )
            .dt.total_seconds()
        )

        stints = laps.groupby(
            [
                "Driver",
                "Stint",
                "Compound"
            ]
        )

        stint_count = 0

        for (
            driver,
            stint,
            compound
        ), stint_laps in stints:

            if len(stint_laps) < 6:

                continue

            stint_laps = (
                stint_laps
                .sort_values(
                    "LapNumber"
                )
            )

            avg_pace = (
                stint_laps["LapTime"]
                .mean()
            )

            first_three_avg = (
                stint_laps
                .head(3)["LapTime"]
                .mean()
            )

            last_three_avg = (
                stint_laps
                .tail(3)["LapTime"]
                .mean()
            )

            pace_dropoff = (
                last_three_avg
                - first_three_avg
            )

            degradation_rate = (
                pace_dropoff
                / len(stint_laps)
            )

            all_degradation_metrics.append(
                {
                    "Race": race_name,
                    "Driver": driver,
                    "Compound": compound,
                    "Stint": stint,
                    "StintLength":
                        len(stint_laps),
                    "AvgPace":
                        avg_pace,
                    "FirstThreeAvg":
                        first_three_avg,
                    "LastThreeAvg":
                        last_three_avg,
                    "PaceDropoff":
                        pace_dropoff,
                    "DegradationRate":
                        degradation_rate
                }
            )

            stint_count += 1

        print(
            f"Created "
            f"{stint_count} "
            f"stint degradation records"
        )

    if len(all_degradation_metrics) == 0:

        raise ValueError(
            "No degradation metrics generated"
        )

    tire_degradation = pd.DataFrame(
        all_degradation_metrics
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
        / f"fact_tire_degradation_{year}.csv"
    )

    tire_degradation.to_csv(
        output_file,
        index=False
    )

    print("\n--------------------------------")
    print("Transformation complete")
    print(
        f"Created "
        f"{len(tire_degradation)} "
        f"records"
    )
    print(
        f"Saved to "
        f"{output_file}"
    )


if __name__ == "__main__":
    build_tire_degradation_metrics()