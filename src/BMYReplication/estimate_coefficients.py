"""
Python translation of ``Estimate_Coefficients.do``.

This script estimates production-function coefficients using rolling 5-year
windows by industry and exports the same intermediate .dta files that the Stata
pipeline expects:
- theta_W_s_window_*.dta (windowed IV/GMM elasticities)
- theta_c_*.dta (median cost-share elasticities)
- theta_acf_*.dta (ACF-style GMM elasticities)
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import scipy.optimize
import statsmodels.api as sm
from linearmodels.iv import IV2SLS

from .utils import (
    INTERMEDIATE_DIR,
    RAW_DATA_DIR,
    ensure_directories,
    lag_by_group,
    read_dta,
    safe_log,
    write_dta,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------

def _load_main(include_interest_cogs: bool) -> pd.DataFrame:
    fname = "data_main_upd_trim_1_intExp.dta" if include_interest_cogs else "data_main_upd_trim_1.dta"
    path = INTERMEDIATE_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"Run create_data.py first. Missing {path}")
    df = read_dta(path)
    df["id"] = df["gvkey"]
    df = df.dropna(subset=["id"])
    return df


def _drop_missing_sga(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the DEU overlap trims from the Stata code."""
    df = df.copy()
    for s in (1, 2):
        df[f"costshare{s}"] = df["cogs_D"] / (df["cogs_D"] + (0 if s == 1 else df["xsga_D"]) + df["kexp"])
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
    return df


