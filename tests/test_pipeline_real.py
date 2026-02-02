"""Test data preparation + theta estimation with real Compustat data.

Run with:
    uv run python tests/test_pipeline_real.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

COMPUSTAT_PATH = "Input/DLEU/Compustat_annual.dta"
MACRO_PATH = "Input/DLEU/macro_vars_new.xlsx"


def check_inputs() -> bool:
    """Check required input files exist."""
    missing = []
    for p in [COMPUSTAT_PATH, MACRO_PATH]:
        if not Path(p).exists():
            missing.append(p)
    if missing:
        print(f"SKIP: Missing input files: {missing}")
        return False
    return True


def test_data_preparation() -> pd.DataFrame:
    """Test data preparation step."""
    print("\n" + "=" * 60)
    print("STEP 1: Data Preparation")
    print("=" * 60)

    from PyMarkup.core.data_preparation import create_compustat_panel

    panel = create_compustat_panel(COMPUSTAT_PATH, MACRO_PATH)

    print(f"  Rows:       {panel.shape[0]:,}")
    print(f"  Columns:    {panel.shape[1]}")
    print(f"  Year range: {panel['year'].min()} - {panel['year'].max()}")
    print(f"  Industries: {panel['ind2d'].nunique()} unique 2-digit NAICS")
    print(f"  Firms:      {panel['gvkey'].nunique():,}")

    # Verify key columns exist
    required = ["sale_D", "cogs_D", "capital_D", "kexp", "nrind2", "ms2d"]
    present = [c for c in required if c in panel.columns]
    missing = [c for c in required if c not in panel.columns]
    print(f"  Key columns present: {present}")
    if missing:
        print(f"  WARNING - Missing columns: {missing}")

    print("\n  Deflated variable summary:")
    print(panel[["sale_D", "cogs_D", "capital_D"]].describe().to_string())

    return panel


def test_cost_share(panel: pd.DataFrame) -> pd.DataFrame:
    """Test Cost Share estimator."""
    print("\n" + "=" * 60)
    print("STEP 2a: Cost Share Estimation")
    print("=" * 60)

    from PyMarkup.estimators import CostShareEstimator

    est = CostShareEstimator()
    result = est.estimate_elasticities(panel)

    print(f"  Industry-year estimates: {len(result):,}")
    if len(result) > 0:
        print(f"  theta_c summary:")
        print(f"    mean:   {result['theta_c'].mean():.4f}")
        print(f"    median: {result['theta_c'].median():.4f}")
        print(f"    std:    {result['theta_c'].std():.4f}")
        print(f"    min:    {result['theta_c'].min():.4f}")
        print(f"    max:    {result['theta_c'].max():.4f}")
    else:
        print("  WARNING: No estimates produced")

    return result


def test_wooldridge_iv(panel: pd.DataFrame) -> pd.DataFrame:
    """Test Wooldridge IV estimator."""
    print("\n" + "=" * 60)
    print("STEP 2b: Wooldridge IV Estimation")
    print("=" * 60)

    from PyMarkup.estimators import WooldridgeIVEstimator

    est = WooldridgeIVEstimator(specification="spec2", window_years=5)
    result = est.estimate_elasticities(panel)

    print(f"  Industry-year estimates: {len(result):,}")
    if len(result) > 0:
        print(f"  theta_c summary:")
        print(f"    mean:   {result['theta_c'].mean():.4f}")
        print(f"    median: {result['theta_c'].median():.4f}")
        print(f"    std:    {result['theta_c'].std():.4f}")
        print(f"    min:    {result['theta_c'].min():.4f}")
        print(f"    max:    {result['theta_c'].max():.4f}")
        if "theta_k" in result.columns:
            print(f"  theta_k summary:")
            print(f"    mean:   {result['theta_k'].mean():.4f}")
            print(f"    median: {result['theta_k'].median():.4f}")
    else:
        print("  WARNING: No estimates produced")

    return result


def test_acf(panel: pd.DataFrame) -> pd.DataFrame:
    """Test ACF estimator."""
    print("\n" + "=" * 60)
    print("STEP 2c: ACF Estimation")
    print("=" * 60)

    from PyMarkup.estimators import ACFEstimator

    est = ACFEstimator(window_years=5, include_market_share=True)
    result = est.estimate_elasticities(panel)

    print(f"  Industry-year estimates: {len(result):,}")
    if len(result) > 0:
        print(f"  theta_c summary:")
        print(f"    mean:   {result['theta_c'].mean():.4f}")
        print(f"    median: {result['theta_c'].median():.4f}")
        print(f"    std:    {result['theta_c'].std():.4f}")
        print(f"    min:    {result['theta_c'].min():.4f}")
        print(f"    max:    {result['theta_c'].max():.4f}")
    else:
        print("  WARNING: No estimates produced")

    return result


def test_markup_calculation(
    panel: pd.DataFrame, elasticities: pd.DataFrame, method: str
) -> None:
    """Test markup calculation using core module (compute_markups + aggregate_markups)."""
    from PyMarkup.core.markup_calculation import aggregate_markups, compute_markups

    print(f"\n  Markup calculation ({method}):")

    # --- compute_markups: cogs_only ---
    firm_markups = compute_markups(elasticities, panel, cost_share_type="cogs_only")

    assert {"gvkey", "year", "ind2d", "markup", "theta_c", "cost_share"} == set(
        firm_markups.columns
    ), f"Unexpected columns: {list(firm_markups.columns)}"

    valid = firm_markups.dropna(subset=["markup"])
    valid = valid[(valid["markup"] > 0) & (valid["markup"] < 50)]
    if len(valid) == 0:
        print("    SKIP: No valid firm-year observations")
        return

    print(f"    Firm-year observations: {len(valid):,}")
    print(f"    Markup mean:   {valid['markup'].mean():.4f}")
    print(f"    Markup median: {valid['markup'].median():.4f}")
    print(f"    Markup std:    {valid['markup'].std():.4f}")
    print(f"    Markup > 1:    {(valid['markup'] > 1).mean():.1%}")

    # Cost share should be in (0, 1)
    cs = valid["cost_share"]
    assert (cs > 0).all() and (cs <= 1).all(), (
        f"Cost shares outside (0,1]: min={cs.min():.4f}, max={cs.max():.4f}"
    )

    # --- compute_markups: with_sga ---
    if "xsga_D" in panel.columns:
        fm_sga = compute_markups(elasticities, panel, cost_share_type="with_sga")
        valid_sga = fm_sga.dropna(subset=["markup"])
        valid_sga = valid_sga[(valid_sga["markup"] > 0) & (valid_sga["markup"] < 50)]
        if len(valid_sga) > 0:
            print(
                f"    With SGA - observations: {len(valid_sga):,}, "
                f"median markup: {valid_sga['markup'].median():.4f}"
            )

    # --- aggregate_markups ---
    agg_year = aggregate_markups(valid, by="year", method="median")
    assert len(agg_year) > 0, "Year aggregation produced no rows"
    print(
        f"    Yearly median markup: [{agg_year['markup'].min():.4f}, "
        f"{agg_year['markup'].max():.4f}] over {len(agg_year)} years"
    )

    agg_ind = aggregate_markups(valid, by="ind2d", method="mean")
    assert len(agg_ind) > 0, "Industry aggregation produced no rows"
    print(f"    Industry mean markup: {len(agg_ind)} industries")

    agg_both = aggregate_markups(valid, by=["ind2d", "year"], method="median")
    assert len(agg_both) > 0, "Industry-year aggregation produced no rows"
    print(f"    Industry-year cells: {len(agg_both)}")


def main() -> int:
    print("=" * 60)
    print("PyMarkup Pipeline Test (Real Data)")
    print("=" * 60)

    if not check_inputs():
        return 1

    # Step 1: Data preparation
    panel = test_data_preparation()

    # Step 2: Estimators
    cs_result = test_cost_share(panel)
    iv_result = test_wooldridge_iv(panel)
    acf_result = test_acf(panel)

    # Step 3: Markup calculation
    print("\n" + "=" * 60)
    print("STEP 3: Markup Calculation")
    print("=" * 60)
    if len(cs_result) > 0:
        test_markup_calculation(panel, cs_result, "Cost Share")
    if len(iv_result) > 0:
        test_markup_calculation(panel, iv_result, "Wooldridge IV")
    if len(acf_result) > 0:
        test_markup_calculation(panel, acf_result, "ACF")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Data preparation:  {panel.shape[0]:,} firm-years")
    print(f"  Cost Share:        {len(cs_result):,} industry-year estimates")
    print(f"  Wooldridge IV:     {len(iv_result):,} industry-year estimates")
    print(f"  ACF:               {len(acf_result):,} industry-year estimates")
    print("=" * 60)
    print("DONE")

    return 0


if __name__ == "__main__":
    sys.exit(main())
