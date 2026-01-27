"""Foster-Haltiwanger-Krizan (FHK) decomposition for markups.

References
----------
Foster, Lucia, John Haltiwanger, and C. J. Krizan. 2001.
"Aggregate Productivity Growth: Lessons from Microeconomic Evidence."
In New Developments in Productivity Analysis, edited by Charles R. Hulten,
Edwin R. Dean, and Michael J. Harper, 303–72. University of Chicago Press.
"""

from __future__ import annotations

import logging

import pandas as pd

from .base import BaseDecomposition

logger = logging.getLogger(__name__)


class FHKDecomposition(BaseDecomposition):
    """
    Foster-Haltiwanger-Krizan decomposition of aggregate markup changes.

    Decomposes the change in aggregate markup between two periods into:
    1. **Within component**: Markup changes within continuing firms
    2. **Between component**: Market share reallocation among continuing firms
    3. **Cross component**: Covariance of markup and share changes
    4. **Entry component**: Contribution of entering firms
    5. **Exit component**: Contribution of exiting firms

    The FHK decomposition satisfies:
        Δ Aggregate Markup = Within + Between + Cross + Entry - Exit

    Examples
    --------
    >>> from PyMarkup.decomposition import FHKDecomposition
    >>> fhk = FHKDecomposition()
    >>> results = fhk.decompose(firm_data)
    >>> print(results)
        within  between  cross  entry  exit  aggregate_change
    2020   0.05    0.02   0.01   0.03  0.02             0.09
    2021   0.04    0.03   0.01   0.02  0.01             0.09
    """

    def decompose(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Perform FHK decomposition.

        Parameters
        ----------
        data : pd.DataFrame
            Firm-level panel with columns: firm_var, time_var, markup_var, weight_var

        Returns
        -------
        pd.DataFrame
            Decomposition results with columns:
            - within: Within-firm markup changes
            - between: Between-firm reallocation
            - cross: Cross term (covariance)
            - entry: Entry contribution
            - exit: Exit contribution
            - aggregate_change: Total change in aggregate markup
            Index is time periods (starting from period 2)
        """
        self.validate_data(data)
        logger.info("Starting FHK decomposition...")

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

        logger.info(f"FHK decomposition complete for {len(results)} period transitions")
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

        continuing = firms_t0 & firms_t1  # Continuing firms
        entrants = firms_t1 - firms_t0  # New entrants
        exiters = firms_t0 - firms_t1  # Exiting firms

        # Calculate aggregate markups
        agg_t0 = (df_t0[self.markup_var] * df_t0["share"]).sum()
        agg_t1 = (df_t1[self.markup_var] * df_t1["share"]).sum()
        total_change = agg_t1 - agg_t0

        # Initialize components
        within = 0.0
        between = 0.0
        cross = 0.0
        entry = 0.0
        exit = 0.0

        # 1. Continuing firms: Within + Between + Cross
        if continuing:
            df_cont_t0 = df_t0.loc[list(continuing)]
            df_cont_t1 = df_t1.loc[list(continuing)]

            # Markup changes
            delta_markup = df_cont_t1[self.markup_var] - df_cont_t0[self.markup_var]

            # Share changes
            delta_share = df_cont_t1["share"] - df_cont_t0["share"]

            # Base period shares and markups
            s_t0 = df_cont_t0["share"]
            mu_t0 = df_cont_t0[self.markup_var]

            # Mean markup in base period (for continuing firms)
            mu_bar_t0 = (mu_t0 * s_t0).sum()

            # Within component: Σ s_it * Δμ_it
            within = (s_t0 * delta_markup).sum()

            # Between component: Σ (μ_it - μ̄_t) * Δs_it
            between = ((mu_t0 - mu_bar_t0) * delta_share).sum()

            # Cross component: Σ Δμ_it * Δs_it
            cross = (delta_markup * delta_share).sum()

        # 2. Entry component: Σ (μ_it+1 - μ̄_t) * s_it+1  for entrants
        if entrants:
            df_entry = df_t1.loc[list(entrants)]

            # Use aggregate markup from base period as reference
            mu_bar_t0 = agg_t0

            entry = ((df_entry[self.markup_var] - mu_bar_t0) * df_entry["share"]).sum()

        # 3. Exit component: Σ (μ_it - μ̄_t) * s_it  for exiters
        if exiters:
            df_exit = df_t0.loc[list(exiters)]

            # Use aggregate markup from base period as reference
            mu_bar_t0 = agg_t0

            exit = ((df_exit[self.markup_var] - mu_bar_t0) * df_exit["share"]).sum()

        return {
            "within": within,
            "between": between,
            "cross": cross,
            "entry": entry,
            "exit": exit,
            "aggregate_change": total_change,
            "n_continuing": len(continuing),
            "n_entrants": len(entrants),
            "n_exiters": len(exiters),
        }
