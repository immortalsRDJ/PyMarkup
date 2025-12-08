"""
Python translation of ``Compute_Markups.do``.

Uses the estimated production elasticities to construct firm-level markups and
aggregate them under various weighting schemes, writing .dta files identical to
the Stata pipeline.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .utils import INTERMEDIATE_DIR, RAW_DATA_DIR, ensure_directories, read_dta, write_dta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


def _load_main(include_interest_cogs: bool) -> pd.DataFrame:
    fname = "data_main_upd_trim_1_intExp.dta" if include_interest_cogs else "data_main_upd_trim_1.dta"
    path = INTERMEDIATE_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run create_data.py first.")
    return read_dta(path)


def _apply_screening(df: pd.DataFrame, drop_missing_sga: bool) -> pd.DataFrame:
    df = df.copy()
    df["costshare1"] = df["cogs_D"] / (df["cogs_D"] + df["kexp"])
    df["costshare2"] = df["cogs_D"] / (df["cogs_D"] + df["xsga_D"] + df["kexp"])
    if drop_missing_sga:
        for s in (1, 2):
            p1 = df.groupby("year")[f"costshare{s}"].transform(lambda x: x.quantile(0.01))
            p99 = df.groupby("year")[f"costshare{s}"].transform(lambda x: x.quantile(0.99))
            df = df[
                (df[f"costshare{s}"] > 0)
                & df[f"costshare{s}"].notna()
                & (df[f"costshare{s}"] > p1)
                & (df[f"costshare{s}"] < p99)
            ]
        deu_path = RAW_DATA_DIR / "deu_observations.dta"
        if deu_path.exists():
            deu = read_dta(deu_path)[["gvkey", "year"]].drop_duplicates()
            df = df.merge(deu, on=["gvkey", "year"], how="inner")
    else:
        df["s_g2"] = df["sale"] / df["xsga"]
        p1 = df.groupby("year")["s_g2"].transform(lambda x: x.quantile(0.01))
        p99 = df.groupby("year")["s_g2"].transform(lambda x: x.quantile(0.99))
        df = df[(df["s_g2"] >= p1) | df["s_g2"].isna()]
        df = df[(df["s_g2"] <= p99) | df["s_g2"].isna()]
        df = df.drop(columns=["s_g2"])
    return df


def _theta_files(include_interest_cogs: bool, drop_missing_sga: bool, drop3254: bool) -> tuple[Path, Path, Path]:
    if include_interest_cogs and drop_missing_sga:
        suffix = "_DEUSample_intExp"
    elif (not include_interest_cogs) and drop_missing_sga:
        suffix = "_DEUSample"
    elif include_interest_cogs and (not drop_missing_sga):
        suffix = "_fullSample_intExp"
    elif (not include_interest_cogs) and (not drop_missing_sga) and drop3254:
        suffix = "_no3254"
    else:
        suffix = "_fullSample"
    return (
        INTERMEDIATE_DIR / f"theta_W_s_window{suffix}.dta",
        INTERMEDIATE_DIR / f"theta_acf{suffix}.dta",
        INTERMEDIATE_DIR / f"theta_c{suffix}.dta",
    )


def _merge_thetas(df: pd.DataFrame, include_interest_cogs: bool, drop_missing_sga: bool, drop3254: bool) -> pd.DataFrame:
    theta_w_path, theta_acf_path, theta_c_path = _theta_files(include_interest_cogs, drop_missing_sga, drop3254)
    for path in (theta_w_path, theta_acf_path):
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}; run estimate_coefficients.py first.")
    df = df.merge(read_dta(theta_w_path), on=["ind2d", "year"], how="left", validate="m:1")
    df = df.merge(read_dta(theta_acf_path), on=["ind2d", "year"], how="left", validate="m:1")
    if theta_c_path.exists():
        df = df.merge(read_dta(theta_c_path), on=["ind2d", "year"], how="left")
    return df


def _aggregate_markups(df: pd.DataFrame, mu_col: str, weight_col: str) -> pd.Series:
    series = df.groupby("year").apply(lambda g: np.sum(g[weight_col] * g[mu_col]))
    return series.sort_index()


def compute_markups(include_interest_cogs: bool, drop_missing_sga: bool, drop3254: bool) -> Path:
    ensure_directories()
    df = _load_main(include_interest_cogs)
    df = _apply_screening(df, drop_missing_sga)
    if drop3254:
        df = df[df["ind4d"] != 3254]

    df["id"] = df["gvkey"]
    df = _merge_thetas(df, include_interest_cogs, drop_missing_sga, drop3254)

    df["mu_10"] = df["theta_WI1_ct"] * (df["sale_D"] / df["cogs_D"])
    df["mu_11"] = df["theta_WI2_ct"] * (df["sale_D"] / df["cogs_D"])
    df["mu_12"] = df["theta_acf"] * (df["sale_D"] / df["cogs_D"])

    df["newSGA"] = df["xsga_D"].fillna(0)
    df["TOTSALES"] = df.groupby("year")["sale_D"].transform("sum")
    df["share_firm_agg"] = df["sale_D"] / df["TOTSALES"]
    df["TOTCOGS"] = df.groupby("year")["cogs_D"].transform("sum")
    df["share_firm_agg_cogs"] = df["cogs_D"] / df["TOTCOGS"]
    df["TOTOPEX"] = df.groupby("year")[["cogs_D", "newSGA"]].transform("sum").sum(axis=1)
    df["share_firm_agg_opex"] = (df["cogs_D"] + df["newSGA"]) / df["TOTOPEX"]

    agg_results = pd.DataFrame({"year": sorted(df["year"].unique())})
    for i, col in ((10, "mu_10"), (11, "mu_11"), (12, "mu_12")):
        agg_results[f"MARKUP{i}_AGG"] = _aggregate_markups(df, col, "share_firm_agg").values
        agg_results[f"MARKUP{i}_AGGCOGS"] = _aggregate_markups(df, col, "share_firm_agg_cogs").values
        agg_results[f"MARKUP{i}_AGGOPEX"] = _aggregate_markups(df, col, "share_firm_agg_opex").values

    df_no52 = df[df["ind2d"] != 52]
    agg_no52 = pd.DataFrame({"year": sorted(df_no52["year"].unique())})
    for i, col in ((10, "mu_10"), (11, "mu_11"), (12, "mu_12")):
        agg_no52[f"MARKUP{i}_AGG_no52"] = _aggregate_markups(df_no52, col, "share_firm_agg").values
        agg_no52[f"MARKUP{i}_AGGCOGS_no52"] = _aggregate_markups(df_no52, col, "share_firm_agg_cogs").values
        agg_no52[f"MARKUP{i}_AGGOPEX_no52"] = _aggregate_markups(df_no52, col, "share_firm_agg_opex").values

    df_man = df[df["ind2d"].isin([31, 32, 33])].copy()
    df_man["share_firm_agg_man"] = df_man["sale_D"] / df_man.groupby("year")["sale_D"].transform("sum")
    agg_man = pd.DataFrame({"year": sorted(df_man["year"].unique())})
    agg_man["MARKUP10_AGG_man"] = _aggregate_markups(df_man, "mu_10", "share_firm_agg_man").values

    df_man32 = df[df["ind2d"] == 32].copy()
    df_man32["share_firm_agg_man32"] = df_man32["sale_D"] / df_man32.groupby("year")["sale_D"].transform("sum")
    agg_man32 = pd.DataFrame({"year": sorted(df_man32["year"].unique())})
    agg_man32["MARKUP10_AGG_man32"] = _aggregate_markups(df_man32, "mu_10", "share_firm_agg_man32").values

    out = agg_results.merge(agg_no52, on="year", how="left").merge(agg_man, on="year", how="left").merge(agg_man32, on="year", how="left")

    if (not include_interest_cogs) and drop_missing_sga:
        out = out.rename(
            columns={
                "MARKUP10_AGG": "MARKUP10_AGG_DEU",
                "MARKUP10_AGG_no52": "MARKUP10_AGG_DEU_no52",
                "MARKUP10_AGGCOGS": "MARKUP10_AGGCOGS_DEU",
                "MARKUP10_AGGCOGS_no52": "MARKUP10_AGGCOGS_DEU_no52",
                "MARKUP10_AGGOPEX": "MARKUP10_AGGOPEX_DEU",
                "MARKUP10_AGGOPEX_no52": "MARKUP10_AGGOPEX_DEU_no52",
                "MARKUP12_AGG": "MARKUP12_AGG_DEU",
                "MARKUP12_AGG_no52": "MARKUP12_AGG_DEU_no52",
                "MARKUP10_AGG_man": "MARKUP10_AGG_DEU_man",
                "MARKUP10_AGG_man32": "MARKUP10_AGG_DEU_man32",
            }
        )
        out_path = INTERMEDIATE_DIR / "markup_DEU.dta"
    elif include_interest_cogs and (not drop_missing_sga):
        out = out.rename(
            columns={
                "MARKUP10_AGG": "MARKUP10_AGG_full_intExp",
                "MARKUP10_AGG_no52": "MARKUP10_AGG_full_int_no52",
                "MARKUP12_AGG": "MARKUP12_AGG_full_intExp",
                "MARKUP12_AGG_no52": "MARKUP12_AGG_full_int_no52",
            }
        )
        out_path = INTERMEDIATE_DIR / "markup_full_intExp.dta"
    elif (not include_interest_cogs) and (not drop_missing_sga) and drop3254:
        out = out.rename(
            columns={
                "MARKUP10_AGG": "MARKUP10_AGG_no3254",
                "MARKUP10_AGG_no52": "MARKUP10_AGG_full_no52_no3254",
            }
        )
        out_path = INTERMEDIATE_DIR / "markup_full_no3254.dta"
    else:
        out = out.rename(
            columns={
                "MARKUP10_AGG": "MARKUP10_AGG_full",
                "MARKUP10_AGG_no52": "MARKUP10_AGG_full_no52",
                "MARKUP12_AGG": "MARKUP12_AGG_full",
                "MARKUP12_AGG_no52": "MARKUP12_AGG_full_no52",
                "MARKUP10_AGGCOGS": "MARKUP10_AGGCOGS_full",
                "MARKUP10_AGGCOGS_no52": "MARKUP10_AGGCOGS_full_no52",
                "MARKUP10_AGGOPEX": "MARKUP10_AGGOPEX_full",
                "MARKUP10_AGGOPEX_no52": "MARKUP10_AGGOPEX_full_no52",
                "MARKUP10_AGG_man": "MARKUP10_AGG_full_man",
                "MARKUP10_AGG_man32": "MARKUP10_AGG_full_man32",
            }
        )
        out_path = INTERMEDIATE_DIR / "markup_full.dta"

    write_dta(out, out_path)
    LOGGER.info("Saved %s", out_path)
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replicate Compute_Markups.do in Python.")
    parser.add_argument("--include-interest-cogs", type=int, default=0, choices=[0, 1])
    parser.add_argument("--drop-missing-sga", type=int, default=0, choices=[0, 1])
    parser.add_argument("--drop3254", type=int, default=0, choices=[0, 1])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    compute_markups(bool(args.include_interest_cogs), bool(args.drop_missing_sga), bool(args.drop3254))


if __name__ == "__main__":
    main()
