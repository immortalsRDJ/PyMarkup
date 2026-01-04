"""Data preparation and cleaning for Compustat panel.

This module contains functions for:
- Loading and cleaning Compustat data
- Deflating by macro variables
- Industry code processing
- Percentile trimming
- Creating lagged variables
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def prep_industry_codes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create 2-digit, 3-digit, and 4-digit industry codes from NAICS.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'naics' column

    Returns
    -------
    pd.DataFrame
        DataFrame with added ind2d, ind3d, ind4d columns
    """
    for digits in (2, 3, 4):
        col = f"ind{digits}d"
        df[col] = pd.to_numeric(df["naics"].str.slice(0, digits), errors="coerce")
    return df


def trim_sale_cogs_ratio(df: pd.DataFrame, lower: float = 0.01, upper: float = 0.99) -> pd.DataFrame:
    """
    Trim observations based on sales/COGS ratio percentiles.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'sale' and 'cogs' columns
    lower : float
        Lower percentile (default: 0.01)
    upper : float
        Upper percentile (default: 0.99)

    Returns
    -------
    pd.DataFrame
        Trimmed DataFrame
    """
    df = df.copy()
    df["s_g"] = df["sale"] / df["cogs"]
    p_lower = df.groupby("year")["s_g"].transform(lambda x: x.quantile(lower))
    p_upper = df.groupby("year")["s_g"].transform(lambda x: x.quantile(upper))
    trimmed = df[(df["s_g"] > p_lower) & (df["s_g"] < p_upper)]
    return trimmed.drop(columns=["s_g"])


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
    macro = pd.read_excel(path)
    macro.columns = macro.columns.str.strip()
    required_cols = {"year", "USGDP", "usercost"}
    if not required_cols.issubset(macro.columns):
        raise ValueError(f"macro_vars_new.xlsx must contain columns: {required_cols}")
    return macro[["year", "USGDP", "usercost"]]


def add_lags(df: pd.DataFrame, group: str, time: str, cols: Iterable[str]) -> pd.DataFrame:
    """
    Add lagged variables by group and time.

    Parameters
    ----------
    df : pd.DataFrame
        Input data
    group : str
        Column name for grouping (e.g., 'gvkey', 'id')
    time : str
        Column name for time dimension (e.g., 'year')
    cols : Iterable[str]
        Columns to lag

    Returns
    -------
    pd.DataFrame
        DataFrame with added L.{col} columns
    """
    df = df.copy()
    df = df.sort_values([group, time])
    for col in cols:
        df[f"L.{col}"] = df.groupby(group)[col].shift(1)
    return df


def safe_log(series: pd.Series) -> pd.Series:
    """
    Natural log that returns NaN for non-positive values.

    Parameters
    ----------
    series : pd.Series
        Input series

    Returns
    -------
    pd.Series
        Log-transformed series
    """
    return np.where(series > 0, np.log(series), np.nan)


