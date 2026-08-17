# Changelog

All notable changes to this project are logged here, newest first. This
log started 2026-08-17 as part of fixing correctness bugs found during an
ETL review; every change from that point forward is recorded, not just
bug fixes.

## 2026-08-17

### Fixed

- **Round-ordering corruption in `build_championship_standings.py`**:
  `Round` was assigned via `enumerate(raw_folder.iterdir(), start=1)`,
  which follows filesystem/OS iteration order, not chronological season
  order. This silently miscomputed `CumulativePoints` and
  `ChampionshipPosition` for every race. Now derives `Round` from the
  actual FastF1 event schedule via `src/utils/schedule.get_round_map()`.
  Verified against real 2025 results: Round 1 now correctly shows
  NOR/VER/RUS podium at the Australian GP, and the final-round standings
  (Round 24, Abu Dhabi) correctly show NOR leading the championship.

- **Same root cause in `build_driver_dimension.py`**: `dim_driver`'s
  "most recent team" was chosen via
  `drop_duplicates(subset="DriverNumber", keep="last")` after sorting only
  by `DriverNumber` — "last" was effectively arbitrary filesystem order,
  not chronologically latest. Now sorts by `[DriverNumber, Round]` (using
  the same schedule-derived round map) before deduplicating, so "last"
  means the actual most recent race.

- **Same root cause in `build_race_dimension.py`**: race folder names were
  `sorted()` alphabetically and positionally zipped against the schedule
  sorted by `RoundNumber` — alphabetical order does not match chronological
  order (e.g. `abu_dhabi` sorted first but is the final round of the
  season), so every round was mislabeled with the wrong country/location/
  date. Now derives each round's folder name directly from its
  `EventName` via `get_race_folder_name()`, with an explicit check that
  raises if any expected folder is missing (previously only checked that
  the *counts* matched, which couldn't catch a mismatched pairing).

- **Broken file reference in `build_pitstop_summary.py`**: read
  `fact_driver_stints.csv`, but `build_driver_stints.py` writes
  `fact_driver_stints_{year}.csv`. This stage could not run at all before
  this fix (`FileNotFoundError` every time).

- **Partial-race gap in `race_data.py` extraction**: a race was skipped
  entirely if `laps.csv` existed, without checking `results.csv` or
  `weather.csv`. If extraction crashed after writing `laps.csv` but before
  the other two files, a rerun would silently skip that race forever,
  leaving `results.csv`/`weather.csv` permanently missing. Now checks all
  three files before skipping.

- **Non-atomic writes in `race_data.py` and `driver_telemetry.py`**: CSVs
  were written directly to their final filename, so a crash mid-write
  could leave a truncated/corrupt file that a later run's
  file-existence-based skip check would treat as complete. Both now write
  to a `.tmp` file and rename into place.

### Added

- `src/utils/schedule.py`: shared helper (`get_race_folder_name`,
  `get_round_map`) so folder-naming and round-order logic exists in one
  place instead of being re-implemented (and re-broken) in every script
  that needs it. Used by `race_data.py`, `driver_telemetry.py`,
  `build_championship_standings.py`, `build_driver_dimension.py`, and
  `build_race_dimension.py`.
- This changelog.
- `__pycache__/` to `.gitignore` (bytecode cache directories were showing
  up as untracked after running the scripts above to verify the fixes).

### Verification performed

- All edited files pass `python -m py_compile`.
- `build_race_dimension.py`, `build_driver_dimension.py`,
  `build_championship_standings.py`, `build_driver_stints.py`, and
  `build_pitstop_summary.py` were re-run against real 2025 season data end
  to end; outputs regenerated successfully.
- Spot-checked `fact_championship_standings_2025.csv` against known real
  2025 results (Australian GP round-1 podium, final standings order) —
  matches.

### Not changed in this pass

- No changes were made to the Postgres/database work — that remains a
  self-directed learning exercise per `Learning material/postgres-f1-pipeline/`.
- Did not restructure `build_pitstop_summary.py` or `build_race_dimension.py`
  into the function + `if __name__` pattern the rest of the transform
  scripts use — that's a style/consistency cleanup, not a correctness fix,
  and was left out to keep this change minimal and scoped to the actual
  bugs.
