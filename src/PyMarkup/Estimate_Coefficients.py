"""
Python reimplementation of the Stata routine in ``Estimate_Coefficients.do``.

This script estimates production-function output elasticities using
rolling 5-year windows by 2-digit industry, following the Wooldridge-style
IV/GMM approach from the original .do file. It then produces the same
intermediate outputs (theta_W* and cost-share medians).

Key differences vs Stata version:
- Uses ``linearmodels`` IV2SLS for the GMM/IV step (one-step 2SLS with a
  robust covariance).
- Uses pandas for data wrangling; joins are handled with standard merges.
- Does not execute the commented-out ACF block from the Stata code.

Usage (example):
    python Estimate_Coefficients.py \
        --data-root /Users/.../RisingPricesRisingMarkupsReplication \
        --include-interest-cogs 0 \
        --drop-missing-sga 0

Expected inputs (relative to ``data_root``):
- Intermediate/data_main_upd_trim_1.dta (or *_intExp.dta if including interest)
- rawData/deu_observations.dta (only if drop_missing_sga == 1)

Outputs are written to ``Intermediate/`` mirroring the Stata filenames.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
import pandas as pd
from linearmodels.iv import IV2SLS


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


# -------------------------------------------------------------------------------------------------
# Data helpers
# -------------------------------------------------------------------------------------------------

def load_main_data(data_root: Path, include_interest_cogs: bool) -> pd.DataFrame:
    """Load the main trimmed Compustat panel with or without interest in COGS."""
    fname = (
        "data_main_upd_trim_1_intExp.dta"
        if include_interest_cogs
        else "data_main_upd_trim_1.dta"
    )
    path = data_root / "Intermediate" / fname
    LOGGER.info("Loading %s", path)
    return pd.read_stata(path)


def add_lags(df: pd.DataFrame, group: str, time: str, cols: Iterable[str]) -> pd.DataFrame:
    """Add L.col lags by group/time."""
    df = df.copy()
    df = df.sort_values([group, time])
    for col in cols:
        df[f"L.{col}"] = df.groupby(group)[col].shift(1)
    return df


def safe_log(series: pd.Series) -> pd.Series:
    """Natural log that returns NaN for nonpositive inputs."""
    return np.where(series > 0, np.log(series), np.nan)


# -------------------------------------------------------------------------------------------------
# IV estimation
# -------------------------------------------------------------------------------------------------

def run_iv(
    df: pd.DataFrame,
    dep: str,
    endog: str,
    exog: Iterable[str],
    instruments: Iterable[str],
) -> Optional[Dict[str, float]]:
    """
    Run a one-step IV/2SLS regression, returning coefficients of interest.
    Returns None if the regression cannot be estimated.
    """
    cols_needed = [dep, endog, *exog, *instruments]
    work = df[cols_needed].dropna()
    if work.shape[0] < 5:  # too few observations to be meaningful
        return None
    try:
        model = IV2SLS(
            dependent=work[dep],
            exog=pd.concat([pd.Series(1.0, index=work.index, name="const"), work[list(exog)]], axis=1),
            endog=work[[endog]],
            instruments=work[list(instruments)],
        )
        res = model.fit(cov_type="robust")
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("IV estimation failed: %s", exc)
        return None
    return res.params.to_dict()


def estimate_window_coeffs(df: pd.DataFrame) -> Tuple[Optional[Dict[str, float]], Optional[Dict[str, float]]]:
    """
    Estimate both specs (without and with SG&A) for a given window subset.
    Returns (spec1_coefs, spec2_coefs), each dict or None.
    """
    # Spec 1: y = b_c * c + b_k * k, instrument c with L.c, controls L.i, L.k2, L.k
    spec1 = run_iv(
        df,
        dep="r",
        endog="c",
        exog=["k", "L.i", "L.k2", "L.k"],
        instruments=["L.c"],
    )

    # Spec 2: add SG&A (lsga) and its polynomial terms as in the Stata code
    spec2 = run_iv(
        df,
        dep="r",
        endog="c",
        exog=["k", "lsga", "L.i", "L.k2", "L.lsga2", "L.k", "L.lsga"],
        instruments=["L.c"],
    )
    return spec1, spec2


# -------------------------------------------------------------------------------------------------
# Main estimation flow (mirrors the .do logic)
# -------------------------------------------------------------------------------------------------

def preprocess(
    df: pd.DataFrame,
    drop_missing_sga: bool,
    data_root: Path,
) -> pd.DataFrame:
    """Match the trimming and lag construction from the Stata code."""
    df = df.copy()

    # Cost shares
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

        deu_path = data_root / "rawData" / "deu_observations.dta"
        if deu_path.exists():
            deu = pd.read_stata(deu_path)[["gvkey", "year"]].drop_duplicates()
            df = df.merge(deu, on=["gvkey", "year"], how="inner")
        else:
            LOGGER.warning("DEU observations file not found; proceeding without that join.")
    else:
        df["s_g2"] = df["xsga"] / df["sale"]
        p1 = df.groupby("year")["s_g2"].transform(lambda x: x.quantile(0.01))
        p99 = df.groupby("year")["s_g2"].transform(lambda x: x.quantile(0.99))
        df = df[
            (~df["s_g2"].notna())
            | ((df["s_g2"] >= p1) & (df["s_g2"] <= p99))
        ]
        df = df.drop(columns=["s_g2"])

    # Firm id
    df["id"] = df["gvkey"].astype("category").cat.codes
    df = df[df["id"].notna()]

    # Core variables
    df["r"] = np.log(df["sale_D"])
    df["y"] = df["r"]
    df["c"] = np.log(df["cogs_D"])
    df["c2"] = df["c"] ** 2
    df["c3"] = df["c"] ** 3

    df["k"] = np.log(df["capital_D"])
    df["k2"] = df["k"] ** 2
    df["ck"] = df["c"] * df["k"]
    df["k3"] = df["k"] ** 3
    df["depr"] = 0.1

    df["lsga"] = safe_log(df["xsga_D"])
    df["lsga2"] = df["lsga"] ** 2

    df = add_lags(df, group="id", time="year", cols=["c", "i", "k"])

    df["K"] = np.exp(df["k"])
    df = add_lags(df, group="id", time="year", cols=["K"])
    df["Inv"] = df["K"] - (1 - df["depr"]) * df["L.K"]
    df["i"] = safe_log(df["Inv"])
    df["i2"] = df["i"] ** 2
    df["i3"] = df["i"] ** 3
    df["ik"] = df["i"] * df["k"]

    return df


def build_result_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Create the container for rolling-window coefficients."""
    res = df[["ind2d", "year"]].drop_duplicates().copy()
    for col in ["theta_WI1_ct", "theta_WI2_ct", "theta_WI2_xt", "theta_WI1_kt", "theta_WI2_kt"]:
        res[col] = np.nan
    return res


