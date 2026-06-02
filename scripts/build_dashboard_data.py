#!/usr/bin/env python3
"""
Build firm-level parquet with markups under multiple assumptions.

Usage:
    python scripts/build_dashboard_data.py
"""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTERMEDIATE = PROJECT_ROOT / "Output" / "intermediate"
OUTPUT = PROJECT_ROOT / "data"


def load_panel() -> pd.DataFrame:
    path = INTERMEDIATE / "panel_data.csv"
    if not path.exists():
        raise FileNotFoundError(f"Panel data not found: {path}")
    df = pd.read_csv(path)
    logger.info(f"Loaded panel: {len(df)} firm-years")
    return df


def load_markups(filename: str) -> pd.DataFrame:
    path = INTERMEDIATE / filename
    if not path.exists():
        logger.warning(f"Not found: {path}")
        return pd.DataFrame()
    df = pd.read_csv(path)
    logger.info(f"  {filename}: {len(df)} firm-years")
    return df


def build_firm_parquet() -> pd.DataFrame:
    panel = load_panel()

    # Base firm-year table
    base_cols = [
        "gvkey", "year", "ind2d", "ind3d", "conm",
        "sale_D", "cogs_D", "xsga_D", "capital_D", "kexp",
    ]
    df = panel[[c for c in base_cols if c in panel.columns]].copy()

    # Factor shares
    logger.info("Computing factor shares...")
    df["costshare_basic"] = df["cogs_D"] / df["sale_D"]
    df["costshare_capital"] = df["cogs_D"] / (df["cogs_D"] + df["kexp"])

    # Markups: IV spec1, IV spec2, Cost Share, ACF.
    # Each value is a list of candidate filenames tried in order — handles both
    # the dual-spec output (markups_wooldridge_iv_spec1.csv) and legacy /
    # single-spec runs (markups_wooldridge_iv.csv).
    logger.info("Merging markups...")
    markup_sources = {
        "markup_iv_spec1": ["markups_wooldridge_iv_spec1.csv", "markups_iv_spec1.csv"],
        "markup_iv_spec2": ["markups_wooldridge_iv_spec2.csv", "markups_iv_spec2.csv", "markups_wooldridge_iv.csv"],
        "markup_cs": ["markups_cost_share.csv"],
        "markup_acf": ["markups_acf.csv"],
    }

    for col_name, candidates in markup_sources.items():
        markups = pd.DataFrame()
        for filename in candidates:
            markups = load_markups(filename)
            if not markups.empty:
                break
        if markups.empty:
            df[col_name] = float("nan")
            continue
        markups = markups[["gvkey", "year", "markup"]].rename(columns={"markup": col_name})
        markups = markups.drop_duplicates(subset=["gvkey", "year"], keep="last")
        df = df.merge(markups, on=["gvkey", "year"], how="left")

    # Filter outliers
    for col in ["markup_iv_spec1", "markup_iv_spec2", "markup_cs", "markup_acf"]:
        if col in df.columns:
            df.loc[df[col] <= 0, col] = float("nan")
            df.loc[df[col] > 50, col] = float("nan")

    # Clean up
    df = df.dropna(subset=["sale_D", "cogs_D"])
    df = df[(df["sale_D"] > 0) & (df["cogs_D"] > 0)]

    logger.info(f"Final parquet: {len(df)} firm-years, {len(df.columns)} columns")
    return df


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    df = build_firm_parquet()

    # Save with monthly timestamp (e.g., firm_markups_2026_04.parquet)
    month_tag = datetime.now().strftime("%Y_%m")
    parquet_path = OUTPUT / f"firm_markups_{month_tag}.parquet"
    df.to_parquet(parquet_path, index=False)
    size_mb = parquet_path.stat().st_size / 1024 / 1024
    logger.info(f"Saved to {parquet_path} ({size_mb:.1f} MB)")

    # Summary
    logger.info("=" * 60)
    logger.info(f"Years: {int(df['year'].min())}-{int(df['year'].max())}")
    logger.info(f"Firms: {df['gvkey'].nunique()}")
    for col in df.columns:
        n = df[col].notna().sum()
        logger.info(f"  {col}: {n} non-null ({n/len(df)*100:.0f}%)")


if __name__ == "__main__":
    main()
