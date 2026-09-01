import sys
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT_DIR))

from src.utils.cli import get_year

year = get_year(default=2025)

print(f"Project Root: {ROOT_DIR}")

stints = pd.read_csv(
    ROOT_DIR / "data" / "processed" / f"fact_driver_stints_{year}.csv"
)

stints = stints.sort_values(
    ["Race", "Driver", "Stint"]
)

stints["PitLap"] = (
    stints.groupby(["Race", "Driver"])["Laps"]
    .transform(lambda x: x.cumsum().shift())
)

pitstops = stints[stints["Stint"] > 1].copy()

pitstops["PitLap"] = pitstops["PitLap"].astype(int)

pitstops = pitstops[
    [
        "Race",
        "Driver",
        "Stint",
        "PitLap",
        "Compound"
    ]
]

pitstops.to_csv(
    ROOT_DIR
    / "data"
    / "processed"
    / f"fact_pitstops_{year}.csv",
    index=False
)

print("Pitstop summary created")
print(pitstops.head())