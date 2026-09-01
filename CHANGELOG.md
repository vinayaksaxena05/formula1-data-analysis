# Changelog

All notable changes to this project are logged here, newest first. This
log started 2026-08-17 as part of fixing correctness bugs found during an
ETL review; every change from that point forward is recorded, not just
bug fixes.

## 2026-09-01

### Added

- `run_pipeline.py`: orchestrates the full pipeline (extract → transform →
  load dimensions → load facts → create views → validate) with a
  lightweight local stage cache, so a rerun skips stages that already
  completed for a given season instead of redoing the whole pipeline.
- `src/utils/pipeline_cache.py`: `is_completed(stage, year)`,
  `mark_completed(stage, year)`, `invalidate(stage, year)`,
  `clear_cache(year=None)`, backed by `.pipeline/state.json` (safe
  read/write: falls back to an empty cache on a missing or corrupt state
  file, writes via a temp file + atomic rename). `.pipeline/` added to
  `.gitignore`.
- `--force` flag on `run_pipeline.py`: re-runs every stage regardless of
  cache state. Implemented by stripping `--force` out of `sys.argv` before
  `src.utils.cli.get_year()` parses the remaining args, so the existing
  year-resolution logic (CLI arg or interactive prompt) didn't need to
  change.
- The year resolved by `run_pipeline.py` (via prompt or CLI arg) is now
  passed as `argv[1]` to every child script's `subprocess.run` call, so
  each ETL script's own `get_year()` call picks it up instead of
  independently prompting.

### Fixed

- `pipeline_cache._save_state()` called `json.dump(state, file, ident=4)`
  — `ident` isn't a valid `json.dump` kwarg, so every `mark_completed()`
  call raised `TypeError`. Fixed to `indent=4`.
- `pipeline_cache._load_state()` returned `None` (bare `return`) on a
  corrupt/unreadable state file instead of `{}`, which would crash
  `is_completed()`/`mark_completed()` on the next call. Fixed to return
  `{}`.
- Every `run_script()` call site in `run_pipeline.py` was passing the
  resolved `year` positionally into the `stage` parameter (and never
  passing an actual year), so every stage's cache key collided on the
  same integer value — completing one stage would incorrectly skip all
  the others. All call sites now pass an explicit, unique stage name
  (`extract_race_data`, `transform_season`, `create_dimensions`, etc.).
- `run_script("src/load/create_views.py")` and
  `run_script("src/load/validate_pipeline.py")` were called with no
  `stage` argument at all — `TypeError: missing required positional
  argument`, since `stage` has no default. Fixed by naming these stages
  `create_views` and `validation`.
- `src/load/create_views.py` and `src/load/validate_pipeline.py` printed
  a `✓` checkmark, which crashed with `UnicodeEncodeError` under
  Windows' default `cp1252` console encoding — meaning `create_views`
  (and, transitively, `validation`) could never complete on this machine.
  Both scripts now call `sys.stdout.reconfigure(encoding="utf-8")` right
  after `import sys`.

### Verification performed

- `python -m py_compile` on all edited files.
- Unit-level exercise of `is_completed`/`mark_completed`/`invalidate`/
  `clear_cache` against a real `.pipeline/state.json`, including the
  corrupt-state fallback path.
- `run_script()`'s execute → skip → force-rerun → failure-not-cached
  paths verified against disposable dummy scripts (no real ETL/DB
  touched).
- Verified `--force` argv-stripping against `python run_pipeline.py`,
  `--force`, `2024 --force`, and `--force 2024` — all resolve the correct
  `(year, force)` pair without disturbing `get_year()`'s own parsing.
- Verified year-forwarding: a dummy child script echoing `sys.argv`
  confirmed it receives the resolved year as `argv[1]`.
- Full real run against the 2025 season (`python run_pipeline.py 2025`,
  `python_ds` conda env): extraction, all 11 transforms, and all 4
  Postgres load stages completed and cached correctly; `create_views`
  failed on the pre-existing Unicode bug and was correctly left
  uncached.
- Re-run with no `--force`: all 17 previously-completed stages were
  skipped instantly; only the uncached `create_views` re-attempted.
- After the Unicode fix, `python run_pipeline.py 2025 --force`: full
  pipeline re-ran end to end for real (9m43s) — extraction, transforms,
  dimension/fact loads, view creation, and validation all completed and
  passed every data-quality check (row counts, NULL keys, foreign keys,
  season/race coverage, driver-race grain uniqueness).

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
