"""Base class for markup decompositions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class BaseDecomposition(ABC):
    """
    Abstract base class for markup decomposition methods.

    Decompositions break down aggregate markup changes into components
    like within-firm changes, between-firm reallocation, and entry/exit effects.
    """

    def __init__(
        self,
        firm_var: str = "gvkey",
        time_var: str = "year",
        markup_var: str = "markup",
        weight_var: str = "sale",
    ):
        """
        Initialize decomposition.

        Parameters
        ----------
        firm_var : str, default "gvkey"
            Column name for firm identifier
        time_var : str, default "year"
            Column name for time period
        markup_var : str, default "markup"
            Column name for markup values
        weight_var : str, default "sale"
            Column name for weights (typically sales or market share)
        """
        self.firm_var = firm_var
        self.time_var = time_var
        self.markup_var = markup_var
        self.weight_var = weight_var

    @abstractmethod
    def decompose(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Perform decomposition on firm-level data.

        Parameters
        ----------
        data : pd.DataFrame
            Firm-level panel data with columns: firm_var, time_var, markup_var, weight_var

        Returns
        -------
        pd.DataFrame
            Decomposition results by time period
        """
        pass

    def validate_data(self, data: pd.DataFrame) -> None:
        """
        Validate input data has required columns.

        Parameters
        ----------
        data : pd.DataFrame
            Input data to validate

        Raises
        ------
        ValueError
            If required columns are missing
        """
        required_cols = {self.firm_var, self.time_var, self.markup_var, self.weight_var}
        missing = required_cols - set(data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Check for missing values
        for col in required_cols:
            if data[col].isna().any():
                n_missing = data[col].isna().sum()
                raise ValueError(f"Column '{col}' has {n_missing} missing values")

    def _calculate_shares(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate market shares for each firm-period.

        Parameters
        ----------
        data : pd.DataFrame
            Firm-level data

        Returns
        -------
        pd.DataFrame
            Data with added 'share' column
        """
        data = data.copy()

        # Calculate total weight by period
        total_by_period = (
            data.groupby(self.time_var)[self.weight_var].sum().rename("total_weight")
        )

        # Merge and calculate shares
        data = data.merge(total_by_period, left_on=self.time_var, right_index=True)
        data["share"] = data[self.weight_var] / data["total_weight"]

        return data

    def _calculate_aggregate(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate aggregate (weighted average) markup by period.

        Parameters
        ----------
        data : pd.DataFrame
            Firm-level data with 'share' column

        Returns
        -------
        pd.Series
            Aggregate markup by time period
        """
        if "share" not in data.columns:
            data = self._calculate_shares(data)

        aggregate = (
            data.groupby(self.time_var)
            .apply(lambda x: (x[self.markup_var] * x["share"]).sum())
            .rename("aggregate_markup")
        )

        return aggregate

    def summary(self, decomposition: pd.DataFrame) -> dict[str, Any]:
        """
        Generate summary statistics for decomposition results.

        Parameters
        ----------
        decomposition : pd.DataFrame
            Decomposition results from decompose()

        Returns
        -------
        dict
            Summary statistics
        """
        # Calculate total change
        periods = sorted(decomposition.index)
        if len(periods) < 2:
            return {"error": "Need at least 2 periods for summary"}

        first_period = periods[0]
        last_period = periods[-1]

        summary = {
            "start_period": first_period,
            "end_period": last_period,
            "total_change": decomposition.loc[last_period].sum()
            - decomposition.loc[first_period].sum(),
            "n_periods": len(periods),
        }

        # Add component contributions if available
        component_cols = [c for c in decomposition.columns if c != "aggregate_markup"]
        if component_cols:
            changes = decomposition.loc[last_period] - decomposition.loc[first_period]
            total_change = changes.sum()

            summary["component_contributions"] = {}
            for col in component_cols:
                contribution = changes[col] / total_change if total_change != 0 else 0
                summary["component_contributions"][col] = {
                    "absolute_change": changes[col],
                    "percentage_contribution": contribution * 100,
                }

        return summary
