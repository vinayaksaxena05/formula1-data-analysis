from pathlib import Path
import pandas as pd
import fastf1

ROOT_DIR = Path(__file__).resolve().parents[2]

year = 2025

processed_folder = ROOT_DIR / "data" / "processed"
processed_folder.mkdir(parents=True, exist_ok=True)

season = fastf1.get_event_schedule(year)

dim_races = season[season["RoundNumber"] > 0][
    [
        "RoundNumber",
        "Country",
        "Location",
        "OfficialEventName",
        "EventDate",
        "EventFormat"
    ]
].copy()

dim_races["SprintWeekend"] = dim_races["EventFormat"].apply(
    lambda event: "Y" if "sprint" in event.lower() else "N"
)

dim_races = dim_races.drop(columns=["EventFormat"])

output_file = processed_folder / f"dim_races_{year}.csv"

dim_races.to_csv(output_file, index=False)

dim_races