def assign_coeffs(res: pd.DataFrame, cond: pd.Series, spec1: Optional[Dict[str, float]], spec2: Optional[Dict[str, float]]) -> None:
    """Assign estimated coefficients to the result frame under the provided condition."""
    if spec1:
        if "c" in spec1:
            res.loc[cond, "theta_WI1_ct"] = spec1["c"]
        if "k" in spec1:
            res.loc[cond, "theta_WI1_kt"] = spec1["k"]
    if spec2:
        if "c" in spec2:
            res.loc[cond, "theta_WI2_ct"] = spec2["c"]
        if "lsga" in spec2:
            res.loc[cond, "theta_WI2_xt"] = spec2["lsga"]
        if "k" in spec2:
            res.loc[cond, "theta_WI2_kt"] = spec2["k"]


def run_rolling_windows(df: pd.DataFrame) -> pd.DataFrame:
    """Replicate the rolling-window estimation and assignment logic."""
    res = build_result_frame(df)

    # Helper to subset and estimate
    def estimate_for_subset(subset: pd.DataFrame, assign_mask: pd.Series) -> None:
        spec1, spec2 = estimate_window_coeffs(subset)
        if spec1 or spec2:
            assign_coeffs(res, assign_mask, spec1, spec2)

    # Early windows: industries 1-16, 18-25, and special industry 17
    for s in range(1, 17):
        subset = df[(df["nrind2"] == s) & (df["year"] < 1972) & df[["r", "c", "k", "L.c", "L.i", "L.k"]].notna().all(axis=1)]
        if subset.shape[0] > 15:
            mask = (res["ind2d"] == s) & (res["year"] < 1970)
            estimate_for_subset(subset, mask)

    for s in range(18, 26):
        subset = df[(df["nrind2"] == s) & (df["year"] < 1972) & df[["r", "c", "k", "L.c", "L.i", "L.k"]].notna().all(axis=1)]
        if subset.shape[0] > 15:
            mask = (res["ind2d"] == s) & (res["year"] < 1970)
            estimate_for_subset(subset, mask)

    subset_17 = df[(df["nrind2"] == 17) & (df["year"] < 1985) & df[["r", "c", "k", "L.c", "L.i", "L.k"]].notna().all(axis=1)]
    if subset_17.shape[0] > 15:
        mask = (res["ind2d"] == 17) & (res["year"] < 1985)
        estimate_for_subset(subset_17, mask)

    # Rolling windows by year
    for t in range(1970, 2025):
        window_mask = (df["year"] >= t - 2) & (df["year"] <= t + 2)

        for s in range(1, 17):
            subset = df[
                (df["nrind2"] == s)
                & window_mask
                & df[["r", "c", "k", "L.c", "L.i", "L.k"]].notna().all(axis=1)
            ]
            if subset.shape[0] > 15:
                mask = (res["ind2d"] == s) & (res["year"] == t)
                estimate_for_subset(subset, mask)

        for s in range(18, 26):
            subset = df[
                (df["nrind2"] == s)
                & window_mask
                & df[["r", "c", "k", "L.c", "L.i", "L.k"]].notna().all(axis=1)
            ]
            if subset.shape[0] > 15:
                mask = (res["ind2d"] == s) & (res["year"] == t)
                estimate_for_subset(subset, mask)

        if t >= 1985:
            subset = df[
                (df["nrind2"] == 17)
                & window_mask
                & df[["r", "c", "k", "L.c", "L.i", "L.k"]].notna().all(axis=1)
            ]
            if subset.shape[0] > 15:
                mask = (res["ind2d"] == 17) & (res["year"] == t)
                estimate_for_subset(subset, mask)

    return res


