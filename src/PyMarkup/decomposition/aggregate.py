"""Aggregate markup trend analysis."""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def aggregate_markup_trends(
    data: pd.DataFrame,
    markup_var: str = "markup",
    weight_var: str = "sale",
    time_var: str = "year",
    group_var: str | None = None,
) -> pd.DataFrame:
    """
    Calculate aggregate markup trends over time.

    Computes weighted average markups by period, optionally within groups
    (e.g., industries, size categories).

    Parameters
    ----------
    data : pd.DataFrame
        Firm-level data
    markup_var : str, default "markup"
        Column name for markup values
    weight_var : str, default "sale"
        Column name for weights (typically sales)
    time_var : str, default "year"
        Column name for time period
    group_var : str, optional
        Column name for grouping (e.g., industry). If None, calculates overall aggregate.

    Returns
    -------
    pd.DataFrame
        Aggregate markup by period (and group if specified)
        Columns: time_var, [group_var], aggregate_markup, total_weight, n_firms

    Examples
    --------
    >>> # Overall aggregate
    >>> trends = aggregate_markup_trends(firm_data)

    >>> # By industry
    >>> industry_trends = aggregate_markup_trends(
    ...     firm_data,
    ...     group_var="industry"
    ... )
    """
    logger.info("Calculating aggregate markup trends...")

    # Validate columns
    required_cols = {markup_var, weight_var, time_var}
    if group_var:
        required_cols.add(group_var)

    missing = required_cols - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Remove missing values
    data_clean = data[list(required_cols)].dropna()

    # Group by time (and optionally by group_var)
    group_cols = [time_var]
    if group_var:
        group_cols.append(group_var)

    # Calculate aggregates
    results = (
        data_clean.groupby(group_cols)
        .apply(
            lambda x: pd.Series(
                {
                    "aggregate_markup": (x[markup_var] * x[weight_var]).sum()
                    / x[weight_var].sum(),
                    "total_weight": x[weight_var].sum(),
                    "n_firms": len(x),
                    "min_markup": x[markup_var].min(),
                    "max_markup": x[markup_var].max(),
                    "median_markup": x[markup_var].median(),
                    "std_markup": x[markup_var].std(),
                }
            )
        )
        .reset_index()
    )

    logger.info(f"Calculated trends for {len(results)} period-group combinations")
    return results


def calculate_growth_rates(
    trends: pd.DataFrame,
    value_var: str = "aggregate_markup",
    time_var: str = "year",
    group_var: str | None = None,
) -> pd.DataFrame:
    """
    Calculate growth rates from trend data.

    Parameters
    ----------
    trends : pd.DataFrame
        Output from aggregate_markup_trends()
    value_var : str, default "aggregate_markup"
        Column to calculate growth rates for
    time_var : str, default "year"
        Time period column
    group_var : str, optional
        Grouping variable

    Returns
    -------
    pd.DataFrame
        Trends with added growth rate columns:
        - growth_rate: Period-to-period growth rate
        - cumulative_growth: Cumulative growth from first period
        - cagr: Compound Annual Growth Rate (if time_var is years)
    """
    trends = trends.copy()

    # Sort by time (and group if specified)
    sort_cols = [time_var]
    if group_var:
        sort_cols.insert(0, group_var)
    trends = trends.sort_values(sort_cols)

    # Calculate period-to-period growth
    if group_var:
        trends["growth_rate"] = trends.groupby(group_var)[value_var].pct_change()
    else:
        trends["growth_rate"] = trends[value_var].pct_change()

    # Calculate cumulative growth from first period
    def calc_cumulative(group):
        first_value = group[value_var].iloc[0]
        group["cumulative_growth"] = (group[value_var] / first_value - 1) * 100
        return group

    if group_var:
        trends = trends.groupby(group_var, group_keys=False).apply(calc_cumulative)
    else:
        trends = calc_cumulative(trends)

    # Calculate CAGR if time periods are years
    if trends[time_var].dtype in ["int64", "int32"]:

        def calc_cagr(group):
            first_year = group[time_var].iloc[0]
            first_value = group[value_var].iloc[0]

            group["cagr"] = (
                (group[value_var] / first_value) ** (1 / (group[time_var] - first_year))
                - 1
            ) * 100
            return group

        if group_var:
            trends = trends.groupby(group_var, group_keys=False).apply(calc_cagr)
        else:
            trends = calc_cagr(trends)

    return trends
