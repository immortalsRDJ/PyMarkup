"""Dynamic Olley-Pakes decomposition for markups.

Decomposes period-to-period changes in aggregate markup into three components:

    Δμ_t = Δwithin + Δreallocation + Δnet_entry

Where:
- **Δwithin**: Change in markup holding market shares at t-1 fixed
           = Σ m_{i,t-1} * Δμ_{i,t}
- **Δreallocation**: Effect of market share changes on markups
                  = Σ μ̃_{i,t-1} * Δm_{i,t} + Σ Δμ_{i,t} * Δm_{i,t}
- **Δnet_entry**: Net contribution from entering and exiting firms
                = Σ_{i∈Entry} μ̃_{i,t} * m_{i,t} - Σ_{i∈Exit} μ̃_{i,t-1} * m_{i,t-1}

This dynamic decomposition tracks how changes in individual firm markups,
market share reallocation, and firm entry/exit contribute to aggregate markup growth.

References
----------
Olley, G. Steven, and Ariel Pakes. 1996.
"The Dynamics of Productivity in the Telecommunications Equipment Industry."
Econometrica 64 (6): 1263-97.

De Loecker, J., Eeckhout, Y., & Unger, G. (2020).
"The Rise of Market Power and the Macroeconomic Implications." QJE 135(2): 561-644.
"""

from __future__ import annotations

import logging

import pandas as pd

from .base import BaseDecomposition

logger = logging.getLogger(__name__)


