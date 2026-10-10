import sys
import pandas as pd
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))

from src.utils.cli import get_year
from src.utils.dimensions import merge_dimension


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

    # Driver identity attributes (name, nationality) don't change across a
    # season, so unlike the old team-carrying version of this dimension,
    # there's no need to track round order here to find the "most recent"
    # row -- any race's results row for a driver gives the same identity
    # attributes. Team is intentionally NOT included: it belongs in
    # fact_driver_results, since a driver's team is a per-race fact, not a
    # permanent attribute of the driver (drivers change teams between
    # seasons, and the old TeamName column here could not represent that).
    required_columns = [
        "DriverNumber",
        "Abbreviation",
        "FirstName",
        "LastName",
        "FullName",
        "CountryCode"
    ]

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
        .drop_duplicates(
            subset="Abbreviation",
            keep="first"
        )
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

    # No year in the filename: the driver dimension is cumulative across
    # seasons and keyed on Abbreviation. Team is deliberately excluded
    # (see note above), so the only per-season drift here is DriverNumber,
    # which takes the latest season's value.
    output_file = (
        output_folder
        / "dim_drivers.csv"
    )

    dim_driver = merge_dimension(
        dim_driver,
        output_file,
        key="Abbreviation"
    )

    dim_driver = (
        dim_driver
        .sort_values("DriverNumber")
        .reset_index(drop=True)
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
    year = get_year(default=2025)
    build_driver_dimension(year=year)
