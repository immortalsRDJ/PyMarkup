"""
Python replacement for ``0.4 Create Main Datasets.do``.

Builds the annual and quarterly main datasets, computes firm-level markups
using the estimated theta values, and exports the CSVs consumed by downstream
figure/table scripts.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from Estimate_Coefficients import theta_suffix
from path_plot_config import data_dir, int_dir

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


def _load_naics_desc(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(columns={"sector_definition": "ind2d_definition"})
    df["ind2d"] = pd.to_numeric(df["ind2d"], errors="coerce")
    return df[["ind2d", "ind2d_definition"]]


def _load_ppi(path: Path, period_col: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(columns={"naics_code": "naics"})
    df["naics"] = df["naics"].astype(str).str.strip()
    df[period_col] = df[period_col].astype(str).str.strip()
    return df[[period_col, "naics", "ppi"]]


def _load_cpi(path: Path, period_col: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    df[period_col] = df[period_col].astype(str).str.strip()
    return df[[period_col, "cpi"]]


def _apply_costshare_trim(df: pd.DataFrame, time_col: str) -> pd.DataFrame:
    df = df.copy()
    df["costshare0"] = 0.85
    df["costshare1"] = df["cogs_D"] / (df["cogs_D"] + df["kexp"])
    df["costshare2"] = df["cogs_D"] / (df["cogs_D"] + df["xsga_D"] + df["kexp"])
    for col in ("costshare1", "costshare2"):
        p1 = df.groupby(time_col)[col].transform(lambda x: x.quantile(0.01))
        p99 = df.groupby(time_col)[col].transform(lambda x: x.quantile(0.99))
        df = df[
            (df[col] > 0)
            & df[col].notna()
            & (df[col] > p1)
            & (df[col] < p99)
        ]
    return df


def _attach_theta(df: pd.DataFrame, theta_w_path: Path, theta_acf_path: Path) -> pd.DataFrame:
    if not theta_w_path.exists():
        raise FileNotFoundError(f"Missing theta file {theta_w_path}. Run 0.3 theta_estimation.py first.")
    theta = pd.read_stata(theta_w_path)
    theta.columns = theta.columns.str.lower()
    theta = theta.rename(columns={"theta_wi1_ct": "theta_WI1_ct"})
    df = df.merge(theta[["ind2d", "year", "theta_WI1_ct"]], on=["ind2d", "year"], how="left")

    if theta_acf_path.exists():
        theta_acf = pd.read_stata(theta_acf_path)
        theta_acf.columns = theta_acf.columns.str.lower()
        theta_acf = theta_acf.rename(columns={"theta_acf": "theta_acf_val"})
        df = df.merge(theta_acf[["ind2d", "year", "theta_acf_val"]], on=["ind2d", "year"], how="left")
    else:
        LOGGER.warning("theta_acf file missing (%s); OP/ACF markups will be NaN.", theta_acf_path)
        df["theta_acf_val"] = np.nan
    return df


def _compute_mu(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["mu_10"] = df["theta_WI1_ct"] * (df["sale_D"] / df["cogs_D"])
    df["mu_12"] = df["theta_acf_val"] * (df["sale_D"] / df["cogs_D"])
    return df


def _aggregate_markup(df: pd.DataFrame, time_col: str, markup_col: str = "mu_10") -> pd.DataFrame:
    df = df.copy()
    df["TOTSALES"] = df.groupby(time_col)["sale_D"].transform("sum")
    df["share_firm_agg"] = df["sale_D"] / df["TOTSALES"]
    agg = (
        df.groupby(time_col)
        .apply(lambda g: np.sum(g["share_firm_agg"] * g[markup_col].fillna(0)))
        .reset_index(name="MARKUP_spec1")
    )
    return agg


def _save_for_figure1(df: pd.DataFrame, limited: bool, out_dir: Path, markup_col: str = "mu_10", label: str = "") -> None:
    filtered = df if not limited else df[df["ppi"].notna()]
    agg = _aggregate_markup(filtered, "year", markup_col=markup_col)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{label}" if label else ""
    fname = ("agg_markup_limited_to_PPI matched_annual" + suffix + ".csv") if limited else ("agg_markup_annual" + suffix + ".csv")
    agg.to_csv(out_dir / fname, index=False)
    LOGGER.info("Saved %s", out_dir / fname)


def prepare_annual(data_root: Path, include_interest_cogs: bool, drop_missing_sga: bool) -> None:
    naics_desc = _load_naics_desc(data_root / "Input" / "Other" / "NAICS_2D_Description.xlsx")
    ppi = _load_ppi(data_root / "Input" / "PPI" / "PPI_annual.csv", "year")
    cpi = _load_cpi(data_root / "Input" / "CPI" / "CPI_annual.csv", "year")

    fname = "data_main_upd_trim_1_intExp.dta" if include_interest_cogs else "data_main_upd_trim_1.dta"
    main_path = data_root / "Intermediate" / fname
    if not main_path.exists():
        raise FileNotFoundError(f"Missing {main_path}. Run Create_Data.py first.")

    df = pd.read_stata(main_path)
    df["naics"] = df["naics"].astype(str).str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    df = df.merge(ppi, on=["year", "naics"], how="left")
    df = df.merge(cpi, on="year", how="left")
    df = df.merge(naics_desc, on="ind2d", how="left")

    df = _apply_costshare_trim(df, time_col="year")
    df = df[df["year"] >= 1955]
    df = df[df["ind2d"] != 99]

    suffix = theta_suffix(include_interest_cogs, drop_missing_sga)
    theta_w_path = data_root / "Intermediate" / f"theta_W_s_window_{suffix}.dta"
    theta_acf_path = data_root / "Intermediate" / f"theta_acf_{suffix}.dta"
    df = _attach_theta(df, theta_w_path, theta_acf_path)
    df = _compute_mu(df)

    df = df.rename(columns={"mu_10": "firm_level_markup", "mu_12": "firm_level_markup_acf"})
    annual_out = df[
        ["gvkey", "conm", "year", "naics", "ind2d", "ind2d_definition", "firm_level_markup", "firm_level_markup_acf", "sale", "sale_D", "cogs", "cogs_D", "ppi", "cpi"]
    ].copy()
    int_dir.mkdir(parents=True, exist_ok=True)
    annual_out.to_csv(int_dir / "main_annual.csv", index=False)
    LOGGER.info("Saved %s", int_dir / "main_annual.csv")

    out_dir = data_root / "Intermediate" / "For Figure 1"
    _save_for_figure1(df, limited=False, out_dir=out_dir, markup_col="mu_10")
    _save_for_figure1(df, limited=True, out_dir=out_dir, markup_col="mu_10")
    # Optional OP/ACF aggregate outputs (won't affect plotting)
    _save_for_figure1(df, limited=False, out_dir=out_dir, markup_col="mu_12", label="op_acf")
    _save_for_figure1(df, limited=True, out_dir=out_dir, markup_col="mu_12", label="op_acf")


def prepare_quarterly(data_root: Path, include_interest_cogs: bool, drop_missing_sga: bool) -> None:
    naics_desc = _load_naics_desc(data_root / "Input" / "Other" / "NAICS_2D_Description.xlsx")
    ppi = _load_ppi(data_root / "Input" / "PPI" / "PPI_quarterly.csv", "quarter")
    cpi = _load_cpi(data_root / "Input" / "CPI" / "CPI_quarterly.csv", "quarter")
    macro = pd.read_excel(data_root / "Input" / "DLEU" / "macro_vars_new.xlsx")
    macro.columns = macro.columns.str.strip()
    macro = macro[["year", "USGDP", "usercost"]]

    comp_path = data_root / "Input" / "DLEU" / "Compustat_quarterly.dta"
    if not comp_path.exists():
        raise FileNotFoundError(f"Missing {comp_path}")
    df = pd.read_stata(comp_path)

    df = df[df["fqtr"].notna()]
    df["fyearq"] = df["fyearq"].astype(int).astype(str)
    df["fqtr"] = df["fqtr"].astype(int).astype(str)
    df["quarter"] = df["fyearq"] + "Q" + df["fqtr"]

    df = df.sort_values(["gvkey", "quarter"])
    df["nrobs"] = df.groupby(["gvkey", "quarter"])["quarter"].transform("size")
    df = df[~(((df["nrobs"] == 2) | (df["nrobs"] == 3)) & (df["indfmt"] == "FS"))]
    df = df.drop_duplicates(subset=["gvkey", "quarter"])

    df = df[df["naics"].notna() & (df["naics"] != "")]
    for digits in (2, 3, 4):
        df[f"ind{digits}d"] = pd.to_numeric(df["naics"].str.slice(0, digits), errors="coerce")

    keep_cols = ["gvkey", "fyearq", "quarter", "naics", "ind2d", "ind3d", "ind4d", "saleq", "cogsq", "xsgaq", "ppegtq", "conm"]
    df = df[keep_cols].copy()
    df[["saleq", "cogsq", "xsgaq", "ppegtq"]] = df[["saleq", "cogsq", "xsgaq", "ppegtq"]] * 1000

    df = df.rename(columns={"fyearq": "year"})
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    df = df.merge(macro, on="year", how="inner")
    df["naics"] = df["naics"].astype(str).str.strip()
    df = df.merge(ppi, on=["quarter", "naics"], how="left")
    df = df.merge(cpi, on="quarter", how="left")
    df = df.merge(naics_desc, on="ind2d", how="left")

    df["sale_D"] = (df["saleq"] / df["USGDP"]) * 100
    df["cogs_D"] = (df["cogsq"] / df["USGDP"]) * 100
    df["xsga_D"] = (df["xsgaq"] / df["USGDP"]) * 100
    df["capital_D"] = (df["ppegtq"] / df["USGDP"]) * 100
    df["kexp"] = df["usercost"] * df["capital_D"]

    df = df[df["sale_D"] >= 0]
    df = df[df["cogs_D"] >= 0]
    df = df[df["xsgaq"] >= 0]

    df["s_g"] = df["saleq"] / df["cogsq"]
    p1 = df.groupby("quarter")["s_g"].transform(lambda x: x.quantile(0.01))
    p99 = df.groupby("quarter")["s_g"].transform(lambda x: x.quantile(0.99))
    df = df[(df["s_g"] > p1) & (df["s_g"] < p99)]
    df = df.drop(columns=["s_g"])

    df = _apply_costshare_trim(df, time_col="quarter")
    suffix = theta_suffix(include_interest_cogs, drop_missing_sga)
    theta_w_path = data_root / "Intermediate" / f"theta_W_s_window_{suffix}.dta"
    theta_acf_path = data_root / "Intermediate" / f"theta_acf_{suffix}.dta"
    df = _attach_theta(df, theta_w_path, theta_acf_path)
    df = _compute_mu(df)

    df = df[df["year"] >= 1955]
    df = df[df["ind2d"] != 99]
    df = df.rename(columns={"mu_10": "firm_level_markup", "mu_12": "firm_level_markup_acf"})

    quarterly_out = df[
        ["gvkey", "conm", "year", "quarter", "naics", "ind2d", "ind2d_definition", "firm_level_markup", "firm_level_markup_acf", "saleq", "sale_D", "cogsq", "cogs_D", "ppi", "cpi"]
    ].copy()
    quarterly_out.to_csv(int_dir / "main_quarterly.csv", index=False)
    LOGGER.info("Saved %s", int_dir / "main_quarterly.csv")


def main(
    data_root: Optional[Path] = None,
    include_interest_cogs: bool = False,
    drop_missing_sga: bool = False,
) -> None:
    root = data_root or Path(__file__).resolve().parents[2]
    prepare_annual(root, include_interest_cogs=include_interest_cogs, drop_missing_sga=drop_missing_sga)
    prepare_quarterly(root, include_interest_cogs=include_interest_cogs, drop_missing_sga=drop_missing_sga)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Python replacement for 0.4 Create Main Datasets.do")
    parser.add_argument("--data-root", type=Path, default=None, help="Project root containing Input/ and Intermediate/.")
    parser.add_argument("--include-interest-cogs", type=int, choices=[0, 1], default=0)
    parser.add_argument("--drop-missing-sga", type=int, choices=[0, 1], default=0)
    args = parser.parse_args()

    main(
        data_root=args.data_root,
        include_interest_cogs=bool(args.include_interest_cogs),
        drop_missing_sga=bool(args.drop_missing_sga),
    )
