"""Data downloaders for external sources (WRDS, FRED, BLS)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def download_compustat(output_dir: Path, wrds_username: str | None = None) -> None:
    """
    Download Compustat data from WRDS.

    Downloads both annual and quarterly financial data with NAICS codes.

    Parameters
    ----------
    output_dir : Path
        Output directory (typically Input/DLEU/)
    wrds_username : str, optional
        WRDS username. If None, uses default WRDS authentication.

    Raises
    ------
    ImportError
        If wrds package is not installed
    RuntimeError
        If WRDS connection fails

    Notes
    -----
    Requires WRDS credentials and database access.
    Creates:
    - Compustat_annual.dta
    - Compustat_quarterly.dta
    """
    try:
        import wrds
    except ImportError as e:
        raise ImportError(
            "wrds package required for Compustat download. "
            "Install with: pip install wrds"
        ) from e

    logger.info("Connecting to WRDS...")
    try:
        db = wrds.Connection(wrds_username=wrds_username) if wrds_username else wrds.Connection()
    except Exception as e:
        raise RuntimeError(f"Failed to connect to WRDS: {e}") from e

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Obtain NAICS code from comp.company
    logger.info("Downloading NAICS codes...")
    fields = ["gvkey", "naics"]
    query = "select " + ", ".join(fields) + " from comp.company"
    naics = db.raw_sql(query).sort_values(["gvkey"])

    # -------------------------------------------------------------------------------- #
    # Annual Data
    # -------------------------------------------------------------------------------- #
    logger.info("Downloading annual financial data...")
    fields = [
        "gvkey",
        "indfmt",
        "consol",
        "popsrc",
        "datafmt",
        "conm",
        "fyear",
        "sale",
        "cogs",
        "xsga",
        "ppegt",
        "xlr",
        "xrd",
        "xad",
        "dvt",
        "intan",
        "mkvalt",
        "tie",
        "emp",
        "ppent",
    ]
    query = (
        "select "
        + ", ".join(fields)
        + " from comp.funda where consol = 'C' and popsrc = 'D' and datafmt = 'STD'"
    )
    df_fund = db.raw_sql(query).sort_values(["gvkey", "fyear"])

    df = pd.merge(df_fund, naics, on=["gvkey"], how="left")

    annual_path = output_dir / "Compustat_annual.dta"
    df.to_stata(annual_path, write_index=False)
    logger.info(f"Saved annual data to {annual_path}")

    # -------------------------------------------------------------------------------- #
    # Quarterly Data
    # -------------------------------------------------------------------------------- #
    logger.info("Downloading quarterly financial data...")
    fields = [
        "gvkey",
        "indfmt",
        "consol",
        "popsrc",
        "datafmt",
        "conm",
        "fyearq",
        "fqtr",
        "saleq",
        "cogsq",
        "xsgaq",
        "ppegtq",
    ]
    query = (
        "select "
        + ", ".join(fields)
        + " from comp.fundq where consol = 'C' and popsrc = 'D' and datafmt = 'STD'"
    )
    df_fund = db.raw_sql(query).sort_values(["gvkey", "fyearq", "fqtr"])

    df = pd.merge(df_fund, naics, on=["gvkey"], how="left")

    quarterly_path = output_dir / "Compustat_quarterly.dta"
    df.to_stata(quarterly_path, write_index=False)
    logger.info(f"Saved quarterly data to {quarterly_path}")

    db.close()
    logger.info("Compustat download complete")


def download_cpi(output_dir: Path, fred_api_key: str) -> None:
    """
    Download Consumer Price Index data from FRED.

    Downloads monthly CPI data and creates annual (January) and quarterly files.

    Parameters
    ----------
    output_dir : Path
        Output directory (typically Input/CPI/)
    fred_api_key : str
        FRED API key

    Raises
    ------
    ImportError
        If fredapi package is not installed
    RuntimeError
        If FRED API call fails

    Notes
    -----
    Creates:
    - CPI_annual.csv (January data only)
    - CPI_quarterly.csv (Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct)
    """
    try:
        import numpy as np
        from fredapi import Fred
    except ImportError as e:
        raise ImportError(
            "fredapi package required for CPI download. "
            "Install with: pip install fredapi"
        ) from e

    logger.info("Connecting to FRED API...")
    try:
        fred = Fred(api_key=fred_api_key)
    except Exception as e:
        raise RuntimeError(f"Failed to connect to FRED: {e}") from e

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading CPI data (CPIAUCSL)...")
    cpi_dict = {"CPIAUCSL": "CPI"}

    def name_series(series, name):
        series.name = name
        return series

    data_list = [name_series(fred.get_series(k), v) for k, v in cpi_dict.items()]
    df = pd.concat(data_list, axis=1)
    df.reset_index(inplace=True)
    df = df.rename(columns={"index": "Date"})

    df["year"] = df["Date"].dt.year
    df["month"] = df["Date"].dt.month

    # Get Annual CPI (January data only)
    df_annual = df[df.month == 1]
    df_annual = df_annual[["year", "CPI"]]
    annual_path = output_dir / "CPI_annual.csv"
    df_annual.to_csv(annual_path, index=False)
    logger.info(f"Saved annual CPI to {annual_path}")

    # Get Quarterly CPI (Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct)
    df["year"] = df["year"].astype(int).astype(str)
    df["month"] = df["month"].astype(int)
    df["quarter"] = None
    df.loc[df.month == 1, "quarter"] = df["year"] + "Q1"
    df.loc[df.month == 4, "quarter"] = df["year"] + "Q2"
    df.loc[df.month == 7, "quarter"] = df["year"] + "Q3"
    df.loc[df.month == 10, "quarter"] = df["year"] + "Q4"
    df["CPI"] = pd.to_numeric(df["CPI"])
    df = df.dropna(subset=["quarter"])
    df = df[["quarter", "CPI"]]
    quarterly_path = output_dir / "CPI_quarterly.csv"
    df.to_csv(quarterly_path, index=False)
    logger.info(f"Saved quarterly CPI to {quarterly_path}")

    logger.info("CPI download complete")


def download_ppi(output_dir: Path, use_browser: bool = False) -> None:
    """
    Download and process Producer Price Index data from BLS.

    Downloads pc.data.0.Current.txt from BLS and processes into annual/quarterly files.
    Merges with existing old PPI data if available.

    Parameters
    ----------
    output_dir : Path
        Output directory (typically Input/PPI/)
    use_browser : bool, default False
        If True, use Playwright browser automation to download.
        If False, assumes pc.data.0.Current.txt already exists.

    Raises
    ------
    ImportError
        If playwright package is not installed (when use_browser=True)
    RuntimeError
        If download or processing fails

    Notes
    -----
    Processing rules:
    - Quarterly data: use quarter-end months (M03, M06, M09, M12)
    - Annual data: use December (M12) only
    - Filters for valid NAICS codes (2-6 digits)
    - Merges with PPI_quarterly_old.csv and PPI_annual_old.csv if they exist

    Creates:
    - PPI_quarterly.csv
    - PPI_annual.csv
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = output_dir / "pc.data.0.Current.txt"

    # Download if requested
    if use_browser:
        logger.info("Downloading PPI data from BLS using browser automation...")
        _download_ppi_source(
            "https://download.bls.gov/pub/time.series/pc/",
            "pc.data.0.Current",
            input_path,
        )
    else:
        if not input_path.exists():
            raise FileNotFoundError(
                f"PPI source file not found: {input_path}. "
                "Set use_browser=True to download automatically."
            )
        logger.info(f"Using existing PPI file: {input_path}")

    # Process the data
    logger.info("Processing PPI data...")
    _process_ppi_data(input_path, output_dir)
    logger.info("PPI download and processing complete")


