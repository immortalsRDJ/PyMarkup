"""
Self-contained Python replacement for ``0.3 theta_estimation.do``.

Includes the Create_Data and Estimate_Coefficients logic inline so nothing
else needs to be imported. It builds the trimmed Compustat panel, estimates
production-function elasticities, and writes theta outputs to Intermediate/.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
import pandas as pd
import scipy.optimize
import statsmodels.api as sm
from linearmodels.iv import IV2SLS

from path_plot_config import data_dir, int_dir

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
# Create Data
# --------------------------------------------------------------------------------------

def _prep_industry_codes(df: pd.DataFrame) -> pd.DataFrame:
    for digits in (2, 3, 4):
        col = f"ind{digits}d"
        df[col] = pd.to_numeric(df["naics"].str.slice(0, digits), errors="coerce")
    return df


def _trim_sale_cogs_ratio(df: pd.DataFrame) -> pd.DataFrame:
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


def create_data(
    include_interest_cogs: bool,
    compustat_path: Optional[Path] = None,
    macro_path: Optional[Path] = None,
) -> Path:
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
    # Group codes mirroring Stata's egen group(ind2d)
    df["nrind2"] = df["ind2d"].astype("category").cat.codes + 1
    df["nrind3"] = df["ind3d"].astype("category").cat.codes + 1
    df["nrind4"] = df["ind4d"].astype("category").cat.codes + 1

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
    # Market shares for OP/ACF
    df["totsales2d"] = df.groupby(["ind2d", "year"])["sale_D"].transform("sum")
    df["totsales3d"] = df.groupby(["ind3d", "year"])["sale_D"].transform("sum")
    df["totsales4d"] = df.groupby(["ind4d", "year"])["sale_D"].transform("sum")
    df["ms2d"] = df["sale_D"] / df["totsales2d"]
    df["ms3d"] = df["sale_D"] / df["totsales3d"]
    df["ms4d"] = df["sale_D"] / df["totsales4d"]

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


# --------------------------------------------------------------------------------------
# Estimate Coefficients
# --------------------------------------------------------------------------------------

def load_main_data(data_root: Path, include_interest_cogs: bool) -> pd.DataFrame:
    fname = "data_main_upd_trim_1_intExp.dta" if include_interest_cogs else "data_main_upd_trim_1.dta"
    path = data_root / "Intermediate" / fname
    LOGGER.info("Loading %s", path)
    return pd.read_stata(path)


def add_lags(df: pd.DataFrame, group: str, time: str, cols: Iterable[str]) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values([group, time])
    for col in cols:
        df[f"L.{col}"] = df.groupby(group)[col].shift(1)
    return df


def safe_log(series: pd.Series) -> pd.Series:
    return np.where(series > 0, np.log(series), np.nan)


def run_iv(df: pd.DataFrame, dep: str, endog: str, exog: Iterable[str], instruments: Iterable[str]) -> Optional[Dict[str, float]]:
    cols_needed = [dep, endog, *exog, *instruments]
    work = df[cols_needed].dropna()
    if work.shape[0] < 5:
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
    spec1 = run_iv(df, dep="r", endog="c", exog=["k", "L.i", "L.k2", "L.k"], instruments=["L.c"])
    spec2 = run_iv(
        df,
        dep="r",
        endog="c",
        exog=["k", "lsga", "L.i", "L.k2", "L.lsga2", "L.k", "L.lsga"],
        instruments=["L.c"],
    )
    return spec1, spec2


# -------------------------------------------------------------------------------------------------
# OP/ACF estimator helpers
# -------------------------------------------------------------------------------------------------

def _gmm_objective(betas: np.ndarray, phi: np.ndarray, phi_lag: np.ndarray, Z: np.ndarray, X: np.ndarray, X_lag: np.ndarray) -> float:
    omega = phi - X @ betas
    omega_lag = phi_lag - X_lag @ betas
    omega_lag_pol = np.column_stack([np.ones_like(omega_lag), omega_lag])
    g_b = np.linalg.pinv(omega_lag_pol.T @ omega_lag_pol) @ omega_lag_pol.T @ omega
    xi = omega - omega_lag_pol @ g_b
    moment = Z.T @ xi
    return float(moment.T @ moment)


def estimate_acf_window(df: pd.DataFrame) -> Optional[Dict[str, float]]:
    """ACF-style GMM following the BMYReplication implementation."""
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

    work = df.dropna(subset=["phi", "phi_lag", "c", "k", "c_lag", "k_lag"])
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


def preprocess(df: pd.DataFrame, drop_missing_sga: bool, data_root: Path) -> pd.DataFrame:
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
        df = df[(df["s_g2"] >= p1) | df["s_g2"].isna()]
        df = df[(df["s_g2"] <= p99) | df["s_g2"].isna()]
        df = df.drop(columns=["s_g2"])

    df["id"] = df["gvkey"].astype("category").cat.codes
    df = df[df["id"].notna()]

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

    # Convenience lags for OP/ACF routine
    df["c_lag"] = df["L.c"]
    df["k_lag"] = df["L.k"]

    return df


def build_result_frame(df: pd.DataFrame) -> pd.DataFrame:
    res = df[["ind2d", "year"]].drop_duplicates().copy()
    for col in ["theta_WI1_ct", "theta_WI2_ct", "theta_WI2_xt", "theta_WI1_kt", "theta_WI2_kt"]:
        res[col] = np.nan
    return res


def assign_coeffs(res: pd.DataFrame, cond: pd.Series, spec1: Optional[Dict[str, float]], spec2: Optional[Dict[str, float]]) -> None:
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
    res = build_result_frame(df)

    def estimate_for_subset(subset: pd.DataFrame, assign_mask: pd.Series) -> None:
        spec1, spec2 = estimate_window_coeffs(subset)
        if spec1 or spec2:
            assign_coeffs(res, assign_mask, spec1, spec2)

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


def run_acf_windows(df: pd.DataFrame) -> pd.DataFrame:
    """Run ACF estimation on rolling 5-year windows by 2-digit industry."""
    records = []
    sectors = sorted(df["nrind2"].dropna().unique())
    years = sorted(df["year"].dropna().unique())
    for sector in sectors:
        sector_df = df[df["nrind2"] == sector]
        for year in years:
            mask = (sector_df["year"] >= year - 2) & (sector_df["year"] <= year + 2)
            window_df = sector_df[mask]
            acf_res = estimate_acf_window(window_df)
            if acf_res:
                records.append({"ind2d": sector, "year": year, "theta_acf": acf_res["theta_c"]})
    return pd.DataFrame(records)


def theta_suffix(include_interest_cogs: bool, drop_missing_sga: bool) -> str:
    suffix = "DEUSample" if drop_missing_sga else "fullSample"
    if include_interest_cogs:
        suffix += "_intExp"
    return suffix


def save_theta_outputs(res: pd.DataFrame, df: pd.DataFrame, data_root: Path, include_interest_cogs: bool, drop_missing_sga: bool) -> None:
    interm = data_root / "Intermediate"
    interm.mkdir(parents=True, exist_ok=True)
    suffix = theta_suffix(include_interest_cogs, drop_missing_sga)

    out_w = interm / f"theta_W_s_window_{suffix}.dta"
    res.sort_values(["ind2d", "year"]).to_stata(out_w, write_index=False)
    LOGGER.info("Saved %s", out_w)

    cs = df.copy()
    cs["cs2d"] = cs.groupby(["year", "ind2d"])["costshare1"].transform("median")
    cs["cs3d"] = cs.groupby(["year", "ind3d"])["costshare1"].transform("median")
    cs["cs4d"] = cs.groupby(["year", "ind4d"])["costshare1"].transform("median")
    cs_out = cs[["ind2d", "cs2d", "cs3d", "cs4d", "year"]].drop_duplicates().sort_values(["ind2d", "year"])

    out_c = interm / f"theta_c_{suffix}.dta"
    cs_out.to_stata(out_c, write_index=False)
    LOGGER.info("Saved %s", out_c)


def save_theta_acf(acf_df: pd.DataFrame, data_root: Path, include_interest_cogs: bool, drop_missing_sga: bool) -> None:
    if acf_df.empty:
        LOGGER.warning("No ACF estimates were generated; skipping theta_acf output.")
        return
    interm = data_root / "Intermediate"
    interm.mkdir(parents=True, exist_ok=True)
    suffix = theta_suffix(include_interest_cogs, drop_missing_sga)
    out_acf = interm / f"theta_acf_{suffix}.dta"
    acf_df.to_stata(out_acf, write_index=False)
    LOGGER.info("Saved %s", out_acf)


def estimate_coefficients(data_root: Path, include_interest_cogs: bool = False, drop_missing_sga: bool = False) -> None:
    df = load_main_data(data_root, include_interest_cogs=include_interest_cogs)
    df = preprocess(df, drop_missing_sga=drop_missing_sga, data_root=data_root)
    res = run_rolling_windows(df)
    acf_df = run_acf_windows(df)
    save_theta_outputs(
        res=res,
        df=df,
        data_root=data_root,
        include_interest_cogs=include_interest_cogs,
        drop_missing_sga=drop_missing_sga,
    )
    save_theta_acf(
        acf_df=acf_df,
        data_root=data_root,
        include_interest_cogs=include_interest_cogs,
        drop_missing_sga=drop_missing_sga,
    )


# --------------------------------------------------------------------------------------
# CLI glue
# --------------------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Python replacement for 0.3 theta_estimation.do (fully inlined).")
    parser.add_argument("--data-root", type=Path, default=None, help="Project root containing Input/ and Intermediate/.")
    parser.add_argument("--include-interest-cogs", type=int, choices=[0, 1], default=0, help="Match Stata flag includeinterestcogs.")
    parser.add_argument("--drop-missing-sga", type=int, choices=[0, 1], default=0, help="Match Stata flag dropmissingsga.")
    parser.add_argument("--compustat-path", type=Path, default=None, help="Optional override for Compustat_annual.dta")
    parser.add_argument("--macro-path", type=Path, default=None, help="Optional override for macro_vars_new.xlsx")
    return parser.parse_args()


def main(
    data_root: Optional[Path] = None,
    include_interest_cogs: bool = False,
    drop_missing_sga: bool = False,
    compustat_path: Optional[Path] = None,
    macro_path: Optional[Path] = None,
) -> None:
    root = data_root or Path(__file__).resolve().parents[2]

    LOGGER.info("Running Create_Data include_interest_cogs=%s", int(include_interest_cogs))
    create_data(
        include_interest_cogs=include_interest_cogs,
        compustat_path=compustat_path,
        macro_path=macro_path,
    )

    LOGGER.info("Estimating theta coefficients (drop_missing_sga=%s)", int(drop_missing_sga))
    estimate_coefficients(
        data_root=root,
        include_interest_cogs=include_interest_cogs,
        drop_missing_sga=drop_missing_sga,
    )


if __name__ == "__main__":
    args = parse_args()
    main(
        data_root=args.data_root,
        include_interest_cogs=bool(args.include_interest_cogs),
        drop_missing_sga=bool(args.drop_missing_sga),
        compustat_path=args.compustat_path,
        macro_path=args.macro_path,
    )
