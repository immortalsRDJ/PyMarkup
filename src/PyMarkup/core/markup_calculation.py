"""Markup calculation from production function elasticities.

This module computes firm-level markups from estimated output elasticities
using the formula: markup = theta / cost_share
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _apply_costshare_trim(df: pd.DataFrame, time_col: str = "year") -> pd.DataFrame:
    """
    Trim observations based on cost share percentiles.

    This matches the legacy 0.4 Create Main Datasets.py trimming logic,
    which trims on both costshare1 and costshare2 (p1-p99 by time period).

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

    # Create cost share variables (matching legacy logic)
    df["costshare1"] = df["cogs_D"] / (df["cogs_D"] + df["kexp"])
    df["costshare2"] = df["cogs_D"] / (df["cogs_D"] + df["xsga_D"] + df["kexp"])

    # Trim on both cost shares sequentially (p1-p99 by time period)
    for col in ("costshare1", "costshare2"):
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
    df = df.drop(columns=["costshare1", "costshare2"], errors="ignore")

    return df


def compute_markups(
    elasticities: pd.DataFrame,
    panel_data: pd.DataFrame,
    apply_costshare_trim: bool = True,
    min_year: int = 1955,
    exclude_ind2d: int | list[int] | None = 99,
    time_col: str = "year",
) -> pd.DataFrame:
    """
    Compute firm-level markups from output elasticities.

    The markup is computed using the De Loecker & Warzynski formula:
        markup = theta_c / cost_share
        where cost_share = COGS / Revenue

    Parameters
    ----------
    elasticities : pd.DataFrame
        Elasticity estimates with columns: ind2d, year, theta_c
    panel_data : pd.DataFrame
        Firm-level panel with columns: gvkey, year, ind2d, cogs_D, sale_D, kexp, xsga_D
    apply_costshare_trim : bool
        If True, apply cost share trimming (p1-p99) before computing markups.
        This matches the legacy 0.4 Create Main Datasets.py behavior. Default: True
    min_year : int
        Minimum year to include (default: 1955, matching legacy behavior)
    exclude_ind2d : int or list[int] or None
        Industry codes to exclude (default: 99, matching legacy behavior).
        Set to None to include all industries.
    time_col : str
        Time column for grouping in cost share trimming (default: "year")

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: gvkey, year, ind2d, markup, theta_c, cost_share
    """
    df = panel_data.copy()

    # Apply cost share trimming (matching legacy 0.4 behavior)
    if apply_costshare_trim:
        n_before = len(df)
        df = _apply_costshare_trim(df, time_col=time_col)
        n_after = len(df)
        logger.info(f"Cost share trimming: {n_before} -> {n_after} observations ({n_before - n_after} removed)")

    # Apply year filter (matching legacy 0.4 behavior: df[df["year"] >= 1955])
    if min_year is not None:
        df = df[df[time_col] >= min_year]

    # Apply industry filter (matching legacy 0.4 behavior: df[df["ind2d"] != 99])
    if exclude_ind2d is not None:
        if isinstance(exclude_ind2d, int):
            exclude_ind2d = [exclude_ind2d]
        df = df[~df["ind2d"].isin(exclude_ind2d)]

    # Compute cost shares using De Loecker & Warzynski formula
    df["cost_share"] = df["cogs_D"] / df["sale_D"]

    # Merge elasticities
    df = df.merge(elasticities[["ind2d", "year", "theta_c"]], on=["ind2d", "year"], how="left")

    # Compute markup: mu = theta * (Revenue / COGS) = theta / cost_share
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
