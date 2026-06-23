import pandas as pd
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]


def build_driver_race_metrics(year=2025):

    print(f"Project root: {ROOT_DIR}")

    raw_folder = (ROOT_DIR/"data"/"raw"/str(year))

    print(f"Raw folder: {raw_folder}")

    if not raw_folder.exists():
        raise FileNotFoundError(f"Could not find {raw_folder}")

    races = [race for race in raw_folder.iterdir() if race.is_dir()]

    print(f"Found {len(races)} races")

    all_pace_metrics = []

    for race_folder in races:
        race_name = race_folder.name
        print("\n--------------------------------")
        print(f"Processing {race_name}")
        results_file = (race_folder/"results.csv")

        laps_file = (race_folder/"laps.csv")

        if (not results_file.exists() or not laps_file.exists()):

            print(f"Skipping {race_name} "f"(missing files)")
            continue

        laps_data = pd.read_csv(laps_file)
        print(f"Loaded "f"{len(laps_data)} lap records")
        required_columns = ["Driver","LapTime"]
        missing_columns = [col for col in required_columns if col not in laps_data.columns]

        if missing_columns:
            print(f"Missing columns: "f"{missing_columns}")
            continue

        laps_data = laps_data[laps_data["LapTime"].notna()].copy()

        if "TrackStatus" in laps_data.columns:
            laps_data = laps_data[laps_data["TrackStatus"].astype(str)== "1"]

        if laps_data.empty:
            print(f"No valid laps "f"for {race_name}")
            continue

        laps_data["LapTime"] = (pd.to_timedelta(laps_data["LapTime"]).dt.total_seconds())

        race_median = (laps_data["LapTime"].median())
        race_fastest = (laps_data["LapTime"].min())

        for driver in (laps_data["Driver"].unique()):

            driver_laps = laps_data[laps_data["Driver"]== driver]

            if len(driver_laps) < 5:
                continue

            representative_pace = (driver_laps["LapTime"].median())
            fastest_lap = (driver_laps["LapTime"].min())
            pace_std = (driver_laps["LapTime"].std())

            relative_pace = (representative_pace/ race_median)

            fastest_lap_delta = (fastest_lap- race_fastest)

            all_pace_metrics.append(
                {
                    "Race": race_name,
                    "Driver": driver,
                    "RepresentativePace":
                        representative_pace,
                    "RelativePace":
                        relative_pace,
                    "FastestLapDelta":
                        fastest_lap_delta,
                    "PaceStdDev":
                        pace_std
                }
            )

        print(f"Processed "f"{laps_data['Driver'].nunique()} "f"drivers")

    if len(all_pace_metrics) == 0:
        raise ValueError(
            "No pace metrics generated"
        )

    driver_race_metrics = pd.DataFrame(all_pace_metrics)

    output_folder = (ROOT_DIR/ "data"/ "processed")

    output_folder.mkdir(parents=True,exist_ok=True)

    output_file = (output_folder/ f"fact_driver_race_metrics_{year}.csv")

    driver_race_metrics.to_csv(output_file,index=False)

    print("\n--------------------------------")
    print("Transformation complete")
    print(f"Created "f"{len(driver_race_metrics)} "f"records")
    print(f"Saved to "f"{output_file}")


if __name__ == "__main__":
    build_driver_race_metrics()