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


def extract_telemetry(year=2026):

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

        telemetry_folder = (
            ROOT_DIR
            / "data"
            / "raw"
            / str(year)
            / folder_name
            / "telemetry"
        )

        print("\n----------------------------------------")
        print(f"Processing {race_name}")

        telemetry_folder.mkdir(
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

        print(f"Found {len(session.drivers)} drivers")

        for driver in session.drivers:

            driver_name = session.get_driver(
                driver
            )["Abbreviation"]

            file_path = (
                telemetry_folder
                / f"{driver_name}.csv"
            )

            if file_path.exists():
                print(
                    f"Skipping {driver_name}"
                )
                continue

            driver_laps = (
                session.laps
                .pick_drivers(driver)
            )

            if driver_laps.empty:
                print(
                    f"No lap data for {driver_name}"
                )
                continue

            try:

                print(
                    f"Saving telemetry for {driver_name}"
                )

                telemetry = (
                    driver_laps
                    .get_telemetry()
                )

                temp_path = file_path.with_suffix(
                    file_path.suffix + ".tmp"
                )

                telemetry.to_csv(
                    temp_path,
                    index=False
                )

                temp_path.replace(file_path)

            except Exception as e:

                print(
                    f"Failed for {driver_name}: {e}"
                )

                continue

        print(f"Finished {race_name}")

    print("\nAll telemetry processed")


if __name__ == "__main__":
    extract_telemetry()