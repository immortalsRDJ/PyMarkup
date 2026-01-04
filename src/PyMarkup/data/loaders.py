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


def load_ppi(path: Path) -> pd.DataFrame:
    """
    Load Producer Price Index (PPI) data.

    Parameters
    ----------
    path : Path
        Path to PPI data file

    Returns
    -------
    pd.DataFrame
        PPI data
    """
    logger.info(f"Loading PPI from {path}")
    # TODO: Implement PPI loading logic
    raise NotImplementedError("PPI loading not yet implemented")


def load_cpi(path: Path) -> pd.DataFrame:
    """
    Load Consumer Price Index (CPI) data.

    Parameters
    ----------
    path : Path
        Path to CPI data file

    Returns
    -------
    pd.DataFrame
        CPI data
    """
    logger.info(f"Loading CPI from {path}")
    # TODO: Implement CPI loading logic
    raise NotImplementedError("CPI loading not yet implemented")
