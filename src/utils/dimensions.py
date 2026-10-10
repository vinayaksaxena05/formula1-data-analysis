"""Helpers for cumulative, natural-key dimension tables.

Dimensions in this project are cumulative across seasons: a pipeline run
for one season merges its rows into whatever is already stored rather than
replacing the file. Anything kept in a dimension is expected to be stable
for the lifetime of its natural key. Season-varying attributes (a driver's
team, a car number, a team's livery colour) are per-season facts and do
not belong here.
"""

from pathlib import Path

import pandas as pd


def merge_dimension(
    new_rows: pd.DataFrame,
    output_file: Path,
    key: str | list[str],
    keep: str = "last",
) -> pd.DataFrame:
    """Merge new dimension rows into an existing cumulative dimension CSV.

    If ``output_file`` exists its rows are read and combined with
    ``new_rows``, then duplicate natural keys are dropped. ``keep="last"``
    lets the current run's view of an entity win (SCD type 1 overwrite);
    ``keep="first"`` preserves the earliest stored row.

    The merged frame is returned unsorted -- the caller applies its own
    ordering before writing it out.
    """

    subset = [key] if isinstance(key, str) else list(key)

    if not output_file.exists():
        return new_rows.reset_index(drop=True)

    existing = pd.read_csv(output_file)

    missing = [col for col in subset if col not in existing.columns]

    if missing:
        raise ValueError(
            f"{output_file} is missing key column(s): {missing}"
        )

    combined = pd.concat(
        [existing, new_rows],
        ignore_index=True,
    )

    combined = combined.drop_duplicates(
        subset=subset,
        keep=keep,
    )

    return combined.reset_index(drop=True)
