"""Wooldridge-style IV/GMM estimator for production function elasticities."""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np
import pandas as pd
from linearmodels.iv import IV2SLS

from PyMarkup.core.data_preparation import add_lags, safe_log
from PyMarkup.estimators.base import ProductionFunctionEstimator

logger = logging.getLogger(__name__)


class WooldridgeIVEstimator(ProductionFunctionEstimator):
    """
    Wooldridge-style IV/GMM estimator using lagged COGS as instrument.

    This estimator addresses simultaneity bias in production function estimation
    by instrumenting current COGS with lagged COGS, following Wooldridge's approach.

    Two specifications are available:
    - spec1: Output ~ COGS + Capital (+ controls)
    - spec2: Output ~ COGS + Capital + SG&A (+ controls)

    Parameters
    ----------
    specification : {"spec1", "spec2", "both"}
        Which specification to estimate:
        - "spec1": COGS + capital only
        - "spec2": COGS + capital + SG&A
        - "both": estimate both, return spec2 results
    window_years : int
        Rolling window size in years (default: 5 = ±2 years)
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
    >>> estimator = WooldridgeIVEstimator(specification="spec2", window_years=5)
    >>> elasticities = estimator.estimate_elasticities(panel_data)
    >>> print(elasticities.head())
    """

    def __init__(
        self,
        specification: Literal["spec1", "spec2", "both"] = "spec2",
        window_years: int = 5,
        industry_level: int = 2,
        min_observations: int = 15,
    ):
        if industry_level not in {2, 3, 4}:
            raise ValueError(f"industry_level must be 2, 3, or 4, got {industry_level}")

        self.specification = specification
        self.window_years = window_years
        self.industry_level = industry_level
        self.min_observations = min_observations
        self.results_ = None

    def get_method_name(self) -> str:
        """Return method name."""
        return f"Wooldridge IV ({self.specification})"

    def _preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data for IV estimation.

        Creates log-transformed variables, polynomials, and lags.
        """
        df = data.copy()

        # Create firm ID if not exists
        if "id" not in df.columns:
            df["id"] = df["gvkey"].astype("category").cat.codes

        # Log-transform main variables
        df["r"] = np.log(df["sale_D"])  # Output (revenue)
        df["y"] = df["r"]
        df["c"] = np.log(df["cogs_D"])  # Variable input
        df["k"] = np.log(df["capital_D"])  # Capital

        # Polynomials
        df["c2"] = df["c"] ** 2
        df["c3"] = df["c"] ** 3
        df["k2"] = df["k"] ** 2
        df["k3"] = df["k"] ** 3
        df["ck"] = df["c"] * df["k"]

        # SG&A (if using spec2)
        df["lsga"] = safe_log(df["xsga_D"])
        df["lsga2"] = df["lsga"] ** 2

        # Capital stock and investment
        df["K"] = np.exp(df["k"])
        df["depr"] = 0.1
        df = add_lags(df, group="id", time="year", cols=["K"])
        df["Inv"] = df["K"] - (1 - df["depr"]) * df["L.K"]
        df["i"] = safe_log(df["Inv"])
        df["i2"] = df["i"] ** 2

        # Lags for instruments and controls
        df = add_lags(df, group="id", time="year", cols=["c", "k", "i", "lsga", "k2", "lsga2"])

        return df

    def _run_iv(
        self,
        df: pd.DataFrame,
        dep: str,
        endog: str,
        exog: list[str],
        instruments: list[str],
    ) -> dict[str, float] | None:
        """
        Run IV/2SLS regression.

        Parameters
        ----------
        df : pd.DataFrame
            Data for estimation
        dep : str
            Dependent variable
        endog : str
            Endogenous variable
        exog : list[str]
            Exogenous variables (controls)
        instruments : list[str]
            Instrumental variables

        Returns
        -------
        dict or None
            Dictionary of coefficients, or None if estimation fails
        """
        cols_needed = [dep, endog, *exog, *instruments]
        work = df[cols_needed].dropna()

        if work.shape[0] < self.min_observations:
            return None

        try:
            model = IV2SLS(
                dependent=work[dep],
                exog=pd.concat([pd.Series(1.0, index=work.index, name="const"), work[exog]], axis=1),
                endog=work[[endog]],
                instruments=work[instruments],
            )
            res = model.fit(cov_type="robust")
            return res.params.to_dict()
        except Exception as exc:
            logger.warning(f"IV estimation failed: {exc}")
            return None

    def _estimate_window(self, df: pd.DataFrame) -> tuple[dict | None, dict | None]:
        """
        Estimate both specifications for a given window.

        Returns
        -------
        tuple
            (spec1_coefficients, spec2_coefficients)
        """
        # Specification 1: COGS + Capital
        spec1 = self._run_iv(
            df,
            dep="r",
            endog="c",
            exog=["k", "L.i", "L.k2", "L.k"],
            instruments=["L.c"],
        )

        # Specification 2: COGS + Capital + SG&A
        spec2 = self._run_iv(
            df,
            dep="r",
            endog="c",
            exog=["k", "lsga", "L.i", "L.k2", "L.lsga2", "L.k", "L.lsga"],
            instruments=["L.c"],
        )

        return spec1, spec2

    def _build_result_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create container for results."""
        ind_col = f"ind{self.industry_level}d"
        ind_num_col = f"nrind{self.industry_level}"

        # Get unique industry-year combinations
        res = df[[ind_col, "year"]].drop_duplicates().copy()

        # Store actual industry code for output (don't rename yet)
        res["ind2d"] = res[ind_col]

        # Initialize coefficient columns
        for col in ["theta_WI1_ct", "theta_WI2_ct", "theta_WI2_xt", "theta_WI1_kt", "theta_WI2_kt"]:
            res[col] = np.nan

        return res

    def _assign_coefficients(
        self,
        res: pd.DataFrame,
        condition: pd.Series,
        spec1: dict | None,
        spec2: dict | None,
    ) -> None:
        """Assign estimated coefficients to result frame."""
        if spec1:
            if "c" in spec1:
                res.loc[condition, "theta_WI1_ct"] = spec1["c"]
            if "k" in spec1:
                res.loc[condition, "theta_WI1_kt"] = spec1["k"]

        if spec2:
            if "c" in spec2:
                res.loc[condition, "theta_WI2_ct"] = spec2["c"]
            if "lsga" in spec2:
                res.loc[condition, "theta_WI2_xt"] = spec2["lsga"]
            if "k" in spec2:
                res.loc[condition, "theta_WI2_kt"] = spec2["k"]

    def _run_rolling_windows(self, df: pd.DataFrame, res: pd.DataFrame) -> None:
        """
        Run rolling window estimation for all industries and years.

        This implements the full logic from the original Stata code, including:
        - Early windows for industries 1-16, 18-25
        - Special handling for industry 17
        - Rolling 5-year windows for all industries from 1970 onwards
        """
        ind_col = f"nrind{self.industry_level}"

        # Helper function to estimate for a subset
        def estimate_for_subset(subset: pd.DataFrame, assign_mask: pd.Series) -> None:
            spec1, spec2 = self._estimate_window(subset)
            if spec1 or spec2:
                self._assign_coefficients(res, assign_mask, spec1, spec2)

        # Early windows: industries 1-16 (before 1970)
        for s in range(1, 17):
            subset = df[
                (df[ind_col] == s) & (df["year"] < 1972) & df[["r", "c", "k", "L.c", "L.i", "L.k"]].notna().all(axis=1)
            ]
            if subset.shape[0] > self.min_observations:
                mask = (res["ind2d"] == s) & (res["year"] < 1970)
                estimate_for_subset(subset, mask)

        # Early windows: industries 18-25 (before 1970)
        for s in range(18, 26):
            subset = df[
                (df[ind_col] == s) & (df["year"] < 1972) & df[["r", "c", "k", "L.c", "L.i", "L.k"]].notna().all(axis=1)
            ]
            if subset.shape[0] > self.min_observations:
                mask = (res["ind2d"] == s) & (res["year"] < 1970)
                estimate_for_subset(subset, mask)

        # Special industry 17 (before 1985)
        subset_17 = df[
            (df[ind_col] == 17) & (df["year"] < 1985) & df[["r", "c", "k", "L.c", "L.i", "L.k"]].notna().all(axis=1)
        ]
        if subset_17.shape[0] > self.min_observations:
            mask = (res["ind2d"] == 17) & (res["year"] < 1985)
            estimate_for_subset(subset_17, mask)

        # Rolling windows from 1970 onwards
        window_half = self.window_years // 2

        for t in range(1970, 2025):
            window_mask = (df["year"] >= t - window_half) & (df["year"] <= t + window_half)

            # Industries 1-16
            for s in range(1, 17):
                subset = df[
                    (df[ind_col] == s)
                    & window_mask
                    & df[["r", "c", "k", "L.c", "L.i", "L.k"]].notna().all(axis=1)
                ]
                if subset.shape[0] > self.min_observations:
                    mask = (res["ind2d"] == s) & (res["year"] == t)
                    estimate_for_subset(subset, mask)

            # Industries 18-25
            for s in range(18, 26):
                subset = df[
                    (df[ind_col] == s)
                    & window_mask
                    & df[["r", "c", "k", "L.c", "L.i", "L.k"]].notna().all(axis=1)
                ]
                if subset.shape[0] > self.min_observations:
                    mask = (res["ind2d"] == s) & (res["year"] == t)
                    estimate_for_subset(subset, mask)

            # Industry 17 (from 1985 onwards)
            if t >= 1985:
                subset = df[
                    (df[ind_col] == 17)
                    & window_mask
                    & df[["r", "c", "k", "L.c", "L.i", "L.k"]].notna().all(axis=1)
                ]
                if subset.shape[0] > self.min_observations:
                    mask = (res["ind2d"] == 17) & (res["year"] == t)
                    estimate_for_subset(subset, mask)

    def estimate_elasticities(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Estimate output elasticities using rolling windows by industry.

        Parameters
        ----------
        data : pd.DataFrame
            Prepared panel data with required columns:
            - gvkey, year, sale_D, cogs_D, capital_D, xsga_D (optional)
            - ind2d, nrind2 (or ind3d/nrind3, ind4d/nrind4)

        Returns
        -------
        pd.DataFrame
            Elasticity estimates with columns:
            - ind2d: industry code
            - year: fiscal year
            - theta_c: COGS elasticity (from chosen specification)
            - theta_k: capital elasticity
        """
        logger.info(f"Starting {self.get_method_name()} estimation")
        logger.info(f"Window size: {self.window_years} years, Industry level: {self.industry_level}-digit NAICS")

        # Preprocess data
        df = self._preprocess(data)

        # Build result container
        res = self._build_result_frame(df)

        # Run rolling window estimation
        logger.info("Running rolling window IV estimation...")
        self._run_rolling_windows(df, res)

        # Count successful estimates
        n_estimates = res["theta_WI1_ct"].notna().sum() if self.specification == "spec1" else res["theta_WI2_ct"].notna().sum()
        logger.info(f"Successfully estimated {n_estimates} industry-year elasticities")

        # Select output columns based on specification
        if self.specification == "spec1":
            res["theta_c"] = res["theta_WI1_ct"]
            res["theta_k"] = res["theta_WI1_kt"]
        elif self.specification == "spec2":
            res["theta_c"] = res["theta_WI2_ct"]
            res["theta_k"] = res["theta_WI2_kt"]
        else:  # both
            # Return spec2 by default (more controls)
            res["theta_c"] = res["theta_WI2_ct"]
            res["theta_k"] = res["theta_WI2_kt"]

        # Clean output
        output = res[["ind2d", "year", "theta_c", "theta_k"]].copy()
        output = output.dropna(subset=["theta_c"])  # Drop rows with no estimates

        self.results_ = output
        return output
