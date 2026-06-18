import pandas as pd
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]


def build_driver_dimension(year=2025):

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

    all_drivers = []

    for race_folder in races:

        race_name = race_folder.name

        print(f"Processing {race_name}")

        results_file = (
            race_folder
            / "results.csv"
        )

        if not results_file.exists():

            print(
                f"Skipping {race_name} "
                f"(results.csv not found)"
            )

            continue

        results = pd.read_csv(results_file)

        required_columns = [
            "DriverNumber",
            "Abbreviation",
            "FullName",
            "TeamName"
        ]

        missing_columns = [
            col
            for col in required_columns
            if col not in results.columns
        ]

        if missing_columns:

            print(
                f"Missing columns: "
                f"{missing_columns}"
            )

            continue

        drivers = results[
            required_columns
        ].copy()

        all_drivers.append(drivers)

    if len(all_drivers) == 0:

        raise ValueError(
            "No driver data found"
        )

    dim_driver = pd.concat(
        all_drivers,
        ignore_index=True
    )

    dim_driver = (
        dim_driver
        .drop_duplicates()
        .sort_values("DriverNumber")
        .reset_index(drop=True)
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
        / f"dim_driver_{year}.csv"
    )

    dim_driver.to_csv(
        output_file,
        index=False
    )

    print("\n--------------------------------")
    print("Dimension complete")
    print(
        f"Created {len(dim_driver)} drivers"
    )
    print(
        f"Saved to {output_file}"
    )


if __name__ == "__main__":
    build_driver_dimension()