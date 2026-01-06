"""Melitz-Polanec decomposition for markups.

References
----------
Melitz, Marc J., and Sašo Polanec. 2015.
"Dynamic Olley-Pakes Productivity Decomposition with Entry and Exit."
RAND Journal of Economics 46 (2): 362–75.
"""

from __future__ import annotations

import logging

import pandas as pd

from .base import BaseDecomposition

logger = logging.getLogger(__name__)


class MelitzDecomposition(BaseDecomposition):
    """
    Melitz-Polanec decomposition of aggregate markup changes.

    Simpler alternative to FHK that decomposes markup changes into:
    1. **Surviving component**: Changes among continuing firms
    2. **Entry component**: Contribution of entering firms
    3. **Exit component**: Contribution of exiting firms

    The Melitz-Polanec decomposition satisfies:
        Δ Aggregate Markup = Surviving + Entry - Exit

    This decomposition is particularly useful for analyzing the role of
    firm entry and exit in aggregate markup dynamics.

    Examples
    --------
    >>> from PyMarkup.decomposition import MelitzDecomposition
    >>> melitz = MelitzDecomposition()
    >>> results = melitz.decompose(firm_data)
    >>> print(results)
        surviving  entry  exit  aggregate_change
    2020      0.06   0.03  0.02             0.07
    2021      0.07   0.02  0.01             0.08
    """

    def decompose(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Perform Melitz-Polanec decomposition.

        Parameters
        ----------
        data : pd.DataFrame
            Firm-level panel with columns: firm_var, time_var, markup_var, weight_var

        Returns
        -------
        pd.DataFrame
            Decomposition results with columns:
            - surviving: Contribution from surviving firms
            - entry: Entry contribution
            - exit: Exit contribution
            - aggregate_change: Total change in aggregate markup
            Index is time periods (starting from period 2)
        """
        self.validate_data(data)
        logger.info("Starting Melitz-Polanec decomposition...")

        # Calculate shares
        data = self._calculate_shares(data)

        # Get sorted time periods
        periods = sorted(data[self.time_var].unique())
        if len(periods) < 2:
            raise ValueError("Need at least 2 time periods for decomposition")

        # Initialize results
        results = []

        # Decompose each consecutive period pair
        for i in range(len(periods) - 1):
            t = periods[i]
            t1 = periods[i + 1]

            decomp = self._decompose_period_pair(data, t, t1)
            decomp["period"] = t1
            results.append(decomp)

        results_df = pd.DataFrame(results).set_index("period")

        logger.info(
            f"Melitz-Polanec decomposition complete for {len(results)} period transitions"
        )
        return results_df

    def _decompose_period_pair(
        self, data: pd.DataFrame, t0: int | str, t1: int | str
    ) -> dict:
        """
        Decompose markup change between two periods.

        Parameters
        ----------
        data : pd.DataFrame
            Firm-level data with shares
        t0 : int or str
            Base period
        t1 : int or str
            Comparison period

        Returns
        -------
        dict
            Decomposition components
        """
        # Get data for both periods
        df_t0 = data[data[self.time_var] == t0].set_index(self.firm_var)
        df_t1 = data[data[self.time_var] == t1].set_index(self.firm_var)

        # Identify firm sets
        firms_t0 = set(df_t0.index)
        firms_t1 = set(df_t1.index)

        surviving = firms_t0 & firms_t1  # Surviving firms
        entrants = firms_t1 - firms_t0  # New entrants
        exiters = firms_t0 - firms_t1  # Exiting firms

        # Calculate aggregate markups
        agg_t0 = (df_t0[self.markup_var] * df_t0["share"]).sum()
        agg_t1 = (df_t1[self.markup_var] * df_t1["share"]).sum()
        total_change = agg_t1 - agg_t0

        # Initialize components
        surviving_comp = 0.0
        entry_comp = 0.0
        exit_comp = 0.0

        # 1. Surviving component
        if surviving:
            df_surv_t0 = df_t0.loc[list(surviving)]
            df_surv_t1 = df_t1.loc[list(surviving)]

            # Aggregate markup of survivors in each period
            surv_agg_t0 = (
                df_surv_t0[self.markup_var] * df_surv_t0["share"]
            ).sum()
            surv_agg_t1 = (
                df_surv_t1[self.markup_var] * df_surv_t1["share"]
            ).sum()

            surviving_comp = surv_agg_t1 - surv_agg_t0

        # 2. Entry component
        if entrants:
            df_entry = df_t1.loc[list(entrants)]

            # Contribution of entrants in period t1
            entry_comp = (df_entry[self.markup_var] * df_entry["share"]).sum()

        # 3. Exit component
        if exiters:
            df_exit = df_t0.loc[list(exiters)]

            # Contribution of exiters in period t0
            exit_comp = (df_exit[self.markup_var] * df_exit["share"]).sum()

        return {
            "surviving": surviving_comp,
            "entry": entry_comp,
            "exit": exit_comp,
            "aggregate_change": total_change,
            "n_surviving": len(surviving),
            "n_entrants": len(entrants),
            "n_exiters": len(exiters),
        }