def _download_ppi_source(index_url: str, link_text: str, dest_path: Path) -> None:
    """Download PPI source file using Playwright browser automation."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise ImportError(
            "playwright package required for PPI download. "
            "Install with: pip install playwright && playwright install chromium"
        ) from e

    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()
            with page.expect_download() as dl_info:
                page.goto(index_url, wait_until="networkidle")
                page.get_by_text(link_text, exact=True).click()
            download = dl_info.value
            download.save_as(str(dest_path))
            browser.close()
        logger.info(f"Downloaded PPI source to {dest_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to download PPI data from {index_url}") from e


def _process_ppi_data(input_path: Path, output_dir: Path) -> None:
    """Process raw PPI data into annual and quarterly files."""
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    # Read raw data
    df = pd.read_csv(input_path, sep=r"\s+", dtype=str, engine="python")

    df = df[["series_id", "year", "period", "value"]]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["year"] = df["year"].astype(int)

    # Extract NAICS code from series_id
    df["naics_code"] = (
        df["series_id"].str.slice(start=3, stop=9).str.replace("-", "", regex=False)
    )
    # Filter for valid NAICS (2-6 digits)
    df = df[df["naics_code"].str.match(r"^\d{2,6}$")]

    # Filter for quarter-end months only
    valid_months = ["M03", "M06", "M09", "M12"]
    df = df[df["period"].isin(valid_months)]

    # Map months to quarters
    month_to_q = {"M03": 1, "M06": 2, "M09": 3, "M12": 4}
    df["quarter"] = df["period"].map(month_to_q)
    df["date"] = df["year"].astype(str) + "Q" + df["quarter"].astype(str)

    # Create quarterly dataset
    df_q = (
        df[["year", "quarter", "value", "naics_code", "date"]]
        .rename(columns={"value": "PPI"})
        .sort_values(["naics_code", "year", "quarter"])
        .reset_index(drop=True)
    )

    # Create annual dataset (December only)
    df_a = (
        df[df["period"] == "M12"][["year", "naics_code", "value"]]
        .rename(columns={"value": "PPI"})
        .sort_values(["naics_code", "year"])
        .reset_index(drop=True)
    )

    # Merge with old data if exists
    path_q_old = output_dir / "PPI_quarterly_old.csv"
    path_a_old = output_dir / "PPI_annual_old.csv"
    path_q_new = output_dir / "PPI_quarterly.csv"
    path_a_new = output_dir / "PPI_annual.csv"

    if path_q_old.exists():
        logger.info(f"Merging with old quarterly data: {path_q_old}")
        old_q = pd.read_csv(path_q_old)
        old_q = _drop_index_col(old_q)
        df_q = pd.concat([old_q, df_q], ignore_index=True)
        df_q = (
            df_q.sort_values(["naics_code", "year", "quarter"])
            .drop_duplicates(["naics_code", "year", "quarter"], keep="last")
            .reset_index(drop=True)
        )

    if path_a_old.exists():
        logger.info(f"Merging with old annual data: {path_a_old}")
        old_a = pd.read_csv(path_a_old)
        old_a = _drop_index_col(old_a)
        df_a = pd.concat([old_a, df_a], ignore_index=True)
        df_a = (
            df_a.sort_values(["naics_code", "year"])
            .drop_duplicates(["naics_code", "year"], keep="last")
            .reset_index(drop=True)
        )

    # Save processed data
    df_q.to_csv(path_q_new, index=False)
    df_a.to_csv(path_a_new, index=False)

    logger.info(f"Quarterly data saved to: {path_q_new}")
    logger.info(f"Annual data saved to: {path_a_new}")
    logger.info(f"Coverage: {df_a['year'].min()} - {df_a['year'].max()}")
    logger.info(f"Industries processed: {df_a['naics_code'].nunique()}")


def _drop_index_col(df: pd.DataFrame) -> pd.DataFrame:
    """Remove unnamed index columns from DataFrame."""
    if df.columns[0].lower().startswith("unnamed"):
        df = df.iloc[:, 1:]
    return df
