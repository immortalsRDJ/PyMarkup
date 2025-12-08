"""
Python translation of ``Create_Data.do``.

This script builds the main trimmed Compustat panel and deflated variables, with
an option to include interest expense in COGS. Outputs are written to
``intermediateOutput/`` following the original filenames and the census
inference file is saved alongside.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .utils import (
    INTERMEDIATE_DIR,
    RAW_DATA_DIR,
    ensure_directories,
    group_quantile,
    read_dta,
    write_dta,
)


def _load_raw_compustat(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Compustat extract not found: {path}")
    return read_dta(path)


def _prep_industries(df: pd.DataFrame) -> pd.DataFrame:
    """Create 2-,3-,4-digit NAICS codes mirroring the Stata logic."""
    for digits in (2, 3, 4):
        col = f"ind{digits}d"
        df[col] = pd.to_numeric(df["naics"].str.slice(0, digits), errors="coerce")
    return df


def _apply_trimming(df: pd.DataFrame) -> pd.DataFrame:
    """Replicate the sale/cogs percentile trimming."""
    df["s_g"] = df["sale"] / df["cogs"]
    for p in (0.01, 0.02, 0.03, 0.04, 0.05):
        df[f"s_g_p_{int(p*100)}"] = group_quantile(df, ["year"], "s_g", p)
    for p in (0.95, 0.96, 0.97, 0.98, 0.99):
        df[f"s_g_p_{int(p*100)}"] = group_quantile(df, ["year"], "s_g", p)

    df = df[(df["s_g"] > df["s_g_p_1"]) & (df["s_g"] < df["s_g_p_99"])]
    drop_cols = [c for c in df.columns if c.startswith("s_g_p_")]
    return df.drop(columns=drop_cols)


def create_data(
    include_interest_cogs: bool,
    raw_path: Optional[Path] = None,
    macro_path: Optional[Path] = None,
) -> Path:
    """Main entry point mirroring the Stata program."""
    ensure_directories()
    raw_path = raw_path or RAW_DATA_DIR / "june-24-2025_NA_exact_intExp_CAD.dta"
    macro_path = macro_path or RAW_DATA_DIR / "macro_vars.dta"

    df = _load_raw_compustat(raw_path)
    df = df[(df["fyear"] > 1954) & (df["fyear"] < 2025)].copy()
    df = df.rename(columns={"fyear": "year"})
    df = df.sort_values(["gvkey", "year"])

    df["nrobs"] = df.groupby(["gvkey", "year"])["year"].transform("size")
    df = df[~(((df["nrobs"] == 2) | (df["nrobs"] == 3)) & (df["indfmt"] == "FS"))]
    df = df.drop_duplicates(subset=["gvkey", "year"])
    df = df[df["naics"].notna() & (df["naics"] != "")]
    df = _prep_industries(df)

    df["tie"] = df["tie"].fillna(0)
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

    macro = read_dta(macro_path)
    df = df.merge(macro, on="year", how="inner", validate="m:1")

    df["sale_D"] = (df["sale"] / df["USGDP"]) * 100
    df["cogs_D"] = (df["cogs"] / df["USGDP"]) * 100
    df["xsga_D"] = (df["xsga"] / df["USGDP"]) * 100
    df["mkvalt_D"] = (df["mkvalt"] / df["USGDP"]) * 100
    df["dividend_D"] = (df["dvt"] / df["USGDP"]) * 100
    df["capital_D"] = (df["ppegt"] / df["USGDP"]) * 100
    df["intan_D"] = (df["intan"] / df["USGDP"]) * 100
    df["xlr_D"] = (df["xlr"] / df["USGDP"]) * 100
    df["kexp"] = df["usercost"] * df["capital_D"]

    df = df[df["sale_D"] >= 0]
    df = df[df["cogs_D"] >= 0]
    df = df[df["sale_D"] != 0]
    df = df[df["cogs_D"] != 0]
    df = df[df["sale_D"].notna() & df["cogs_D"].notna()]
    df = df[df["year"] > 1949]
    df = _apply_trimming(df)

    df["xsga"] = df["xsga"].fillna(np.nan)
    df = df[df["xsga"] >= 0]

    fname = "data_main_upd_trim_1_intExp.dta" if include_interest_cogs else "data_main_upd_trim_1.dta"
    out_path = INTERMEDIATE_DIR / fname
    write_dta(df, out_path)

    census_csv = RAW_DATA_DIR / "InferredDEUcensus.csv"
    if census_csv.exists():
        census_df = pd.read_csv(census_csv)
        write_dta(census_df, INTERMEDIATE_DIR / "census.dta")

    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replicate Create_Data.do in Python.")
    parser.add_argument("--include-interest-cogs", type=int, default=1, choices=[0, 1], help="Include interest expense in COGS.")
    parser.add_argument("--raw-path", type=Path, default=None, help="Optional override for the Compustat extract .dta.")
    parser.add_argument("--macro-path", type=Path, default=None, help="Optional override for macro_vars.dta.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out = create_data(bool(args.include_interest_cogs), args.raw_path, args.macro_path)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
