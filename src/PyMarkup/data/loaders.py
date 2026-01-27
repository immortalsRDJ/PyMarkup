"""Data loaders for Compustat, macro variables, deflators."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def load_compustat(path: Path, frequency: str = "annual") -> pd.DataFrame:
    """
    Load Compustat data from Stata file.

    Parameters
    ----------
    path : Path
        Path to Compustat .dta file
    frequency : str
        "annual" or "quarterly"

    Returns
    -------
    pd.DataFrame
        Raw Compustat data
    """
    logger.info(f"Loading Compustat ({frequency}) from {path}")
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
        Path to PPI CSV file (PPI_annual.csv or PPI_quarterly.csv)
    frequency : str
        "annual" or "quarterly"

    Returns
    -------
    pd.DataFrame
        PPI data with columns: naics_code, year, PPI (and quarter for quarterly)
    """
    logger.info(f"Loading PPI ({frequency}) from {path}")
    if not path.exists():
        raise FileNotFoundError(f"PPI file not found: {path}")

    df = pd.read_csv(path)

    # Validate columns
    if frequency == "annual":
        required = {"naics_code", "year", "PPI"}
    else:
        required = {"naics_code", "year", "quarter", "PPI"}

    if not required.issubset(df.columns):
        raise ValueError(f"PPI file must contain columns: {required}")

    return df


def load_cpi(path: Path, frequency: str = "annual") -> pd.DataFrame:
    """
    Load Consumer Price Index (CPI) data.

    Parameters
    ----------
    path : Path
        Path to CPI CSV file (CPI_annual.csv or CPI_quarterly.csv)
    frequency : str
        "annual" or "quarterly"

    Returns
    -------
    pd.DataFrame
        CPI data with columns: year/quarter, CPI
    """
    logger.info(f"Loading CPI ({frequency}) from {path}")
    if not path.exists():
        raise FileNotFoundError(f"CPI file not found: {path}")

    df = pd.read_csv(path)

    # Validate columns
    if frequency == "annual":
        required = {"year", "CPI"}
    else:
        required = {"quarter", "CPI"}

    if not required.issubset(df.columns):
        raise ValueError(f"CPI file must contain columns: {required}")

    return df


def load_naics_descriptions(path: Path) -> pd.DataFrame:
    """
    Load NAICS industry code descriptions.

    Parameters
    ----------
    path : Path
        Path to NAICS_2D_Description.xlsx

    Returns
    -------
    pd.DataFrame
        DataFrame with industry codes and descriptions
    """
    logger.info(f"Loading NAICS descriptions from {path}")
    if not path.exists():
        raise FileNotFoundError(f"NAICS description file not found: {path}")

    return pd.read_excel(path)
