"""Markup calculation from production function elasticities.

This module computes firm-level markups from estimated output elasticities
using the formula: markup = theta / cost_share
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def compute_markups(
    elasticities: pd.DataFrame,
    panel_data: pd.DataFrame,
    cost_share_type: str = "cogs_only",
) -> pd.DataFrame:
    """
    Compute firm-level markups from output elasticities.

    The markup is computed as:
        markup = theta_c / cost_share

    where cost_share = COGS / (COGS + K_expense) or
          cost_share = COGS / (COGS + SG&A + K_expense)

    Parameters
    ----------
    elasticities : pd.DataFrame
        Elasticity estimates with columns: ind2d, year, theta_c
    panel_data : pd.DataFrame
        Firm-level panel with columns: gvkey, year, ind2d, cogs_D, xsga_D, kexp
    cost_share_type : str
        Type of cost share calculation:
        - "cogs_only": COGS / (COGS + K_expense)
        - "with_sga": COGS / (COGS + SG&A + K_expense)

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: gvkey, year, ind2d, markup, theta_c, cost_share
    """
    # Compute cost shares
    df = panel_data.copy()

    if cost_share_type == "cogs_only":
        df["cost_share"] = df["cogs_D"] / (df["cogs_D"] + df["kexp"])
    elif cost_share_type == "with_sga":
        df["cost_share"] = df["cogs_D"] / (df["cogs_D"] + df["xsga_D"] + df["kexp"])
    else:
        raise ValueError(f"Unknown cost_share_type: {cost_share_type}")

    # Merge elasticities
    df = df.merge(elasticities[["ind2d", "year", "theta_c"]], on=["ind2d", "year"], how="left")

    # Compute markup
    df["markup"] = df["theta_c"] / df["cost_share"]

    # Select output columns
    output_cols = ["gvkey", "year", "ind2d", "markup", "theta_c", "cost_share"]
    return df[output_cols].copy()


def aggregate_markups(
    firm_markups: pd.DataFrame,
    by: str | list[str] = "year",
    method: str = "median",
    weights: pd.Series | None = None,
) -> pd.DataFrame:
    """
    Aggregate firm-level markups to industry or time level.

    Parameters
    ----------
    firm_markups : pd.DataFrame
        Firm-level markups from compute_markups()
    by : str or list[str]
        Grouping variable(s): 'year', 'ind2d', or ['ind2d', 'year']
    method : str
        Aggregation method: 'median', 'mean', or 'weighted_mean'
    weights : pd.Series, optional
        Weights for weighted_mean (e.g., sales or employment)

    Returns
    -------
    pd.DataFrame
        Aggregated markups
    """
    if isinstance(by, str):
        by = [by]

    if method == "median":
        agg = firm_markups.groupby(by)["markup"].median().reset_index()
    elif method == "mean":
        agg = firm_markups.groupby(by)["markup"].mean().reset_index()
    elif method == "weighted_mean":
        if weights is None:
            raise ValueError("weights must be provided for weighted_mean")
        # TODO: Implement weighted mean aggregation
        raise NotImplementedError("Weighted mean not yet implemented")
    else:
        raise ValueError(f"Unknown aggregation method: {method}")

    return agg
