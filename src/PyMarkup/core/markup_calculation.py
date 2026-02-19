"""Markup calculation from production function elasticities.

This module computes firm-level markups from estimated output elasticities
using the formula: markup = theta / cost_share
"""

from __future__ import annotations

import logging

import numpy as np
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
    weight_type: str | None = None,
    panel_data: pd.DataFrame | None = None,
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
        Custom weights for weighted_mean. If provided, overrides weight_type.
    weight_type : str, optional
        Built-in weight type for weighted_mean:
        - "revenue": firm revenue share (sale_D / total_sale_D)
        - "cost": firm cost share (cogs_D / total_cogs_D)
        Requires panel_data if used.
    panel_data : pd.DataFrame, optional
        Panel data with sale_D and cogs_D columns. Required if weight_type is used.

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
        df = firm_markups.copy()

        # Compute weights based on weight_type if no custom weights provided
        if weights is not None:
            df["_w"] = weights
        elif weight_type is not None:
            if panel_data is None:
                raise ValueError("panel_data must be provided when using weight_type")

            # Merge panel data to get sale_D and cogs_D
            merge_cols = ["gvkey", "year"]
            if weight_type == "revenue":
                df = df.merge(panel_data[merge_cols + ["sale_D"]], on=merge_cols, how="left")
                df["_total"] = df.groupby(by)["sale_D"].transform("sum")
                df["_w"] = df["sale_D"] / df["_total"]
            elif weight_type == "cost":
                df = df.merge(panel_data[merge_cols + ["cogs_D"]], on=merge_cols, how="left")
                df["_total"] = df.groupby(by)["cogs_D"].transform("sum")
                df["_w"] = df["cogs_D"] / df["_total"]
            else:
                raise ValueError(f"Unknown weight_type: {weight_type}. Use 'revenue' or 'cost'.")
        else:
            raise ValueError("Either weights or weight_type must be provided for weighted_mean")

        agg = df.groupby(by).apply(
            lambda g: np.average(g["markup"].fillna(0), weights=g["_w"]),
            include_groups=False,
        ).reset_index(name="markup")
    else:
        raise ValueError(f"Unknown aggregation method: {method}")

    return agg
