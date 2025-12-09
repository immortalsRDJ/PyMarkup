"""
Python translation of ``Create_Data.do``.

Builds the trimmed Compustat annual panel, deflates by the updated macro
variables, and saves the intermediate ``data_main_upd_trim_1*.dta`` files.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from path_plot_config import data_dir, int_dir

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


# -------------------------------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------------------------------

def _prep_industry_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Create 2-, 3-, and 4-digit NAICS codes mirroring the Stata logic."""
    for digits in (2, 3, 4):
        col = f"ind{digits}d"
        df[col] = pd.to_numeric(df["naics"].str.slice(0, digits), errors="coerce")
    return df


def _trim_sale_cogs_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the 1/99 percentile trim on sale/cogs within each year."""
    df = df.copy()
    df["s_g"] = df["sale"] / df["cogs"]
    p1 = df.groupby("year")["s_g"].transform(lambda x: x.quantile(0.01))
    p99 = df.groupby("year")["s_g"].transform(lambda x: x.quantile(0.99))
    trimmed = df[(df["s_g"] > p1) & (df["s_g"] < p99)]
    return trimmed.drop(columns=["s_g"])


def _load_macro(path: Path) -> pd.DataFrame:
    macro = pd.read_excel(path)
    macro.columns = macro.columns.str.strip()
    if not {"year", "USGDP", "usercost"}.issubset(macro.columns):
        raise ValueError("macro_vars_new.xlsx must contain year, USGDP, and usercost columns.")
    return macro[["year", "USGDP", "usercost"]]


# -------------------------------------------------------------------------------------------------
# Main routine
# -------------------------------------------------------------------------------------------------

def create_data(
    include_interest_cogs: bool,
    compustat_path: Optional[Path] = None,
    macro_path: Optional[Path] = None,
) -> Path:
    """Replicate the Create_Data.do flow for annual Compustat."""
    compustat_path = compustat_path or data_dir / "DLEU" / "Compustat_annual.dta"
    macro_path = macro_path or data_dir / "DLEU" / "macro_vars_new.xlsx"

    if not compustat_path.exists():
        raise FileNotFoundError(f"Compustat file not found: {compustat_path}")
    if not macro_path.exists():
        raise FileNotFoundError(f"Macro variable file not found: {macro_path}")

    LOGGER.info("Loading Compustat from %s", compustat_path)
    df = pd.read_stata(compustat_path)
    df = df[df["fyear"] > 1954].copy()
    df = df.rename(columns={"fyear": "year"})
    df = df.sort_values(["gvkey", "year"])

    df["nrobs"] = df.groupby(["gvkey", "year"])["year"].transform("size")
    df = df[~(((df["nrobs"] == 2) | (df["nrobs"] == 3)) & (df["indfmt"] == "FS"))]
    df = df.drop_duplicates(subset=["gvkey", "year"])
    df = df[df["naics"].notna() & (df["naics"] != "")]
    df = _prep_industry_codes(df)

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

    macro = _load_macro(macro_path)
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
    df = _trim_sale_cogs_ratio(df)

    df["xsga"] = df["xsga"].replace({0: np.nan})
    df = df[df["xsga"].isna() | (df["xsga"] >= 0)]

    out_path = int_dir / ("data_main_upd_trim_1_intExp.dta" if include_interest_cogs else "data_main_upd_trim_1.dta")
    int_dir.mkdir(parents=True, exist_ok=True)
    df.to_stata(out_path, write_index=False)
    LOGGER.info("Saved %s", out_path)
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replicate Create_Data.do in Python.")
    parser.add_argument("--include-interest-cogs", type=int, default=0, choices=[0, 1], help="Include interest expense in COGS.")
    parser.add_argument("--compustat-path", type=Path, default=None, help="Optional override for Compustat_annual.dta")
    parser.add_argument("--macro-path", type=Path, default=None, help="Optional override for macro_vars_new.xlsx")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    create_data(
        include_interest_cogs=bool(args.include_interest_cogs),
        compustat_path=args.compustat_path,
        macro_path=args.macro_path,
    )


if __name__ == "__main__":
    main()
