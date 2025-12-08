"""
Shared helpers for the BMY replication pipeline.

These functions mirror common Stata idioms used in the original .do files:
- consistent paths rooted at this folder
- Stata .dta IO with pandas
- groupwise quantiles and lags
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = BASE_DIR / "rawData"
INTERMEDIATE_DIR = BASE_DIR / "intermediateOutput"
OUTPUT_FIGURES_DIR = BASE_DIR / "outputFigures"
TEMP_DIR = BASE_DIR / "temp"


def ensure_directories() -> None:
    """Create expected output folders if they do not exist."""
    for path in (INTERMEDIATE_DIR, OUTPUT_FIGURES_DIR, TEMP_DIR):
        path.mkdir(parents=True, exist_ok=True)


def read_dta(path: Path) -> pd.DataFrame:
    """Read a Stata file with pandas."""
    return pd.read_stata(path)


def write_dta(df: pd.DataFrame, path: Path) -> None:
    """Persist a DataFrame as a Stata .dta file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_stata(path, write_index=False, version=118)


def group_quantile(df: pd.DataFrame, by: Iterable[str], col: str, q: float) -> pd.Series:
    """Groupwise quantile helper equivalent to Stata's pctile."""
    return df.groupby(list(by))[col].transform(lambda x: x.quantile(q))


def lag_by_group(df: pd.DataFrame, group_col: str, time_col: str, cols: Iterable[str], periods: int = 1) -> pd.DataFrame:
    """Add within-group lags for the requested columns."""
    df = df.sort_values([group_col, time_col]).copy()
    for col in cols:
        df[f"L.{col}"] = df.groupby(group_col)[col].shift(periods)
    return df


def safe_log(series: pd.Series) -> pd.Series:
    """Natural log that returns NaN for nonpositive inputs."""
    return pd.Series(np.where(series > 0, np.log(series), np.nan), index=series.index)

