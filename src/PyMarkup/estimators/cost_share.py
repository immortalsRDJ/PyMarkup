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
    assuming constant returns to scale and perfect competition in input markets.

    The output elasticity is:
        theta_c = cost_share = COGS / (COGS + K_expense)

    Note: Following the original Stata code (Estimate_Coefficients.do),
    the output cost share always uses the formula WITHOUT SG&A (costshare1),
    regardless of the include_sga parameter. The include_sga parameter is
    retained for API compatibility but does not affect the output.

    Parameters
    ----------
    include_sga : bool
        Retained for API compatibility. Does not affect output formula.
        (default: False)
    aggregation : {"median", "mean", "weighted_mean"}
        How to aggregate cost shares within industry-year
    industry_level : int
        NAICS digit level for industry grouping (2, 3, or 4)

    Attributes
    ----------
    results_ : pd.DataFrame
        Estimation results after calling estimate_elasticities()

    Examples
    --------
    >>> estimator = CostShareEstimator(include_sga=False, aggregation="median")
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
