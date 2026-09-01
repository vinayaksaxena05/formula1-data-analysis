import sys
import pandas as pd
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))

from src.utils.cli import get_year


def build_team_dimension(year=2025):

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

    all_teams = []

    # TeamId is FastF1's stable constructor identifier (e.g. "red_bull"),
    # which survives sponsor/livery-driven TeamName changes better than
    # TeamName alone -- it's the natural key this dimension dedupes on.
    required_columns = [
        "TeamId",
        "TeamName",
        "TeamColor"
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

        teams = results[
            required_columns
        ].copy()

        all_teams.append(teams)

    if len(all_teams) == 0:

        raise ValueError(
            "No team data found"
        )

    dim_team = pd.concat(
        all_teams,
        ignore_index=True
    )

    dim_team = (
        dim_team
        .dropna(subset=["TeamId"])
        .drop_duplicates(
            subset="TeamId",
            keep="first"
        )
        .sort_values("TeamId")
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

    # No year in dimension filename
    output_file = (
        output_folder
        / "dim_teams.csv"
    )

    dim_team.to_csv(
        output_file,
        index=False
    )

    print("\n--------------------------------")
    print("Dimension complete")
    print(
        f"Created {len(dim_team)} teams"
    )
    print(
        f"Saved to {output_file}"
    )


if __name__ == "__main__":
    year = get_year(default=2025)
    build_team_dimension(year=year)
