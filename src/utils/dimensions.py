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
    order_by: str | None = None,
) -> pd.DataFrame:
    """Merge new dimension rows into an existing cumulative dimension CSV.

    If ``output_file`` exists its rows are read and combined with
    ``new_rows``, then duplicate natural keys are dropped. ``keep="last"``
    lets the winning row's view of an entity win (SCD type 1 overwrite);
    ``keep="first"`` preserves the earliest stored row.

    Without ``order_by``, "last" means whichever run happened most
    recently -- not whichever season is chronologically latest. Pass
    ``order_by`` (e.g. a column recording the season that produced each
    row) to sort by that first, so re-running an older season after a
    newer one does not revert the newer season's attributes. Rows
    missing ``order_by`` (pre-existing data from before it was tracked)
    sort first, so real values always outrank untracked ones.

    The merged frame is returned unsorted by anything but ``order_by``
    -- the caller applies its own display ordering before writing it out.
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

    if order_by is not None:
        combined = combined.sort_values(
            order_by,
            kind="stable",
            na_position="first",
        ).reset_index(drop=True)

    combined = combined.drop_duplicates(
        subset=subset,
        keep=keep,
    )

    return combined.reset_index(drop=True)


def write_dimension_csv(df: pd.DataFrame, output_file: Path) -> None:
    """Write a dimension CSV atomically.

    ``DataFrame.to_csv`` truncates the target before streaming rows, so
    a process killed mid-write (OOM, Ctrl-C, power loss) can leave a
    dimension file empty or truncated -- costly here because these files
    are the cumulative, multi-season source of truth that merge_dimension
    reads back on the next run. Writing to a temp file and replacing the
    target in one filesystem operation avoids that window.
    """

    temp_file = output_file.with_suffix(output_file.suffix + ".tmp")

    df.to_csv(temp_file, index=False)

    temp_file.replace(output_file)
