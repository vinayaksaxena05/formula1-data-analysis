import sys
import pandas as pd
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))

from src.utils.cli import get_year


def build_season_dimension(year=2025):

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

    if len(races) == 0:

        raise ValueError(
            f"No race data found for {year}"
        )

    dim_season = pd.DataFrame(
        [
            {"SeasonYear": year}
        ]
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
        / "dim_seasons.csv"
    )

    dim_season.to_csv(
        output_file,
        index=False
    )

    print("\n--------------------------------")
    print("Dimension complete")
    print(
        f"Created {len(dim_season)} season record"
    )
    print(
        f"Saved to {output_file}"
    )


if __name__ == "__main__":
    year = get_year(default=2025)
    build_season_dimension(year=year)
