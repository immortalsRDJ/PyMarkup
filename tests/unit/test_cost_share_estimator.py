"""Unit tests for CostShareEstimator."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from PyMarkup.estimators import CostShareEstimator


@pytest.fixture
def sample_panel_with_kexp() -> pd.DataFrame:
    """Create sample panel data with capital expense (kexp) for cost share estimation."""
    np.random.seed(42)
    n_firms = 30
    years = range(2010, 2020)

    data = []
    for gvkey in range(1, n_firms + 1):
        for year in years:
            sale_D = np.exp(10 + np.random.normal(0, 0.3))
            cogs_D = sale_D * (0.6 + np.random.normal(0, 0.05))
            capital_D = sale_D * (0.8 + np.random.normal(0, 0.1))
            xsga_D = sale_D * (0.15 + np.random.normal(0, 0.03))
            kexp = capital_D * 0.05  # User cost * capital

            ind2d = int(11 + (gvkey % 10))

            data.append(
                {
                    "gvkey": gvkey,
                    "year": year,
                    "sale_D": sale_D,
                    "cogs_D": cogs_D,
                    "capital_D": capital_D,
                    "xsga_D": xsga_D,
                    "kexp": kexp,
                    "ind2d": ind2d,
                    "ind3d": ind2d * 10,
                    "ind4d": ind2d * 100,
                }
            )

    return pd.DataFrame(data)


class TestCostShareEstimator:
    """Tests for CostShareEstimator class."""

    def test_initialization_default(self):
        """Test estimator initialization with defaults."""
        estimator = CostShareEstimator()

        assert estimator.include_sga is False
        assert estimator.aggregation == "median"
        assert estimator.industry_level == 2

    def test_initialization_custom_params(self):
        """Test estimator initialization with custom parameters."""
        estimator = CostShareEstimator(
            include_sga=True,
            aggregation="mean",
            industry_level=3,
        )

        assert estimator.include_sga is True
        assert estimator.aggregation == "mean"
        assert estimator.industry_level == 3

    def test_initialization_invalid_industry_level(self):
        """Test that invalid industry level raises error."""
        with pytest.raises(ValueError, match="industry_level must be 2, 3, or 4"):
            CostShareEstimator(industry_level=1)

    def test_get_method_name_without_sga(self):
        """Test method name generation without SG&A."""
        estimator = CostShareEstimator(include_sga=False, aggregation="median")
        assert "COGS only" in estimator.get_method_name()
        assert "median" in estimator.get_method_name()

    def test_get_method_name_with_sga(self):
        """Test method name generation with SG&A."""
        estimator = CostShareEstimator(include_sga=True, aggregation="mean")
        assert "with SG&A" in estimator.get_method_name()
        assert "mean" in estimator.get_method_name()

    def test_estimate_elasticities_returns_dataframe(self, sample_panel_with_kexp: pd.DataFrame):
        """Test that estimate_elasticities returns a DataFrame."""
        estimator = CostShareEstimator()
        result = estimator.estimate_elasticities(sample_panel_with_kexp)

        assert isinstance(result, pd.DataFrame)

    def test_estimate_elasticities_has_required_columns(self, sample_panel_with_kexp: pd.DataFrame):
        """Test that output has required columns."""
        estimator = CostShareEstimator()
        result = estimator.estimate_elasticities(sample_panel_with_kexp)

        required_cols = {"ind2d", "year", "theta_c"}
        assert required_cols.issubset(result.columns)

    def test_estimate_elasticities_median_aggregation(self, sample_panel_with_kexp: pd.DataFrame):
        """Test cost share estimation with median aggregation."""
        estimator = CostShareEstimator(aggregation="median")
        result = estimator.estimate_elasticities(sample_panel_with_kexp)

        # Check result is not empty
        assert len(result) > 0

        # Check theta_c is in valid range (0 to 1 for cost share)
        assert (result["theta_c"] > 0).all()
        assert (result["theta_c"] < 1).all()

    def test_estimate_elasticities_mean_aggregation(self, sample_panel_with_kexp: pd.DataFrame):
        """Test cost share estimation with mean aggregation."""
        estimator = CostShareEstimator(aggregation="mean")
        result = estimator.estimate_elasticities(sample_panel_with_kexp)

        assert len(result) > 0
        assert (result["theta_c"] > 0).all()

    def test_estimate_elasticities_weighted_mean(self, sample_panel_with_kexp: pd.DataFrame):
        """Test cost share estimation with weighted mean by sales."""
        estimator = CostShareEstimator(aggregation="weighted_mean")
        result = estimator.estimate_elasticities(sample_panel_with_kexp)

        assert len(result) > 0
        assert (result["theta_c"] > 0).all()

    def test_estimate_elasticities_with_sga(self, sample_panel_with_kexp: pd.DataFrame):
        """Test estimation including SG&A in costs."""
        estimator = CostShareEstimator(include_sga=True)
        result = estimator.estimate_elasticities(sample_panel_with_kexp)

        # With SG&A, cost share should be lower (denominator is larger)
        assert len(result) > 0
        assert (result["theta_c"] > 0).all()
        assert (result["theta_c"] < 1).all()

    def test_estimate_elasticities_without_sga(self, sample_panel_with_kexp: pd.DataFrame):
        """Test estimation without SG&A."""
        estimator = CostShareEstimator(include_sga=False)
        result = estimator.estimate_elasticities(sample_panel_with_kexp)

        assert len(result) > 0
        assert (result["theta_c"] > 0).all()

    def test_estimate_elasticities_stores_results(self, sample_panel_with_kexp: pd.DataFrame):
        """Test that results are stored in results_ attribute."""
        estimator = CostShareEstimator()
        result = estimator.estimate_elasticities(sample_panel_with_kexp)

        assert estimator.results_ is not None
        pd.testing.assert_frame_equal(estimator.results_, result)

    def test_estimate_elasticities_different_industry_levels(self, sample_panel_with_kexp: pd.DataFrame):
        """Test estimation at different industry aggregation levels."""
        # 2-digit level
        estimator_2d = CostShareEstimator(industry_level=2)
        result_2d = estimator_2d.estimate_elasticities(sample_panel_with_kexp)

        # 3-digit level
        estimator_3d = CostShareEstimator(industry_level=3)
        result_3d = estimator_3d.estimate_elasticities(sample_panel_with_kexp)

        # Both should work
        assert len(result_2d) > 0
        assert len(result_3d) > 0


class TestCostShareEstimatorEdgeCases:
    """Test edge cases for CostShareEstimator."""

    def test_empty_dataframe(self):
        """Test handling of empty input data."""
        estimator = CostShareEstimator()
        empty_df = pd.DataFrame(columns=["gvkey", "year", "cogs_D", "kexp", "ind2d"])

        # Should return empty or minimal result
        result = estimator.estimate_elasticities(empty_df)
        assert isinstance(result, pd.DataFrame)

    def test_missing_required_columns_raises_error(self, sample_panel_with_kexp: pd.DataFrame):
        """Test that missing required columns raises error."""
        df = sample_panel_with_kexp.drop(columns=["kexp"])

        estimator = CostShareEstimator()

        with pytest.raises(ValueError, match="Missing required columns"):
            estimator.estimate_elasticities(df)

    def test_missing_sga_when_required(self, sample_panel_with_kexp: pd.DataFrame):
        """Test error when SG&A is required but missing."""
        df = sample_panel_with_kexp.drop(columns=["xsga_D"])

        estimator = CostShareEstimator(include_sga=True)

        with pytest.raises(ValueError, match="Missing required columns"):
            estimator.estimate_elasticities(df)

    def test_zero_denominators_handled(self):
        """Test handling of zero denominators in cost share calculation."""
        # Create data with some zero costs
        data = []
        for i in range(10):
            data.append(
                {
                    "gvkey": i,
                    "year": 2020,
                    "cogs_D": 100 if i > 5 else 0,  # Some zero COGS
                    "kexp": 10,
                    "ind2d": 31,
                }
            )
        df = pd.DataFrame(data)

        estimator = CostShareEstimator()
        result = estimator.estimate_elasticities(df)

        # Should handle zeros gracefully (drop or use NaN)
        assert isinstance(result, pd.DataFrame)