def save_theta_outputs(
    res: pd.DataFrame,
    df: pd.DataFrame,
    data_root: Path,
    include_interest_cogs: bool,
    drop_missing_sga: bool,
) -> None:
    """Persist theta_W* and theta_c* outputs to the Intermediate folder."""
    interm = data_root / "Intermediate"
    interm.mkdir(parents=True, exist_ok=True)

    # theta_W rolling outputs
    fname_w = "theta_W_s_window_"
    fname_w += "DEUSample_" if drop_missing_sga else "fullSample_"
    fname_w += "intExp.dta" if include_interest_cogs else "dta"
    out_w = interm / fname_w
    res.sort_values(["ind2d", "year"]).to_stata(out_w, write_index=False)
    LOGGER.info("Saved %s", out_w)

    # Cost-share output elasticity estimates (medians)
    cs = df.copy()
    cs["cs2d"] = cs.groupby(["year", "ind2d"])["costshare1"].transform("median")
    cs["cs3d"] = cs.groupby(["year", "ind3d"])["costshare1"].transform("median")
    cs["cs4d"] = cs.groupby(["year", "ind4d"])["costshare1"].transform("median")
    cs_out = cs[["ind2d", "cs2d", "cs3d", "cs4d", "year"]].drop_duplicates().sort_values(["ind2d", "year"])

    fname_c = "theta_c_"
    fname_c += "DEUSample_" if drop_missing_sga else "fullSample_"
    fname_c += "intExp.dta" if include_interest_cogs else "dta"
    out_c = interm / fname_c
    cs_out.to_stata(out_c, write_index=False)
    LOGGER.info("Saved %s", out_c)


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate production-function elasticities (Python port of Estimate_Coefficients.do).")
    parser.add_argument("--data-root", type=Path, required=True, help="Path to RisingPricesRisingMarkupsReplication directory (contains Intermediate/, rawData/, etc.)")
    parser.add_argument("--include-interest-cogs", type=int, choices=[0, 1], default=0, help="Match Stata flag includeinterestcogs.")
    parser.add_argument("--drop-missing-sga", type=int, choices=[0, 1], default=0, help="Match Stata flag dropmissingsga.")
    args = parser.parse_args()

    df = load_main_data(args.data_root, include_interest_cogs=bool(args.include_interest_cogs))
    df = preprocess(df, drop_missing_sga=bool(args.drop_missing_sga), data_root=args.data_root)
    res = run_rolling_windows(df)
    save_theta_outputs(
        res=res,
        df=df,
        data_root=args.data_root,
        include_interest_cogs=bool(args.include_interest_cogs),
        drop_missing_sga=bool(args.drop_missing_sga),
    )


if __name__ == "__main__":
    main()
