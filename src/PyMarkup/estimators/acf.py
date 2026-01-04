"""Ackerberg-Caves-Frazer (ACF) GMM estimator."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import scipy.optimize
import statsmodels.api as sm

from PyMarkup.core.data_preparation import add_lags, safe_log
from PyMarkup.estimators.base import ProductionFunctionEstimator

logger = logging.getLogger(__name__)


class ACFEstimator(ProductionFunctionEstimator):
    """
    Ackerberg-Caves-Frazer (2015) two-stage GMM estimator.

    This estimator addresses simultaneity and selection bias using timing
    assumptions about input choices. It uses a control function approach
    with GMM to recover production function parameters.

    The estimation proceeds in two stages:
    1. Estimate productivity proxy (phi) via OLS regression
    2. Recover structural parameters via GMM minimization

    Parameters
    ----------
    window_years : int
        Rolling window size in years (default: 5 = ±2 years)
    include_market_share : bool
        Include market share controls in first stage (default: True)
    industry_level : int
        NAICS digit level for industry grouping (2, 3, or 4)
    min_observations : int
        Minimum observations required per window (default: 15)

    Attributes
    ----------
    results_ : pd.DataFrame
        Estimation results after calling estimate_elasticities()

    Examples
    --------
    >>> estimator = ACFEstimator(window_years=5, include_market_share=True)
    >>> elasticities = estimator.estimate_elasticities(panel_data)

    References
    ----------
    Ackerberg, D. A., Caves, K., & Frazer, G. (2015). Identification properties
    of recent production function estimators. Econometrica, 83(6), 2411-2451.
    """

    def __init__(
        self,
        window_years: int = 5,
        include_market_share: bool = True,
        industry_level: int = 2,
        min_observations: int = 15,
    ):
        if industry_level not in {2, 3, 4}:
            raise ValueError(f"industry_level must be 2, 3, or 4, got {industry_level}")

        self.window_years = window_years
        self.include_market_share = include_market_share
        self.industry_level = industry_level
        self.min_observations = min_observations
        self.results_ = None

    def get_method_name(self) -> str:
        """Return method name."""
        return "ACF (Ackerberg-Caves-Frazer)"

    def _preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for ACF estimation."""
        df = data.copy()

        # Create firm ID if not exists
        if "id" not in df.columns:
            df["id"] = df["gvkey"].astype("category").cat.codes

        # Log-transform variables
        df["y"] = np.log(df["sale_D"])
        df["c"] = np.log(df["cogs_D"])
        df["k"] = np.log(df["capital_D"])

        # Polynomials
        df["c2"] = df["c"] ** 2
        df["k2"] = df["k"] ** 2
        df["ck"] = df["c"] * df["k"]

        # Lags
        df = add_lags(df, group="id", time="year", cols=["c", "k"])
        df["c_lag"] = df["L.c"]
        df["k_lag"] = df["L.k"]

        return df

    def _gmm_objective(
        self,
        betas: np.ndarray,
        phi: np.ndarray,
        phi_lag: np.ndarray,
        Z: np.ndarray,
        X: np.ndarray,
        X_lag: np.ndarray,
    ) -> float:
        """
        GMM objective function for second stage.

        Parameters
        ----------
        betas : np.ndarray
            Parameter vector [intercept, beta_c, beta_k]
        phi : np.ndarray
            Productivity proxy (current period)
        phi_lag : np.ndarray
            Lagged productivity proxy
        Z : np.ndarray
            Instruments
        X : np.ndarray
            Covariates (current period)
        X_lag : np.ndarray
            Lagged covariates

        Returns
        -------
        float
            GMM objective value
        """
        # Compute productivity shocks (omega)
        omega = phi - X @ betas
        omega_lag = phi_lag - X_lag @ betas

        # First-stage: regress omega on omega_lag polynomial
        omega_lag_pol = np.column_stack([np.ones_like(omega_lag), omega_lag])
        g_b = np.linalg.pinv(omega_lag_pol.T @ omega_lag_pol) @ omega_lag_pol.T @ omega

        # Innovation (xi)
        xi = omega - omega_lag_pol @ g_b

        # Moment conditions
        moment = Z.T @ xi

        return float(moment.T @ moment)

    def _estimate_window(self, df: pd.DataFrame) -> dict[str, float] | None:
        """
        Estimate ACF for a single window.

        Returns
        -------
        dict or None
            Dictionary with keys: theta_c, theta_k
        """
        # First stage: estimate productivity proxy (phi)
        phi_reg_cols = ["c", "c2", "k", "k2", "ck"]

        if self.include_market_share:
            phi_reg_cols.extend(["ms2d", "ms4d"])

        # Add year dummies
        year_dummies = pd.get_dummies(df["year"], prefix="year", drop_first=False)
        X_phi = pd.concat([df[phi_reg_cols], year_dummies], axis=1)
        X_phi = sm.add_constant(X_phi)
        y_phi = df["y"]

        # Check sufficient observations
        if y_phi.dropna().shape[0] < len(phi_reg_cols) + 5:
            return None

        # OLS for first stage
        try:
            phi_model = sm.OLS(y_phi, X_phi, missing="drop").fit()
        except Exception as exc:
            logger.warning(f"First-stage OLS failed: {exc}")
            return None

        df = df.copy()
        df["phi"] = phi_model.fittedvalues
        df["phi_lag"] = df.groupby("id")["phi"].shift(1)

        # Prepare data for GMM second stage
        work = df.dropna(subset=["phi", "phi_lag", "c", "k", "c_lag", "k_lag"])
        if work.empty or len(work) < self.min_observations:
            return None

        PHI = work["phi"].to_numpy()
        PHI_LAG = work["phi_lag"].to_numpy()
        X = np.column_stack([np.ones(len(work)), work["c"], work["k"]])
        X_lag = np.column_stack([np.ones(len(work)), work["c_lag"], work["k_lag"]])
        Z = np.column_stack([np.ones(len(work)), work["c_lag"], work["k"]])

        # GMM optimization
        def objective(betas: np.ndarray) -> float:
            return self._gmm_objective(betas, PHI, PHI_LAG, Z, X, X_lag)

        try:
            res = scipy.optimize.minimize(objective, x0=np.array([0.0, 0.9, 0.1]), method="Nelder-Mead")
            if not res.success:
                return None
            return {"theta_c": res.x[1], "theta_k": res.x[2]}
        except Exception as exc:
            logger.warning(f"GMM optimization failed: {exc}")
            return None

    def estimate_elasticities(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Estimate output elasticities using ACF on rolling windows.

        Parameters
        ----------
        data : pd.DataFrame
            Prepared panel data with required columns:
            - gvkey, year, sale_D, cogs_D, capital_D
            - ind2d, nrind2 (or ind3d/nrind3, ind4d/nrind4)
            - ms2d, ms4d (market shares, optional if include_market_share=False)

        Returns
        -------
        pd.DataFrame
            Elasticity estimates with columns:
            - ind2d: industry code
            - year: fiscal year
            - theta_c: COGS elasticity
            - theta_k: capital elasticity
        """
        logger.info(f"Starting {self.get_method_name()} estimation")
        logger.info(f"Window size: {self.window_years} years, Market share controls: {self.include_market_share}")

        # Preprocess
        df = self._preprocess(data)

        # Industry columns
        ind_col = f"ind{self.industry_level}d"
        ind_num_col = f"nrind{self.industry_level}"

        # Create industry numeric codes if not exists
        if ind_num_col not in df.columns:
            df[ind_num_col] = df[ind_col].astype("category").cat.codes + 1

        # Run rolling windows
        records = []
        sectors = sorted(df[ind_num_col].dropna().unique())
        years = sorted(df["year"].dropna().unique())

        logger.info(f"Estimating for {len(sectors)} industries across {len(years)} years")

        for sector in sectors:
            sector_df = df[df[ind_num_col] == sector]

            # Get actual industry code for this sector
            ind_code = sector_df[ind_col].iloc[0] if len(sector_df) > 0 else sector

            for year in years:
                # Define window
                window_half = self.window_years // 2
                mask = (sector_df["year"] >= year - window_half) & (sector_df["year"] <= year + window_half)
                window_df = sector_df[mask]

                if len(window_df) < self.min_observations:
                    continue

                # Estimate
                acf_res = self._estimate_window(window_df)
                if acf_res:
                    records.append(
                        {
                            "ind2d": ind_code,
                            "year": year,
                            "theta_c": acf_res["theta_c"],
                            "theta_k": acf_res.get("theta_k"),
                        }
                    )

        result = pd.DataFrame(records)
        self.results_ = result

        logger.info(f"Successfully estimated ACF elasticities for {len(result)} industry-years")
        return result
