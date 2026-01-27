"""Data downloaders for Compustat, CPI, and PPI."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .config import DataConfig, load_config

logger = logging.getLogger(__name__)


# =============================================================================
# Compustat (WRDS)
# =============================================================================


def download_compustat(
    config: DataConfig | None = None,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """
    Download Compustat annual and quarterly data from WRDS.

    Parameters
    ----------
    config : DataConfig, optional
        Configuration with WRDS credentials
    output_dir : Path, optional
        Output directory (default: config.data_dir / "DLEU")

    Returns
    -------
    tuple[Path, Path]
        Paths to annual and quarterly Stata files
    """
    try:
        import wrds
    except ImportError:
        raise ImportError("wrds package required. Install with: uv add wrds")

    config = config or load_config()
    output_dir = output_dir or config.data_dir / "DLEU"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Connecting to WRDS...")
    db = wrds.Connection()

    # Get NAICS codes
    logger.info("Fetching NAICS codes...")
    naics_query = "SELECT gvkey, naics FROM comp.company"
    naics = db.raw_sql(naics_query).sort_values(["gvkey"])

    # Annual data
    logger.info("Downloading annual Compustat data...")
    annual_fields = [
        "gvkey", "indfmt", "consol", "popsrc", "datafmt", "conm", "fyear",
        "sale", "cogs", "xsga", "ppegt", "xlr", "xrd", "xad", "dvt",
        "intan", "mkvalt", "tie", "emp", "ppent",
    ]
    annual_query = f"""
        SELECT {', '.join(annual_fields)}
        FROM comp.funda
        WHERE consol = 'C' AND popsrc = 'D' AND datafmt = 'STD'
    """
    df_annual = db.raw_sql(annual_query).sort_values(["gvkey", "fyear"])
    df_annual = pd.merge(df_annual, naics, on=["gvkey"], how="left")

    annual_path = output_dir / "Compustat_annual.dta"
    df_annual.to_stata(annual_path, write_index=False)
    logger.info(f"Saved annual data to {annual_path}")

    # Quarterly data
    logger.info("Downloading quarterly Compustat data...")
    quarterly_fields = [
        "gvkey", "indfmt", "consol", "popsrc", "datafmt", "conm",
        "fyearq", "fqtr", "saleq", "cogsq", "xsgaq", "ppegtq",
    ]
    quarterly_query = f"""
        SELECT {', '.join(quarterly_fields)}
        FROM comp.fundq
        WHERE consol = 'C' AND popsrc = 'D' AND datafmt = 'STD'
    """
    df_quarterly = db.raw_sql(quarterly_query).sort_values(["gvkey", "fyearq", "fqtr"])
    df_quarterly = pd.merge(df_quarterly, naics, on=["gvkey"], how="left")

    quarterly_path = output_dir / "Compustat_quarterly.dta"
    df_quarterly.to_stata(quarterly_path, write_index=False)
    logger.info(f"Saved quarterly data to {quarterly_path}")

    db.close()
    return annual_path, quarterly_path


# =============================================================================
# CPI (FRED)
# =============================================================================


def download_cpi(
    config: DataConfig | None = None,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """
    Download CPI data from FRED.

    Parameters
    ----------
    config : DataConfig, optional
        Configuration with FRED API key
    output_dir : Path, optional
        Output directory (default: config.data_dir / "CPI")

    Returns
    -------
    tuple[Path, Path]
        Paths to annual and quarterly CSV files
    """
    try:
        from fredapi import Fred
    except ImportError:
        raise ImportError("fredapi package required. Install with: uv add fredapi")

    config = config or load_config()
    config.validate(require_fred=True)

    output_dir = output_dir or config.data_dir / "CPI"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Connecting to FRED...")
    fred = Fred(api_key=config.fred_api_key)

    logger.info("Downloading CPI data (CPIAUCSL)...")
    cpi_series = fred.get_series("CPIAUCSL")
    cpi_series.name = "CPI"

    df = pd.DataFrame(cpi_series).reset_index()
    df = df.rename(columns={"index": "Date"})
    df["year"] = df["Date"].dt.year
    df["month"] = df["Date"].dt.month

    # Annual CPI (January values)
    df_annual = df[df.month == 1][["year", "CPI"]].copy()
    annual_path = output_dir / "CPI_annual.csv"
    df_annual.to_csv(annual_path, index=False)
    logger.info(f"Saved annual CPI to {annual_path}")

    # Quarterly CPI (months 1, 4, 7, 10)
    df["year_str"] = df["year"].astype(str)
    df["quarter"] = np.nan
    df.loc[df.month == 1, "quarter"] = df["year_str"] + "Q1"
    df.loc[df.month == 4, "quarter"] = df["year_str"] + "Q2"
    df.loc[df.month == 7, "quarter"] = df["year_str"] + "Q3"
    df.loc[df.month == 10, "quarter"] = df["year_str"] + "Q4"

    df_quarterly = df.dropna(subset=["quarter"])[["quarter", "CPI"]].copy()
    quarterly_path = output_dir / "CPI_quarterly.csv"
    df_quarterly.to_csv(quarterly_path, index=False)
    logger.info(f"Saved quarterly CPI to {quarterly_path}")

    return annual_path, quarterly_path


# =============================================================================
# PPI (BLS)
# =============================================================================


def download_ppi(
    config: DataConfig | None = None,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """
    Download and process PPI data from BLS.

    Parameters
    ----------
    config : DataConfig, optional
        Configuration with PPI URL
    output_dir : Path, optional
        Output directory (default: config.data_dir / "PPI")

    Returns
    -------
    tuple[Path, Path]
        Paths to annual and quarterly CSV files
    """
    config = config or load_config()
    output_dir = output_dir or config.data_dir / "PPI"
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_path = output_dir / "pc.data.0.Current.txt"

    # Download raw data
    logger.info(f"Downloading PPI data from {config.ppi_url}...")
    response = requests.get(
        config.ppi_url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        timeout=120,
        stream=True,
    )
    response.raise_for_status()

    with open(raw_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    logger.info(f"Downloaded raw PPI data to {raw_path}")

    # Process data
    logger.info("Processing PPI data...")
    df = pd.read_csv(raw_path, sep=r"\s+", dtype=str, engine="python")
    df = df[["series_id", "year", "period", "value"]]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["year"] = df["year"].astype(int)

    # Extract NAICS code from series_id
    df["naics_code"] = df["series_id"].str.slice(start=3, stop=9).str.replace("-", "", regex=False)
    df = df[df["naics_code"].str.match(r"^\d{2,6}$")]

    # Filter to quarter-end months
    valid_months = ["M03", "M06", "M09", "M12"]
    df = df[df["period"].isin(valid_months)]

    month_to_q = {"M03": 1, "M06": 2, "M09": 3, "M12": 4}
    df["quarter"] = df["period"].map(month_to_q)
    df["date"] = df["year"].astype(str) + "Q" + df["quarter"].astype(str)

    # Quarterly data
    df_quarterly = (
        df[["year", "quarter", "value", "naics_code", "date"]]
        .rename(columns={"value": "PPI"})
        .sort_values(["naics_code", "year", "quarter"])
        .reset_index(drop=True)
    )

    # Merge with old data if exists
    old_quarterly_path = output_dir / "PPI_quarterly_old.csv"
    if old_quarterly_path.exists():
        old_q = pd.read_csv(old_quarterly_path)
        if old_q.columns[0].lower().startswith("unnamed"):
            old_q = old_q.iloc[:, 1:]
        df_quarterly = pd.concat([old_q, df_quarterly], ignore_index=True)
        df_quarterly = (
            df_quarterly.sort_values(["naics_code", "year", "quarter"])
            .drop_duplicates(["naics_code", "year", "quarter"], keep="last")
            .reset_index(drop=True)
        )

    quarterly_path = output_dir / "PPI_quarterly.csv"
    df_quarterly.to_csv(quarterly_path, index=False)
    logger.info(f"Saved quarterly PPI to {quarterly_path}")

    # Annual data (December only)
    df_annual = (
        df[df["period"] == "M12"][["year", "naics_code", "value"]]
        .rename(columns={"value": "PPI"})
        .sort_values(["naics_code", "year"])
        .reset_index(drop=True)
    )

    # Merge with old data if exists
    old_annual_path = output_dir / "PPI_annual_old.csv"
    if old_annual_path.exists():
        old_a = pd.read_csv(old_annual_path)
        if old_a.columns[0].lower().startswith("unnamed"):
            old_a = old_a.iloc[:, 1:]
        df_annual = pd.concat([old_a, df_annual], ignore_index=True)
        df_annual = (
            df_annual.sort_values(["naics_code", "year"])
            .drop_duplicates(["naics_code", "year"], keep="last")
            .reset_index(drop=True)
        )

    annual_path = output_dir / "PPI_annual.csv"
    df_annual.to_csv(annual_path, index=False)
    logger.info(f"Saved annual PPI to {annual_path}")

    logger.info(f"PPI coverage: {df_annual['year'].min()} - {df_annual['year'].max()}")
    logger.info(f"Industries processed: {df_annual['naics_code'].nunique()}")

    return annual_path, quarterly_path


# =============================================================================
# Download All
# =============================================================================


def download_all(
    config: DataConfig | None = None,
    skip_compustat: bool = False,
    skip_cpi: bool = False,
    skip_ppi: bool = False,
) -> dict[str, tuple[Path, Path]]:
    """
    Download all data sources.

    Parameters
    ----------
    config : DataConfig, optional
        Configuration
    skip_compustat : bool
        Skip Compustat download (requires WRDS credentials)
    skip_cpi : bool
        Skip CPI download (requires FRED API key)
    skip_ppi : bool
        Skip PPI download

    Returns
    -------
    dict
        Dictionary mapping source name to (annual_path, quarterly_path)
    """
    config = config or load_config()
    results = {}

    if not skip_ppi:
        logger.info("=" * 60)
        logger.info("Downloading PPI data...")
        results["ppi"] = download_ppi(config)

    if not skip_cpi:
        logger.info("=" * 60)
        logger.info("Downloading CPI data...")
        results["cpi"] = download_cpi(config)

    if not skip_compustat:
        logger.info("=" * 60)
        logger.info("Downloading Compustat data...")
        results["compustat"] = download_compustat(config)

    logger.info("=" * 60)
    logger.info("All downloads complete!")
    return results