class OlleyPakesDecomposition(BaseDecomposition):
    """
    Dynamic Olley-Pakes decomposition of aggregate markup changes.

    Decomposes period-to-period changes in aggregate markup into three components:

    **Δμ_t = Δwithin + Δreallocation + Δnet_entry**

    1. **Within**: Markup changes within continuing firms at base period market shares
       - Captures improvements/declines in firm-level markups
    2. **Reallocation**: Effect of market share shifts + cross term
       - Captures resource reallocation toward high/low-markup firms
    3. **Net Entry**: Contribution of firm entry and exit
       - Captures how entrants differ from exiting firms

    The decomposition requires:
    - Panel data with at least 2 consecutive periods
    - Identification of continuing, entering, and exiting firms
    - Firm identifiers, periods, markups, and weights (market shares)

    Examples
    --------
    >>> from PyMarkup.decomposition import OlleyPakesDecomposition
    >>> op = OlleyPakesDecomposition()
    >>> results = op.decompose(firm_data)
    >>> print(results)
       within  reallocation  net_entry  aggregate_change  n_continuing  n_entrants  n_exiters
    2
       0.045        0.012       0.008            0.065            342           28          15
    2021  0.052        0.018       0.005            0.075            348           32          12
    """

    def decompose(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Perform dynamic Olley-Pakes decomposition for consecutive period pairs.

        Parameters
        ----------
        data : pd.DataFrame
            Firm-level panel with columns: firm_var, time_var, markup_var, weight_var.
            Must have at least 2 time periods.

        Returns
        -------
        pd.DataFrame
            One row per period transition with columns:
            - within: Within-firm markup changes (base period shares)
            - reallocation: Market share reallocation effect (including cross term)
            - net_entry: Net contribution from entry/exit
            - aggregate_change: Total change in aggregate markup
            - n_continuing: Number of continuing firms
            - n_entrants: Number of entering firms
            - n_exiters: Number of exiting firms
            Index is the period (t) being compared to (t-1).
        """
        self.validate_data(data)
        logger.info("Starting dynamic Olley-Pakes decomposition...")

        # Calculate shares
        data = self._calculate_shares(data)

        # Get sorted time periods
        periods = sorted(data[self.time_var].unique())
        if len(periods) < 2:
            raise ValueError("Need at least 2 time periods for dynamic decomposition")

        # Initialize results
        results = []

        # Decompose each consecutive period pair
        for i in range(len(periods) - 1):
            t_prev = periods[i]
            t_curr = periods[i + 1]

            decomp = self._decompose_period_pair(data, t_prev, t_curr)
            decomp["period"] = t_curr
            results.append(decomp)

        results_df = pd.DataFrame(results).set_index("period")

        logger.info(
            f"Dynamic OP decomposition complete for {len(results)} period transitions"
        )
        return results_df

    def _decompose_period_pair(
        self, data: pd.DataFrame, t_prev: int | str, t_curr: int | str
    ) -> dict:
        """
        Decompose markup change between two consecutive periods.

        Implements the dynamic decomposition:
        Δμ_t = Σ m_{i,t-1} * Δμ_{i,t} + [Σ μ̃_{i,t-1} * Δm_{i,t} + Σ Δμ_{i,t} * Δm_{i,t}]
               + [Σ_{Entry} μ̃_{i,t} * m_{i,t} - Σ_{Exit} μ̃_{i,t-1} * m_{i,t-1}]

        Parameters
        ----------
        data : pd.DataFrame
            Full firm-level panel
        t_prev : int or str
            Previous period
        t_curr : int or str
            Current period

        Returns
        -------
        dict
            Decomposition components for this period pair
        """
        # Get data for both periods
        df_t_prev = data[data[self.time_var] == t_prev].set_index(self.firm_var)
        df_t_curr = data[data[self.time_var] == t_curr].set_index(self.firm_var)

        # Identify firm sets
        firms_prev = set(df_t_prev.index)
        firms_curr = set(df_t_curr.index)

        continuing = firms_prev & firms_curr
        entrants = firms_curr - firms_prev
        exiters = firms_prev - firms_curr

        # Calculate aggregate markups
        agg_t_prev = (df_t_prev[self.markup_var] * df_t_prev["share"]).sum()
        agg_t_curr = (df_t_curr[self.markup_var] * df_t_curr["share"]).sum()
        total_change = agg_t_curr - agg_t_prev

        # Initialize components
        within = 0.0
        reallocation = 0.0
        net_entry = 0.0

        # 1. WITHIN COMPONENT: Σ m_{i,t-1} * Δμ_{i,t} for continuing firms
        if continuing:
            df_cont_prev = df_t_prev.loc[list(continuing)]
            df_cont_curr = df_t_curr.loc[list(continuing)]

            m_prev = df_cont_prev["share"]  # m_{i,t-1}
            mu_prev = df_cont_prev[self.markup_var]  # μ_{i,t-1}
            mu_curr = df_cont_curr[self.markup_var]  # μ_{i,t}
            delta_mu = mu_curr - mu_prev  # Δμ_{i,t}

            within = (m_prev * delta_mu).sum()

        # 2. REALLOCATION COMPONENT: Σ μ̃_{i,t-1} * Δm_{i,t} + Σ Δμ_{i,t} * Δm_{i,t}
        #    where μ̃ is deviation from mean
        if continuing:
            df_cont_prev = df_t_prev.loc[list(continuing)]
            df_cont_curr = df_t_curr.loc[list(continuing)]

            mu_prev = df_cont_prev[self.markup_var]
            mu_curr = df_cont_curr[self.markup_var]
            m_prev = df_cont_prev["share"]
            m_curr = df_cont_curr["share"]

            # Mean markups (all firms in t-1, not just continuing)
            mu_bar_prev = df_t_prev[self.markup_var].mean()

            # Deviations from previous period mean
            mu_tilde_prev = mu_prev - mu_bar_prev  # μ̃_{i,t-1}
            delta_m = m_curr - m_prev  # Δm_{i,t}
            delta_mu = mu_curr - mu_prev  # Δμ_{i,t}

            # Market share effect: Σ μ̃_{i,t-1} * Δm_{i,t}
            market_share_effect = (mu_tilde_prev * delta_m).sum()

            # Cross term: Σ Δμ_{i,t} * Δm_{i,t}
            cross_effect = (delta_mu * delta_m).sum()

            reallocation = market_share_effect + cross_effect

        # 3. NET ENTRY COMPONENT: Σ_{Entry} μ̃_{i,t} * m_{i,t} - Σ_{Exit} μ̃_{i,t-1} * m_{i,t-1}
        #    where μ̃ is deviation from previous period mean
        mu_bar_prev = df_t_prev[self.markup_var].mean()

        if entrants:
            df_entry = df_t_curr.loc[list(entrants)]
            mu_entry = df_entry[self.markup_var]
            m_entry = df_entry["share"]

            # Deviation of entrants from base period mean
            mu_tilde_entry = mu_entry - mu_bar_prev
            entry_contrib = (mu_tilde_entry * m_entry).sum()
        else:
            entry_contrib = 0.0

        if exiters:
            df_exit = df_t_prev.loc[list(exiters)]
            mu_exit = df_exit[self.markup_var]
            m_exit = df_exit["share"]

            # Deviation of exiters from base period mean
            mu_tilde_exit = mu_exit - mu_bar_prev
            exit_contrib = (mu_tilde_exit * m_exit).sum()
        else:
            exit_contrib = 0.0

        net_entry = entry_contrib - exit_contrib

        return {
            "within": within,
            "reallocation": reallocation,
            "net_entry": net_entry,
            "aggregate_change": total_change,
            "n_continuing": len(continuing),
            "n_entrants": len(entrants),
            "n_exiters": len(exiters),
        }
