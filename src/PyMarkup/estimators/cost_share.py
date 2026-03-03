"""Cost share estimator (accounting approach)."""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np
import pandas as pd

from PyMarkup.estimators.base import ProductionFunctionEstimator

logger = logging.getLogger(__name__)


class CostShareEstimator(ProductionFunctionEstimator):
    """
    Direct cost share estimator (accounting approach).

    This estimator computes output elasticities directly from cost shares,
    assuming constant returns to scale (CRS) and perfect competition in input markets.

    Under CRS, the firm-level markup can be computed directly as:
        markup = Revenue / (COGS + K_expense)

    This follows from:
        theta_c = COGS / (COGS + K)
        markup = theta_c / cost_share = theta_c / (COGS / Revenue)
               = [COGS / (COGS + K)] * [Revenue / COGS]
               = Revenue / (COGS + K)

    The preferred method is `compute_firm_markups()` which directly computes
    firm-level markups without unnecessary industry-year aggregation.

    Parameters
    ----------
    include_sga : bool
        If True, include SG&A in total costs: markup = Revenue / (COGS + SG&A + K)
        (default: False)
    aggregation : {"median", "mean", "weighted_mean"}
        How to aggregate cost shares within industry-year (for backward compatibility)
    industry_level : int
        NAICS digit level for industry grouping (2, 3, or 4)

    Attributes
    ----------
    results_ : pd.DataFrame
        Estimation results after calling estimate_elasticities()

    Examples
    --------
    >>> estimator = CostShareEstimator(include_sga=False)
    >>> # Preferred: direct firm-level markup computation
    >>> firm_markups = estimator.compute_firm_markups(panel_data)
    >>> # Legacy: industry-year aggregated elasticities
    >>> elasticities = estimator.estimate_elasticities(panel_data)
    """

    def __init__(
        self,
        include_sga: bool = False,
        aggregation: Literal["median", "mean", "weighted_mean"] = "median",
        industry_level: int = 2,
    ):
        if industry_level not in {2, 3, 4}:
            raise ValueError(f"industry_level must be 2, 3, or 4, got {industry_level}")

        self.include_sga = include_sga
        self.aggregation = aggregation
        self.industry_level = industry_level
        self.results_ = None

    def get_method_name(self) -> str:
        """Return method name."""
        return f"Cost Share (COGS only, {self.aggregation})"

    def estimate_elasticities(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Estimate output elasticities from cost shares.

        Parameters
        ----------
        data : pd.DataFrame
            Panel data with required columns:
            - gvkey, year: firm and time identifiers
            - ind2d/ind3d/ind4d: industry code (based on industry_level)
            - cogs_D: deflated COGS
            - kexp: capital expense (usercost * capital_D)
            - xsga_D: deflated SG&A (required if include_sga=True)
            - sale_D: deflated sales (required if aggregation='weighted_mean')

        Returns
        -------
        pd.DataFrame
            Elasticity estimates with columns:
            - ind2d: industry code
            - year: fiscal year
            - theta_c: COGS cost share (output elasticity)
        """
        logger.info(f"Starting {self.get_method_name()} estimation")

        df = data.copy()
        ind_col = f"ind{self.industry_level}d"

        # Validate required columns
        required_cols = [ind_col, "year", "cogs_D", "kexp"]
        if self.include_sga:
            required_cols.append("xsga_D")
        if self.aggregation == "weighted_mean":
            required_cols.append("sale_D")

        missing_cols = set(required_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Compute firm-level cost shares
        # Note: Following Stata code, the OUTPUT cost share always uses costshare1
        # (without SG&A). The include_sga flag only affects trimming behavior.
        # See Estimate_Coefficients.do lines 214-217:
        #   bysort year ind2d: egen cs2d = median(costshare1)
        df["costshare"] = df["cogs_D"] / (df["cogs_D"] + df["kexp"])

        # Remove invalid cost shares
        df = df[df["costshare"].notna() & (df["costshare"] > 0) & (df["costshare"] < 1)]

        # Aggregate by industry-year
        if self.aggregation == "median":
            agg = df.groupby([ind_col, "year"])["costshare"].median().reset_index()
        elif self.aggregation == "mean":
            agg = df.groupby([ind_col, "year"])["costshare"].mean().reset_index()
        elif self.aggregation == "weighted_mean":
            # Weight by sales

            def weighted_avg(group):
                weights = group["sale_D"]
                if weights.sum() == 0:
                    return np.nan
                return np.average(group["costshare"], weights=weights)

            agg = df.groupby([ind_col, "year"]).apply(weighted_avg, include_groups=False).reset_index()
            agg.columns = [ind_col, "year", "costshare"]
        else:
            raise ValueError(f"Unknown aggregation method: {self.aggregation}")

        # Rename to standard output format
        agg = agg.rename(columns={ind_col: "ind2d", "costshare": "theta_c"})

        # Remove NaN values
        agg = agg.dropna(subset=["theta_c"])

        self.results_ = agg
        logger.info(f"Estimated cost shares for {len(agg)} industry-years")
        logger.info(f"Mean cost share: {agg['theta_c'].mean():.3f}, Median: {agg['theta_c'].median():.3f}")

        return agg[["ind2d", "year", "theta_c"]].copy()

    def _get_output_filename(self, suffix: str, format: str) -> str:
        """Get output filename matching original convention."""
        suffix_part = f"_{suffix}" if suffix else ""
        return f"theta_c{suffix_part}.{format}"

    def compute_firm_markups(
        self,
        data: pd.DataFrame,
        apply_trim: bool = True,
        min_year: int = 1955,
        exclude_ind2d: int | list[int] | None = 99,
    ) -> pd.DataFrame:
        """
        Compute firm-level markups directly under CRS assumption.

        Under constant returns to scale, the markup simplifies to:
            markup = Revenue / (COGS + K)

        If include_sga=True:
            markup = Revenue / (COGS + SG&A + K)

        This is more efficient and accurate than aggregating theta to
        industry-year and then applying back to individual firms.

        Parameters
        ----------
        data : pd.DataFrame
            Panel data with required columns:
            - gvkey, year: firm and time identifiers
            - ind2d: 2-digit industry code
            - sale_D: deflated sales (revenue)
            - cogs_D: deflated COGS
            - kexp: capital expense (usercost * capital_D)
            - xsga_D: deflated SG&A (required if include_sga=True)
        apply_trim : bool
            If True, apply cost share trimming (p1-p99) before computing markups.
            Default: True
        min_year : int
            Minimum year to include (default: 1955)
        exclude_ind2d : int or list[int] or None
            Industry codes to exclude (default: 99)

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: gvkey, year, ind2d, markup, theta_c, cost_share
        """
        logger.info(f"Computing firm-level markups directly (CRS assumption)")

        df = data.copy()
        ind_col = f"ind{self.industry_level}d"

        # Validate required columns
        required_cols = ["gvkey", "year", ind_col, "sale_D", "cogs_D", "kexp"]
        if self.include_sga:
            required_cols.append("xsga_D")

        missing_cols = set(required_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Apply cost share trimming (matching legacy behavior)
        if apply_trim:
            n_before = len(df)
            df = self._apply_costshare_trim(df)
            n_after = len(df)
            logger.info(f"Cost share trimming: {n_before} -> {n_after} observations")

        # Apply year filter
        if min_year is not None:
            df = df[df["year"] >= min_year]

        # Apply industry filter
        if exclude_ind2d is not None:
            if isinstance(exclude_ind2d, int):
                exclude_ind2d = [exclude_ind2d]
            df = df[~df[ind_col].isin(exclude_ind2d)]

        # Compute total cost
        if self.include_sga:
            # Fill missing SG&A with 0 for this calculation
            xsga = df["xsga_D"].fillna(0)
            df["total_cost"] = df["cogs_D"] + xsga + df["kexp"]
        else:
            df["total_cost"] = df["cogs_D"] + df["kexp"]

        # Filter invalid observations
        df = df[df["total_cost"] > 0]
        df = df[df["sale_D"] > 0]

        # Compute markup directly: mu = Revenue / Total_Cost
        df["markup"] = df["sale_D"] / df["total_cost"]

        # Also compute theta_c and cost_share for compatibility
        df["theta_c"] = df["cogs_D"] / df["total_cost"]
        df["cost_share"] = df["cogs_D"] / df["sale_D"]

        # Remove extreme outliers
        df = df[df["markup"] > 0]
        df = df[df["markup"] < 50]

        logger.info(f"Computed markups for {len(df)} firm-years")
        logger.info(f"Mean markup: {df['markup'].mean():.3f}, Median: {df['markup'].median():.3f}")

        # Output columns (rename ind_col to ind2d for consistency)
        df = df.rename(columns={ind_col: "ind2d"}) if ind_col != "ind2d" else df
        output_cols = ["gvkey", "year", "ind2d", "markup", "theta_c", "cost_share"]

        return df[output_cols].copy()

    def _apply_costshare_trim(self, df: pd.DataFrame, time_col: str = "year") -> pd.DataFrame:
        """
        Trim observations based on cost share percentiles.

        Parameters
        ----------
        df : pd.DataFrame
            Panel data with cogs_D, kexp, xsga_D columns
        time_col : str
            Time column for grouping (default: "year")

        Returns
        -------
        pd.DataFrame
            Trimmed DataFrame
        """
        df = df.copy()

        # Create cost share variables
        df["_costshare1"] = df["cogs_D"] / (df["cogs_D"] + df["kexp"])
        if "xsga_D" in df.columns:
            xsga = df["xsga_D"].fillna(0)
            df["_costshare2"] = df["cogs_D"] / (df["cogs_D"] + xsga + df["kexp"])
        else:
            df["_costshare2"] = df["_costshare1"]

        # Trim on both cost shares sequentially (p1-p99 by time period)
        for col in ("_costshare1", "_costshare2"):
            p1 = df.groupby(time_col)[col].transform(lambda x: x.quantile(0.01))
            p99 = df.groupby(time_col)[col].transform(lambda x: x.quantile(0.99))
            mask = (
                (df[col] > 0)
                & df[col].notna()
                & (df[col] > p1)
                & (df[col] < p99)
            )
            df = df[mask]

        # Drop temporary columns
        df = df.drop(columns=["_costshare1", "_costshare2"], errors="ignore")

        return df
