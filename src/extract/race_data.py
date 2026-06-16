import fastf1
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]

# Cache
CACHE_DIR = ROOT_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

fastf1.Cache.enable_cache(str(CACHE_DIR))


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

        folder_name = (
            race_name.lower()
            .replace(" ", "_")
        )

        race_folder = (
            ROOT_DIR
            / "data"
            / "raw"
            / str(year)
            / folder_name
        )

        laps_file = race_folder / "laps.csv"

        print("\n----------------------------------------")
        print(f"Race: {race_name}")
        print(f"Folder: {race_folder}")
        print(f"Laps file: {laps_file}")
        print(f"Exists: {laps_file.exists()}")

        if laps_file.exists():
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
        session.laps.to_csv(
            race_folder / "laps.csv",
            index=False
        )

        print("Saving results...")
        session.results.to_csv(
            race_folder / "results.csv",
            index=False
        )

        print("Saving weather...")
        session.weather_data.to_csv(
            race_folder / "weather.csv",
            index=False
        )

        print(f"Finished {race_name}")

    print("\nAll races processed")


if __name__ == "__main__":
    extract_race_data()