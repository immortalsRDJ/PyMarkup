"""Data loaders for Compustat, macro variables, deflators."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def load_compustat(path: Path) -> pd.DataFrame:
    """
    Load Compustat annual data from Stata file.

    Parameters
    ----------
    path : Path
        Path to Compustat_annual.dta

    Returns
    -------
    pd.DataFrame
        Raw Compustat data
    """
    logger.info(f"Loading Compustat from {path}")
    if not path.exists():
        raise FileNotFoundError(f"Compustat file not found: {path}")
    return pd.read_stata(path)


def load_macro_vars(path: Path) -> pd.DataFrame:
    """
    Load macro variables (GDP, user cost of capital).

    Parameters
    ----------
    path : Path
        Path to macro_vars_new.xlsx

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: year, USGDP, usercost
    """
    logger.info(f"Loading macro variables from {path}")
    if not path.exists():
        raise FileNotFoundError(f"Macro variable file not found: {path}")

    macro = pd.read_excel(path)
    macro.columns = macro.columns.str.strip()

    required_cols = {"year", "USGDP", "usercost"}
    if not required_cols.issubset(macro.columns):
        raise ValueError(f"macro_vars_new.xlsx must contain columns: {required_cols}")

    return macro[["year", "USGDP", "usercost"]]


def load_ppi(path: Path, frequency: str = "annual") -> pd.DataFrame:
    """
    Load Producer Price Index (PPI) data.

    Parameters
    ----------
    path : Path
        Path to PPI directory or specific PPI file
    frequency : str, default "annual"
        Either "annual" or "quarterly"

    Returns
    -------
    pd.DataFrame
        PPI data with columns: year, naics_code, PPI (annual)
        or year, quarter, naics_code, PPI, date (quarterly)

    Raises
    ------
    FileNotFoundError
        If PPI file not found
    ValueError
        If frequency is not "annual" or "quarterly"
    """
    if frequency not in ["annual", "quarterly"]:
        raise ValueError(f"frequency must be 'annual' or 'quarterly', got: {frequency}")

    path = Path(path)

    # If path is a directory, construct the filename
    if path.is_dir():
        file_path = path / f"PPI_{frequency}.csv"
    else:
        file_path = path

    logger.info(f"Loading PPI ({frequency}) from {file_path}")

    if not file_path.exists():
        raise FileNotFoundError(f"PPI file not found: {file_path}")

    df = pd.read_csv(file_path)

    # Drop any unnamed index columns
    if df.columns[0].lower().startswith("unnamed"):
        df = df.iloc[:, 1:]

    return df


def load_cpi(path: Path, frequency: str = "annual") -> pd.DataFrame:
    """
    Load Consumer Price Index (CPI) data.

    Parameters
    ----------
    path : Path
        Path to CPI directory or specific CPI file
    frequency : str, default "annual"
        Either "annual" or "quarterly"

    Returns
    -------
    pd.DataFrame
        CPI data with columns: year, CPI (annual)
        or quarter, CPI (quarterly)

    Raises
    ------
    FileNotFoundError
        If CPI file not found
    ValueError
        If frequency is not "annual" or "quarterly"
    """
    if frequency not in ["annual", "quarterly"]:
        raise ValueError(f"frequency must be 'annual' or 'quarterly', got: {frequency}")

    path = Path(path)

    # If path is a directory, construct the filename
    if path.is_dir():
        file_path = path / f"CPI_{frequency}.csv"
    else:
        file_path = path

    logger.info(f"Loading CPI ({frequency}) from {file_path}")

    if not file_path.exists():
        raise FileNotFoundError(f"CPI file not found: {file_path}")

    return pd.read_csv(file_path)
