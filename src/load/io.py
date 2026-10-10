"""Shared IO and value-coercion helpers for the load layer.

``load_dimensions`` and ``load_facts`` both read season CSVs from
``data/processed/`` and both have to hand pandas/numpy scalars to
psycopg2, which cannot adapt numpy types. These helpers were previously
duplicated (and only ``load_facts`` had the numpy/NaN handling).
"""

from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]

PROCESSED_FOLDER = ROOT_DIR / "data" / "processed"


def get_csv(filename: str) -> pd.DataFrame:
    """Read a CSV from ``data/processed/``, with a clear error if absent."""

    file = PROCESSED_FOLDER / filename

    if not file.exists():

        raise FileNotFoundError(
            f"\nRequired file not found:\n{file}"
        )

    return pd.read_csv(file)


def to_native(value):
    """Coerce a pandas/numpy scalar to a plain Python type for psycopg2.

    numpy ``int64`` / ``float64`` / ``bool_`` become ``int`` / ``float`` /
    ``bool``; any NaN / NaT becomes ``None``. Strings and already-native
    values pass through untouched.
    """

    if value is None:

        return None

    if hasattr(value, "item"):

        value = value.item()

    if isinstance(value, float) and pd.isna(value):

        return None

    return value


def nan_to_none(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with every NaN / NaT replaced by ``None``."""

    return df.astype(object).where(pd.notna(df), None)