def _drop_trim_sga_ratio(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["s_g2"] = df["xsga"] / df["sale"]
    p1 = df.groupby("year")["s_g2"].transform(lambda x: x.quantile(0.01))
    p99 = df.groupby("year")["s_g2"].transform(lambda x: x.quantile(0.99))
    df = df[(df["s_g2"] >= p1) | df["s_g2"].isna()]
    df = df[(df["s_g2"] <= p99) | df["s_g2"].isna()]
    df = df.drop(columns=["s_g2"])
    return df


def _prep_common_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["nrind2"] = df["ind2d"]
    df["r"] = safe_log(df["sale_D"])
    df["y"] = df["r"]
    df["c"] = safe_log(df["cogs_D"])
    df["k"] = safe_log(df["capital_D"])
    df["c2"] = df["c"] ** 2
    df["c3"] = df["c"] ** 3
    df["k2"] = df["k"] ** 2
    df["k3"] = df["k"] ** 3
    df["ck"] = df["c"] * df["k"]
    df["lsga"] = safe_log(df["xsga_D"])
    df["lsga2"] = df["lsga"] ** 2
    df["depr"] = 0.1
    df["K"] = np.exp(df["k"])
    df = df.sort_values(["id", "year"])
    df["Inv"] = df["K"] - (1 - df["depr"]) * df.groupby("id")["K"].shift(1)
    df["i"] = safe_log(df["Inv"])
    df["i2"] = df["i"] ** 2
    df["i3"] = df["i"] ** 3
    df["ik"] = df["i"] * df["k"]
    df = lag_by_group(df, "id", "year", ["c", "k", "i", "k2", "lsga", "lsga2"])
    return df


def _market_shares(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["totsales2d"] = df.groupby(["ind2d", "year"])["sale_D"].transform("sum")
    df["totsales3d"] = df.groupby(["ind3d", "year"])["sale_D"].transform("sum")
    df["totsales4d"] = df.groupby(["ind4d", "year"])["sale_D"].transform("sum")
    df["ms2d"] = df["sale_D"] / df["totsales2d"]
    df["ms3d"] = df["sale_D"] / df["totsales3d"]
    df["ms4d"] = df["sale_D"] / df["totsales4d"]
    return df


# --------------------------------------------------------------------------------------
# IV / GMM estimators
# --------------------------------------------------------------------------------------

def _run_iv(
    df: pd.DataFrame,
    dep: str,
    endog: str,
    exog: Iterable[str],
    instruments: Iterable[str],
) -> Optional[Dict[str, float]]:
    cols = [dep, endog, *exog, *instruments]
    work = df[cols].dropna()
    if work.shape[0] < 10:
        return None
    exog_df = pd.concat([pd.Series(1.0, index=work.index, name="const"), work[list(exog)]], axis=1)
    try:
        res = IV2SLS(work[dep], exog=exog_df, endog=work[[endog]], instruments=work[list(instruments)]).fit(cov_type="robust")
    except Exception as exc:  # noqa: BLE001
        LOGGER.debug("IV failure: %s", exc)
        return None
    return res.params.to_dict()


def _estimate_window(df: pd.DataFrame) -> Tuple[Optional[Dict[str, float]], Optional[Dict[str, float]]]:
    spec1 = _run_iv(df, "r", "c", ["k", "L.i", "L.k2", "L.k"], ["L.c"])
    spec2 = _run_iv(df, "r", "c", ["k", "lsga", "L.i", "L.k2", "L.lsga2", "L.k", "L.lsga"], ["L.c"])
    return spec1, spec2


def _gmm_objective(betas: np.ndarray, phi: np.ndarray, phi_lag: np.ndarray, Z: np.ndarray, X: np.ndarray, X_lag: np.ndarray) -> float:
    omega = phi - X @ betas
    omega_lag = phi_lag - X_lag @ betas
    omega_lag_pol = np.column_stack([np.ones_like(omega_lag), omega_lag])
    g_b = np.linalg.pinv(omega_lag_pol.T @ omega_lag_pol) @ omega_lag_pol.T @ omega
    xi = omega - omega_lag_pol @ g_b
    moment = Z.T @ xi
    return float(moment.T @ moment)


def _estimate_acf_window(df: pd.DataFrame) -> Optional[Dict[str, float]]:
    phi_reg_cols = ["c", "c2", "k", "k2", "ck", "ms2d", "ms4d"]
    year_dummies = pd.get_dummies(df["year"], prefix="year")
    X_phi = pd.concat([df[phi_reg_cols], year_dummies], axis=1)
    X_phi = sm.add_constant(X_phi)
    y_phi = df["y"]
    if y_phi.dropna().shape[0] < len(phi_reg_cols) + 5:
        return None
    phi_model = sm.OLS(y_phi, X_phi, missing="drop").fit()
    df = df.copy()
    df["phi"] = phi_model.fittedvalues
    df["phi_lag"] = df.groupby("id")["phi"].shift(1)

    work = df.dropna(subset=["phi", "phi_lag", "c", "k", "L.c", "L.k", "c_lag", "k_lag"], how="any")
    if work.empty:
        return None

    PHI = work["phi"].to_numpy()
    PHI_LAG = work["phi_lag"].to_numpy()
    X = np.column_stack([np.ones(len(work)), work["c"], work["k"]])
    X_lag = np.column_stack([np.ones(len(work)), work["c_lag"], work["k_lag"]])
    Z = np.column_stack([np.ones(len(work)), work["c_lag"], work["k"]])

    def objective(betas: np.ndarray) -> float:
        return _gmm_objective(betas, PHI, PHI_LAG, Z, X, X_lag)

    res = scipy.optimize.minimize(objective, x0=np.array([0.0, 0.9, 0.1]), method="Nelder-Mead")
    if not res.success:
        return None
    return {"theta_c": res.x[1], "theta_k": res.x[2]}


# --------------------------------------------------------------------------------------
# Main pipeline
# --------------------------------------------------------------------------------------

def estimate_coefficients(include_interest_cogs: bool, drop_missing_sga: bool, drop3254: bool) -> None:
    ensure_directories()
    df = _load_main(include_interest_cogs)
    df["costshare1"] = df["cogs_D"] / (df["cogs_D"] + df["kexp"])
    df["costshare2"] = df["cogs_D"] / (df["cogs_D"] + df["xsga_D"] + df["kexp"])

    if drop_missing_sga:
        df = _drop_missing_sga(df)
    else:
        df = _drop_trim_sga_ratio(df)

    if drop3254:
        df = df[df["ind4d"] != 3254]

    df = _prep_common_columns(df)
    df = _market_shares(df)
    df = df.rename(columns={"L.c": "c_lag", "L.k": "k_lag"})

    window_results: List[Dict[str, float]] = []
    years = sorted(df["year"].unique())
    sectors = sorted(df["nrind2"].dropna().unique())

    for sector in sectors:
        sector_df = df[df["nrind2"] == sector]
        for year in years:
            mask = (sector_df["year"] >= year - 2) & (sector_df["year"] <= year + 2)
            window_df = sector_df[mask]
            spec1, spec2 = _estimate_window(window_df)
            if spec1 or spec2:
                window_results.append(
                    {
                        "ind2d": sector,
                        "year": year,
                        "theta_WI1_ct": spec1.get("c", np.nan) if spec1 else np.nan,
                        "theta_WI1_kt": spec1.get("k", np.nan) if spec1 else np.nan,
                        "theta_WI2_ct": spec2.get("c", np.nan) if spec2 else np.nan,
                        "theta_WI2_xt": spec2.get("lsga", np.nan) if spec2 else np.nan,
                        "theta_WI2_kt": spec2.get("k", np.nan) if spec2 else np.nan,
                    }
                )

    theta_w_df = pd.DataFrame(window_results).dropna(subset=["theta_WI1_ct", "theta_WI2_ct"], how="all")

    cs_records = []
    for level, col in ((2, "ind2d"), (3, "ind3d"), (4, "ind4d")):
        grouped = df.groupby([col, "year"])["costshare1"].median().reset_index()
        grouped = grouped.rename(columns={col: f"ind{level}d", "costshare1": f"cs{level}d"})
        cs_records.append(grouped)
    theta_c_df = cs_records[0].merge(cs_records[1], left_on=["ind2d", "year"], right_on=["ind3d", "year"], how="left")
    theta_c_df = theta_c_df.merge(cs_records[2], left_on=["ind2d", "year"], right_on=["ind4d", "year"], how="left")
    theta_c_df = theta_c_df[["ind2d", "cs2d", "cs3d", "cs4d", "year"]]

    acf_records = []
    for sector in sectors:
        sector_df = df[df["nrind2"] == sector]
        for year in years:
            mask = (sector_df["year"] >= year - 2) & (sector_df["year"] <= year + 2)
            window_df = sector_df[mask]
            acf_res = _estimate_acf_window(window_df)
            if acf_res:
                acf_records.append({"ind2d": sector, "year": year, "theta_acf": acf_res["theta_c"]})
    theta_acf_df = pd.DataFrame(acf_records)

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

    write_dta(theta_w_df, INTERMEDIATE_DIR / f"theta_W_s_window{suffix}.dta")
    write_dta(theta_c_df, INTERMEDIATE_DIR / f"theta_c{suffix}.dta")
    write_dta(theta_acf_df, INTERMEDIATE_DIR / f"theta_acf{suffix}.dta")
    LOGGER.info("Saved theta outputs with suffix %s", suffix)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replicate Estimate_Coefficients.do in Python.")
    parser.add_argument("--include-interest-cogs", type=int, default=0, choices=[0, 1])
    parser.add_argument("--drop-missing-sga", type=int, default=0, choices=[0, 1])
    parser.add_argument("--drop3254", type=int, default=0, choices=[0, 1])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    estimate_coefficients(bool(args.include_interest_cogs), bool(args.drop_missing_sga), bool(args.drop3254))


if __name__ == "__main__":
    main()
