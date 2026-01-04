"""
Test script to verify all three estimators work correctly.

This script demonstrates:
1. Creating synthetic panel data
2. Running all three estimators (Wooldridge IV, Cost Share, ACF)
3. Comparing results
"""

import logging

import numpy as np
import pandas as pd

from PyMarkup.core.data_preparation import create_compustat_panel
from PyMarkup.estimators import ACFEstimator, CostShareEstimator, WooldridgeIVEstimator

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def create_synthetic_panel() -> pd.DataFrame:
    """
    Create synthetic panel data for testing.

    This generates a small panel with realistic structure but random data.
    """
    np.random.seed(42)

    firms = 100
    years = range(2000, 2020)
    industries = [11, 21, 22, 23, 31, 32, 33]

    records = []
    for i in range(firms):
        ind = np.random.choice(industries)
        for year in years:
            # Generate synthetic data with some correlation
            capital = np.random.lognormal(10, 1)
            cogs = np.random.lognormal(11, 1)
            sale = cogs * np.random.uniform(1.2, 2.0)  # Markup
            xsga = sale * np.random.uniform(0.1, 0.3)

            records.append(
                {
                    "gvkey": f"FIRM{i:03d}",
                    "year": year,
                    "ind2d": ind,
                    "nrind2": industries.index(ind) + 1,
                    "sale_D": sale,
                    "cogs_D": cogs,
                    "capital_D": capital,
                    "xsga_D": xsga,
                    "kexp": capital * 0.1,  # User cost = 10%
                    # Market shares (for ACF)
                    "ms2d": np.random.uniform(0.01, 0.05),
                    "ms4d": np.random.uniform(0.01, 0.05),
                }
            )

    df = pd.DataFrame(records)
    logger.info(f"Created synthetic panel: {len(df)} observations, {firms} firms, {len(years)} years")
    return df


def test_cost_share_estimator(data: pd.DataFrame):
    """Test the CostShareEstimator."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing CostShareEstimator")
    logger.info("=" * 60)

    estimator = CostShareEstimator(include_sga=False, aggregation="median", industry_level=2)

    elasticities = estimator.estimate_elasticities(data)

    logger.info(f"\nResults shape: {elasticities.shape}")
    logger.info(f"Sample results:\n{elasticities.head(10)}")
    logger.info(f"\nSummary statistics:")
    logger.info(f"  Mean theta_c: {elasticities['theta_c'].mean():.4f}")
    logger.info(f"  Median theta_c: {elasticities['theta_c'].median():.4f}")
    logger.info(f"  Std theta_c: {elasticities['theta_c'].std():.4f}")

    return elasticities


def test_wooldridge_iv_estimator(data: pd.DataFrame):
    """Test the WooldridgeIVEstimator."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing WooldridgeIVEstimator")
    logger.info("=" * 60)

    estimator = WooldridgeIVEstimator(
        specification="spec2",  # Include SG&A
        window_years=5,
        industry_level=2,
        min_observations=10,  # Lower threshold for synthetic data
    )

    elasticities = estimator.estimate_elasticities(data)

    logger.info(f"\nResults shape: {elasticities.shape}")
    logger.info(f"Sample results:\n{elasticities.head(10)}")
    if len(elasticities) > 0:
        logger.info(f"\nSummary statistics:")
        logger.info(f"  Mean theta_c: {elasticities['theta_c'].mean():.4f}")
        logger.info(f"  Median theta_c: {elasticities['theta_c'].median():.4f}")
        logger.info(f"  Std theta_c: {elasticities['theta_c'].std():.4f}")
        if elasticities["theta_k"].notna().any():
            logger.info(f"  Mean theta_k: {elasticities['theta_k'].mean():.4f}")

    return elasticities


def test_acf_estimator(data: pd.DataFrame):
    """Test the ACFEstimator."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing ACFEstimator")
    logger.info("=" * 60)

    estimator = ACFEstimator(
        window_years=5, include_market_share=True, industry_level=2, min_observations=10  # Lower for synthetic data
    )

    elasticities = estimator.estimate_elasticities(data)

    logger.info(f"\nResults shape: {elasticities.shape}")
    logger.info(f"Sample results:\n{elasticities.head(10)}")
    if len(elasticities) > 0:
        logger.info(f"\nSummary statistics:")
        logger.info(f"  Mean theta_c: {elasticities['theta_c'].mean():.4f}")
        logger.info(f"  Median theta_c: {elasticities['theta_c'].median():.4f}")
        logger.info(f"  Std theta_c: {elasticities['theta_c'].std():.4f}")

    return elasticities


def compare_estimators(cs_results, iv_results, acf_results):
    """Compare results across all three estimators."""
    logger.info("\n" + "=" * 60)
    logger.info("Comparing Estimators")
    logger.info("=" * 60)

    comparison = []

    if len(cs_results) > 0:
        comparison.append(
            {
                "Method": "Cost Share",
                "N": len(cs_results),
                "Mean theta_c": cs_results["theta_c"].mean(),
                "Median theta_c": cs_results["theta_c"].median(),
            }
        )

    if len(iv_results) > 0:
        comparison.append(
            {
                "Method": "Wooldridge IV",
                "N": len(iv_results),
                "Mean theta_c": iv_results["theta_c"].mean(),
                "Median theta_c": iv_results["theta_c"].median(),
            }
        )

    if len(acf_results) > 0:
        comparison.append(
            {
                "Method": "ACF",
                "N": len(acf_results),
                "Mean theta_c": acf_results["theta_c"].mean(),
                "Median theta_c": acf_results["theta_c"].median(),
            }
        )

    if comparison:
        comp_df = pd.DataFrame(comparison)
        logger.info(f"\n{comp_df.to_string(index=False)}")
    else:
        logger.warning("No results to compare!")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("PyMarkup Estimator Test Suite")
    logger.info("=" * 60)

    # Create synthetic data
    data = create_synthetic_panel()

    # Test each estimator
    cs_results = test_cost_share_estimator(data)
    iv_results = test_wooldridge_iv_estimator(data)
    acf_results = test_acf_estimator(data)

    # Compare results
    compare_estimators(cs_results, iv_results, acf_results)

    logger.info("\n" + "=" * 60)
    logger.info("All tests completed!")
    logger.info("=" * 60)
