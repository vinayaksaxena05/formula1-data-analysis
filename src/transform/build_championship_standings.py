import pandas as pd
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]


def build_championship_standings(year=2025):

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

    all_results = []

    for round_num, race_folder in enumerate(races, start=1):

        race_name = race_folder.name

        print("\n--------------------------------")
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

        print(
            f"Loaded {len(results)} result records"
        )

        required_columns = [
            "Abbreviation",
            "Position",
            "Points",
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

        standings = results[
            required_columns
        ].copy()

        standings["Race"] = race_name
        standings["Round"] = round_num

        standings = standings[
            [
                "Round",
                "Race",
                "Abbreviation",
                "Position",
                "Points",
                "TeamName"
            ]
        ]

        print(
            f"Added "
            f"{len(standings)} drivers"
        )

        all_results.append(standings)

    if len(all_results) == 0:

        raise ValueError(
            "No standings data generated"
        )

    standings = pd.concat(
        all_results,
        ignore_index=True
    )

    standings = standings.sort_values(
        ["Abbreviation", "Round"]
    )

    standings["CumulativePoints"] = (
        standings
        .groupby("Abbreviation")["Points"]
        .cumsum()
    )

    standings["ChampionshipPosition"] = (
        standings
        .groupby("Round")["CumulativePoints"]
        .rank(
            ascending=False,
            method="min"
        )
    )

    standings = standings[
        [
            "Round",
            "Race",
            "Abbreviation",
            "TeamName",
            "Position",
            "Points",
            "CumulativePoints",
            "ChampionshipPosition"
        ]
    ]

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
        / f"fact_championship_standings_{year}.csv"
    )

    standings.to_csv(
        output_file,
        index=False
    )

    print("\n--------------------------------")
    print("Transformation complete")
    print(
        f"Created {len(standings)} records"
    )
    print(
        f"Saved to {output_file}"
    )


if __name__ == "__main__":
    build_championship_standings()