def create_compustat_panel(
    compustat_path: Path,
    macro_path: Path,
    include_interest_cogs: bool = False,
    trim_percentiles: tuple[float, float] = (0.01, 0.99),
) -> pd.DataFrame:
    """
    Create cleaned and trimmed Compustat panel for markup estimation.

    This function:
    1. Loads Compustat data
    2. Removes duplicates and processes industry codes
    3. Merges with macro variables
    4. Deflates by GDP
    5. Trims outliers
    6. Creates market share variables

    Parameters
    ----------
    compustat_path : Path
        Path to Compustat_annual.dta
    macro_path : Path
        Path to macro_vars_new.xlsx
    include_interest_cogs : bool
        Whether to include interest expense in COGS
    trim_percentiles : tuple[float, float]
        Lower and upper percentiles for trimming

    Returns
    -------
    pd.DataFrame
        Cleaned panel with deflated variables
    """
    logger.info(f"Loading Compustat from {compustat_path}")
    df = pd.read_stata(compustat_path)
    df = df[df["fyear"] > 1954].copy()
    df = df.rename(columns={"fyear": "year"})
    df = df.sort_values(["gvkey", "year"])

    # Remove duplicates
    df["nrobs"] = df.groupby(["gvkey", "year"])["year"].transform("size")
    df = df[~(((df["nrobs"] == 2) | (df["nrobs"] == 3)) & (df["indfmt"] == "FS"))]
    df = df.drop_duplicates(subset=["gvkey", "year"])
    df = df[df["naics"].notna() & (df["naics"] != "")]

    # Industry codes
    df = prep_industry_codes(df)
    df["nrind2"] = df["ind2d"].astype("category").cat.codes + 1
    df["nrind3"] = df["ind3d"].astype("category").cat.codes + 1
    df["nrind4"] = df["ind4d"].astype("category").cat.codes + 1

    # Fill missing interest expense
    df["tie"] = df["tie"].fillna(0)

    # Select columns
    keep_cols = [
        "gvkey",
        "year",
        "naics",
        "ind2d",
        "ind3d",
        "ind4d",
        "sale",
        "cogs",
        "xsga",
        "xlr",
        "xrd",
        "xad",
        "dvt",
        "ppegt",
        "intan",
        "emp",
        "mkvalt",
        "conm",
        "tie",
    ]
    df = df[keep_cols]

    # Convert to thousands
    df["sale"] *= 1000
    df["xlr"] *= 1000
    if include_interest_cogs:
        df["cogs"] = (df["cogs"] + df["tie"]) * 1000
    else:
        df["cogs"] *= 1000
    df["xsga"] *= 1000
    df["mkvalt"] *= 1000
    df["dvt"] *= 1000
    df["ppegt"] *= 1000
    df["intan"] *= 1000

    # Merge macro variables
    macro = load_macro_vars(macro_path)
    df = df.merge(macro, on="year", how="inner", validate="m:1")

    # Deflate by GDP
    df["sale_D"] = (df["sale"] / df["USGDP"]) * 100
    df["cogs_D"] = (df["cogs"] / df["USGDP"]) * 100
    df["xsga_D"] = (df["xsga"] / df["USGDP"]) * 100
    df["mkvalt_D"] = (df["mkvalt"] / df["USGDP"]) * 100
    df["dividend_D"] = (df["dvt"] / df["USGDP"]) * 100
    df["capital_D"] = (df["ppegt"] / df["USGDP"]) * 100
    df["intan_D"] = (df["intan"] / df["USGDP"]) * 100
    df["xlr_D"] = (df["xlr"] / df["USGDP"]) * 100
    df["kexp"] = df["usercost"] * df["capital_D"]

    # Market shares for OP/ACF
    df["totsales2d"] = df.groupby(["ind2d", "year"])["sale_D"].transform("sum")
    df["totsales3d"] = df.groupby(["ind3d", "year"])["sale_D"].transform("sum")
    df["totsales4d"] = df.groupby(["ind4d", "year"])["sale_D"].transform("sum")
    df["ms2d"] = df["sale_D"] / df["totsales2d"]
    df["ms3d"] = df["sale_D"] / df["totsales3d"]
    df["ms4d"] = df["sale_D"] / df["totsales4d"]

    # Filter
    df = df[df["sale_D"] >= 0]
    df = df[df["cogs_D"] >= 0]
    df = df[df["sale_D"] != 0]
    df = df[df["cogs_D"] != 0]
    df = df[df["sale_D"].notna() & df["cogs_D"].notna()]
    df = df[df["year"] > 1949]

    # Trim
    df = trim_sale_cogs_ratio(df, lower=trim_percentiles[0], upper=trim_percentiles[1])

    # SG&A handling
    df["xsga"] = df["xsga"].replace({0: np.nan})
    df = df[df["xsga"].isna() | (df["xsga"] >= 0)]

    logger.info(f"Created panel with {len(df)} observations")
    return df
