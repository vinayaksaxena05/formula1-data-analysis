import sys
import fastf1
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))

from src.utils.schedule import get_race_folder_name

# Cache
CACHE_DIR = ROOT_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

fastf1.Cache.enable_cache(str(CACHE_DIR))


def _save_csv_atomic(dataframe, destination):
    """Write via a temp file + replace so a crash mid-write never leaves
    a partial/corrupt CSV at `destination` that a rerun would trust."""

    temp_path = destination.with_suffix(destination.suffix + ".tmp")

    dataframe.to_csv(temp_path, index=False)

    temp_path.replace(destination)


def extract_race_data(year=2026):

    print(f"Project root: {ROOT_DIR}")
    print(f"Cache directory: {CACHE_DIR}")

    schedule = fastf1.get_event_schedule(year)

    races = schedule[
        schedule["EventName"] != "Pre-Season Testing"
    ]

    for _, row in races.iterrows():

        race_name = row["EventName"].replace(
            " Grand Prix",
            ""
        )

        folder_name = get_race_folder_name(row["EventName"])

        race_folder = (
            ROOT_DIR
            / "data"
            / "raw"
            / str(year)
            / folder_name
        )

        laps_file = race_folder / "laps.csv"
        results_file = race_folder / "results.csv"
        weather_file = race_folder / "weather.csv"

        race_complete = (
            laps_file.exists()
            and results_file.exists()
            and weather_file.exists()
        )

        print("\n----------------------------------------")
        print(f"Race: {race_name}")
        print(f"Folder: {race_folder}")
        print(f"Complete: {race_complete}")

        if race_complete:
            print(f"Skipping {race_name}")
            continue

        print(f"Processing {race_name}")

        race_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        session = fastf1.get_session(
            year,
            row["RoundNumber"],
            "R"
        )

        print("Loading session data...")
        session.load()

        print("Saving laps...")
        _save_csv_atomic(session.laps, laps_file)

        print("Saving results...")
        _save_csv_atomic(session.results, results_file)

        print("Saving weather...")
        _save_csv_atomic(session.weather_data, weather_file)

        print(f"Finished {race_name}")

    print("\nAll races processed")


if __name__ == "__main__":
    extract_race_data()