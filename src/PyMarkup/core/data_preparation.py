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
    deu_observations_path: Path | None = None,
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
    7. Optionally filters to DEU sample (original DLEU paper observations)

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
    deu_observations_path : Path, optional
        Path to DEU_observations.dta file. If provided, filters panel to only
        include firm-years present in the original DLEU sample.

    Returns
    -------
    pd.DataFrame
        Cleaned panel with deflated variables
    """
    logger.info(f"Loading Compustat from {compustat_path}")
    compustat_path = Path(compustat_path)
    if compustat_path.suffix.lower() == ".csv":
        df = pd.read_csv(compustat_path, dtype={"naics": str, "gvkey": str})
    elif compustat_path.suffix.lower() == ".dta":
        df = pd.read_stata(compustat_path)
    else:
        raise ValueError(f"Unsupported file format: {compustat_path.suffix}. Use .csv or .dta")

    # Ensure naics is string type
    df["naics"] = df["naics"].astype(str).str.strip()

    df = df[df["fyear"] > 1954].copy()
    df = df.rename(columns={"fyear": "year"})
    df = df.sort_values(["gvkey", "year"])

    # Remove duplicates
    df["nrobs"] = df.groupby(["gvkey", "year"])["year"].transform("size")
    df = df[~(((df["nrobs"] == 2) | (df["nrobs"] == 3)) & (df["indfmt"] == "FS"))]
    df = df.drop_duplicates(subset=["gvkey", "year"])
    df = df[df["naics"].notna() & (df["naics"] != "") & (df["naics"] != "nan")]

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
        "nrind2",
        "nrind3",
        "nrind4",
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

    # Note: Trimming on sale/cogs ratio is NOT done here to match Stata code.
    # The Stata code (Estimate_Coefficients.do) only trims on xsga/sale ratio
    # (when dropmissingsga=0) or costshare variables (when dropmissingsga=1).
    # This trimming is done in the estimator's _preprocess() method instead.

    # SG&A handling
    df["xsga"] = df["xsga"].replace({0: np.nan})
    df = df[df["xsga"].isna() | (df["xsga"] >= 0)]

    # DEU sample filtering (optional)
    # This matches Stata: joinby gvkey year using "rawData/deu_observations.dta"
    if deu_observations_path is not None:
        deu_observations_path = Path(deu_observations_path)
        if deu_observations_path.exists():
            logger.info(f"Filtering to DEU sample from {deu_observations_path}")
            deu = pd.read_stata(deu_observations_path)

            # Convert datetime year to integer if needed
            if deu["year"].dtype == "datetime64[ns]":
                deu["year"] = deu["year"].dt.year

            # Ensure consistent types for merge
            deu["gvkey"] = deu["gvkey"].astype(str).str.strip()
            deu["year"] = deu["year"].astype(float)
            df["gvkey"] = df["gvkey"].astype(str).str.strip()

            n_before = len(df)
            df = df.merge(deu[["gvkey", "year"]], on=["gvkey", "year"], how="inner")
            n_after = len(df)
            logger.info(f"DEU sample filtering: {n_before} -> {n_after} observations")
        else:
            logger.warning(f"DEU observations file not found: {deu_observations_path}")

    logger.info(f"Created panel with {len(df)} observations")
    return df


def create_compustat_panel_quarterly(
    compustat_path: Path,
    macro_path: Path,
    trim_percentiles: tuple[float, float] = (0.01, 0.99),
) -> pd.DataFrame:
    """
    Create quarterly Compustat panel data for markup estimation.

    Mirrors the annual pipeline but uses quarterly columns (saleq, cogsq, etc.).
    Macro variables (USGDP, usercost) are merged at annual frequency — the same
    deflator applies to all four quarters of a fiscal year.

    Parameters
    ----------
    compustat_path : Path
        Path to Compustat_quarterly.csv
    macro_path : Path
        Path to macro_vars_new.xlsx
    trim_percentiles : tuple
        Lower and upper percentiles for trimming (default: 1st/99th)

    Returns
    -------
    pd.DataFrame
        Quarterly panel with deflated variables and quarter identifier
    """
    logger.info("Loading quarterly Compustat data...")
    df = pd.read_csv(compustat_path)
    df.columns = df.columns.str.lower()
    logger.info(f"Loaded {len(df)} quarterly observations")

    # Filter valid quarters
    df = df.dropna(subset=["fyearq", "fqtr"])
    df["fyearq"] = df["fyearq"].astype(int)
    df["fqtr"] = df["fqtr"].astype(int)
    df["year"] = df["fyearq"]
    df["quarter"] = df["fyearq"].astype(str) + "Q" + df["fqtr"].astype(str)

    # Sort and deduplicate
    df["gvkey"] = df["gvkey"].astype(str).str.strip()
    df = df.sort_values(["gvkey", "quarter"])
    df = df.drop_duplicates(subset=["gvkey", "quarter"], keep="last")

    # Industry codes
    df["naics"] = df["naics"].astype(str).str.strip()
    df = df[df["naics"].notna() & (df["naics"] != "") & (df["naics"] != "nan")]
    df = prep_industry_codes(df)

    # Scale to thousands (Compustat reports in millions)
    for col in ["saleq", "cogsq", "xsgaq", "ppegtq"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce") * 1000

    # Merge macro variables (annual → all quarters of that year)
    macro = load_macro_vars(macro_path)
    df = df.merge(macro, on="year", how="inner", validate="m:1")
    logger.info(f"After macro merge: {len(df)} observations")

    # Deflate by GDP
    df["sale_D"] = (df["saleq"] / df["USGDP"]) * 100
    df["cogs_D"] = (df["cogsq"] / df["USGDP"]) * 100
    df["xsga_D"] = (df.get("xsgaq", pd.Series(dtype=float)) / df["USGDP"]) * 100
    df["capital_D"] = (df["ppegtq"] / df["USGDP"]) * 100
    df["kexp"] = df["usercost"] * df["capital_D"]

    # Filter valid observations
    df = df[(df["sale_D"] > 0) & (df["cogs_D"] > 0)]
    df = df.dropna(subset=["sale_D", "cogs_D"])

    # Trim sales/COGS ratio by quarter
    lower, upper = trim_percentiles
    df["_s_g"] = df["sale_D"] / df["cogs_D"]
    p_lo = df.groupby("quarter")["_s_g"].transform(lambda x: x.quantile(lower))
    p_hi = df.groupby("quarter")["_s_g"].transform(lambda x: x.quantile(upper))
    df = df[(df["_s_g"] > p_lo) & (df["_s_g"] < p_hi)].drop(columns=["_s_g"])

    logger.info(f"Created quarterly panel with {len(df)} observations")
    return df
