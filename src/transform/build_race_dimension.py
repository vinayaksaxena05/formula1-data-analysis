import sys
from pathlib import Path
import pandas as pd
import fastf1

ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))

from src.utils.schedule import get_race_folder_name
from src.utils.cli import get_year

year = get_year(default=2025)

processed_folder = ROOT_DIR / "data" / "processed"
processed_folder.mkdir(parents=True, exist_ok=True)

raw_folder = ROOT_DIR / "data" / "raw" / str(year)

season = fastf1.get_event_schedule(year)

# Only actual races
dim_races = season[season["RoundNumber"] > 0][
    [
        "RoundNumber",
        "EventName",
        "Country",
        "Location",
        "OfficialEventName",
        "EventDate",
        "EventFormat"
    ]
].copy()

# Derive each round's Race folder name directly from its EventName,
# instead of positionally zipping a sorted folder list against a
# round-sorted schedule (alphabetical folder order does not match
# chronological round order, e.g. "abu_dhabi" sorts first but races last).
dim_races["Race"] = dim_races["EventName"].apply(get_race_folder_name)

dim_races = dim_races.drop(columns=["EventName"])

existing_folders = {
    folder.name
    for folder in raw_folder.iterdir()
    if folder.is_dir()
}

missing_folders = set(dim_races["Race"]) - existing_folders

if missing_folders:
    raise ValueError(
        f"Missing raw data folders for rounds: {sorted(missing_folders)}"
    )

# Sort schedule by round
dim_races = dim_races.sort_values("RoundNumber").reset_index(drop=True)

dim_races = dim_races[
    [
        "RoundNumber",
        "Race",
        "Country",
        "Location",
        "OfficialEventName",
        "EventDate",
        "EventFormat"
    ]
]

dim_races["SprintWeekend"] = dim_races["EventFormat"].apply(
    lambda x: "Y" if "sprint" in x.lower() else "N"
)

# EventFormat is kept (not dropped) alongside the derived SprintWeekend
# flag -- the warehouse's dim_race stores both the raw FastF1 event format
# and the boolean convenience flag.

output_file = processed_folder / f"dim_races_{year}.csv"

dim_races.to_csv(
    output_file,
    index=False
)

print(dim_races.head())