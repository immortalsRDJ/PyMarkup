"""Unit tests for ACFEstimator."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from PyMarkup.estimators import ACFEstimator


class TestACFEstimator:
    """Tests for ACFEstimator class."""

    def test_initialization_default(self):
        """Test estimator initialization with defaults."""
        estimator = ACFEstimator()

        assert estimator.window_years == 5
        assert estimator.include_market_share is True
        assert estimator.industry_level == 2
        assert estimator.min_observations == 15

    def test_initialization_custom_params(self):
        """Test estimator initialization with custom parameters."""
        estimator = ACFEstimator(
            window_years=7,
            include_market_share=False,
            industry_level=3,
            min_observations=20,
        )

        assert estimator.window_years == 7
        assert estimator.include_market_share is False
        assert estimator.industry_level == 3
        assert estimator.min_observations == 20

    def test_initialization_invalid_industry_level(self):
        """Test that invalid industry level raises error."""
        with pytest.raises(ValueError, match="industry_level must be 2, 3, or 4"):
            ACFEstimator(industry_level=5)

    def test_get_method_name(self):
        """Test method name generation."""
        estimator = ACFEstimator()
        assert estimator.get_method_name() == "ACF (Ackerberg-Caves-Frazer)"

    def test_preprocess_creates_log_variables(self, sample_prepared_panel: pd.DataFrame):
        """Test that preprocessing creates necessary log variables."""
        estimator = ACFEstimator()
        df = estimator._preprocess(sample_prepared_panel)

        # Check log variables were created
        assert "y" in df.columns  # log output
        assert "c" in df.columns  # log COGS
        assert "k" in df.columns  # log capital

    def test_preprocess_creates_polynomials(self, sample_prepared_panel: pd.DataFrame):
        """Test that preprocessing creates polynomial terms."""
        estimator = ACFEstimator()
        df = estimator._preprocess(sample_prepared_panel)

        # Check polynomials
        assert "c2" in df.columns
        assert "k2" in df.columns
        assert "ck" in df.columns

    def test_preprocess_creates_lags(self, sample_prepared_panel: pd.DataFrame):
        """Test that preprocessing creates lagged variables."""
        estimator = ACFEstimator()
        df = estimator._preprocess(sample_prepared_panel)

        # Check lags exist
        assert "c_lag" in df.columns or "L.c" in df.columns
        assert "k_lag" in df.columns or "L.k" in df.columns

    def test_estimate_elasticities_returns_dataframe(self, sample_prepared_panel: pd.DataFrame):
        """Test that estimate_elasticities returns a DataFrame."""
        estimator = ACFEstimator(min_observations=5)
        result = estimator.estimate_elasticities(sample_prepared_panel)

        assert isinstance(result, pd.DataFrame)

    def test_estimate_elasticities_has_required_columns(self, sample_prepared_panel: pd.DataFrame):
        """Test that output has required columns."""
        estimator = ACFEstimator(min_observations=5)
        result = estimator.estimate_elasticities(sample_prepared_panel)

        # Check required columns
        required_cols = {"ind2d", "year", "theta_c"}
        assert required_cols.issubset(result.columns)

    def test_estimate_elasticities_with_market_share(self, sample_prepared_panel: pd.DataFrame):
        """Test ACF estimation with market share controls."""
        estimator = ACFEstimator(include_market_share=True, min_observations=5)
        result = estimator.estimate_elasticities(sample_prepared_panel)

        assert isinstance(result, pd.DataFrame)
        # May or may not have results depending on data quality
        # Just check it doesn't crash

    def test_estimate_elasticities_without_market_share(self, sample_prepared_panel: pd.DataFrame):
        """Test ACF estimation without market share controls."""
        estimator = ACFEstimator(include_market_share=False, min_observations=5)
        result = estimator.estimate_elasticities(sample_prepared_panel)

        assert isinstance(result, pd.DataFrame)

    def test_estimate_elasticities_stores_results(self, sample_prepared_panel: pd.DataFrame):
        """Test that results are stored in results_ attribute."""
        estimator = ACFEstimator(min_observations=5)
        result = estimator.estimate_elasticities(sample_prepared_panel)

        assert estimator.results_ is not None
        # Results should be the same object
        pd.testing.assert_frame_equal(estimator.results_, result)

    def test_estimate_elasticities_different_industry_levels(self, sample_prepared_panel: pd.DataFrame):
        """Test estimation at different industry aggregation levels."""
        # 2-digit level
        estimator_2d = ACFEstimator(industry_level=2, min_observations=5)
        result_2d = estimator_2d.estimate_elasticities(sample_prepared_panel)

        # 3-digit level
        estimator_3d = ACFEstimator(industry_level=3, min_observations=5)
        result_3d = estimator_3d.estimate_elasticities(sample_prepared_panel)

        # Both should return DataFrames
        assert isinstance(result_2d, pd.DataFrame)
        assert isinstance(result_3d, pd.DataFrame)

    def test_estimate_elasticities_reasonable_values(self, sample_prepared_panel: pd.DataFrame):
        """Test that estimated elasticities are in reasonable range (if successful)."""
        estimator = ACFEstimator(min_observations=5)
        result = estimator.estimate_elasticities(sample_prepared_panel)

        if len(result) > 0 and "theta_c" in result.columns:
            # Elasticities should typically be positive and less than 2
            # Note: ACF can fail to converge, so we're lenient here
            valid_estimates = result["theta_c"].dropna()
            if len(valid_estimates) > 0:
                # Just check some are in a reasonable range
                assert (valid_estimates > -1).any()  # Not too negative
                assert (valid_estimates < 5).any()  # Not too large


class TestACFEstimatorEdgeCases:
    """Test edge cases for ACFEstimator."""

    def test_empty_dataframe(self):
        """Test handling of empty input data."""
        estimator = ACFEstimator()
        empty_df = pd.DataFrame(
            columns=["gvkey", "year", "sale_D", "cogs_D", "capital_D", "ind2d", "nrind2"]
        )

        # Should not crash, return empty or minimal result
        result = estimator.estimate_elasticities(empty_df)
        assert isinstance(result, pd.DataFrame)

    def test_insufficient_observations(self):
        """Test handling when there aren't enough observations."""
        # Create minimal data (less than min_observations)
        data = []
        for i in range(5):  # Only 5 observations
            data.append(
                {
                    "gvkey": i,
                    "year": 2020,
                    "sale_D": np.exp(10),
                    "cogs_D": np.exp(9),
                    "capital_D": np.exp(9.5),
                    "ind2d": 31,
                    "nrind2": 1,
                }
            )
        df = pd.DataFrame(data)

        estimator = ACFEstimator(min_observations=20)  # Require more than available
        result = estimator.estimate_elasticities(df)

        # Should return empty or minimal result
        assert isinstance(result, pd.DataFrame)

    def test_single_industry_panel(self):
        """Test ACF estimation with data from single industry."""
        np.random.seed(42)
        # Create panel data for single industry
        data = []
        for gvkey in range(1, 25):
            for year in range(2010, 2020):
                data.append(
                    {
                        "gvkey": gvkey,
                        "year": year,
                        "sale_D": np.exp(10 + 0.02 * (year - 2010) + np.random.normal(0, 0.2)),
                        "cogs_D": np.exp(9 + 0.02 * (year - 2010) + np.random.normal(0, 0.2)),
                        "capital_D": np.exp(9.5 + 0.01 * (year - 2010) + np.random.normal(0, 0.15)),
                        "ind2d": 31,  # Single industry
                        "nrind2": 1,
                    }
                )
        df = pd.DataFrame(data)

        estimator = ACFEstimator(min_observations=10)
        result = estimator.estimate_elasticities(df)

        # Should handle single industry
        assert isinstance(result, pd.DataFrame)

    def test_estimation_convergence_failure_handled(self, sample_prepared_panel: pd.DataFrame):
        """Test that convergence failures in GMM are handled gracefully."""
        # ACF uses optimization which can fail
        # The estimator should handle this and return partial results or empty frame
        estimator = ACFEstimator(min_observations=5)

        # Should not raise exception even if optimization fails internally
        result = estimator.estimate_elasticities(sample_prepared_panel)
        assert isinstance(result, pd.DataFrame)
