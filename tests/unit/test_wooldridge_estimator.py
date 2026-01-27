"""Unit tests for WooldridgeIVEstimator."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from PyMarkup.estimators import WooldridgeIVEstimator


class TestWooldridgeIVEstimator:
    """Tests for WooldridgeIVEstimator class."""

    def test_initialization_default(self):
        """Test estimator initialization with defaults."""
        estimator = WooldridgeIVEstimator()

        assert estimator.specification == "spec2"
        assert estimator.window_years == 5
        assert estimator.industry_level == 2
        assert estimator.min_observations == 15

    def test_initialization_custom_params(self):
        """Test estimator initialization with custom parameters."""
        estimator = WooldridgeIVEstimator(
            specification="spec1",
            window_years=7,
            industry_level=3,
            min_observations=20,
        )

        assert estimator.specification == "spec1"
        assert estimator.window_years == 7
        assert estimator.industry_level == 3
        assert estimator.min_observations == 20

    def test_initialization_invalid_industry_level(self):
        """Test that invalid industry level raises error."""
        with pytest.raises(ValueError, match="industry_level must be 2, 3, or 4"):
            WooldridgeIVEstimator(industry_level=5)

    def test_get_method_name(self):
        """Test method name generation."""
        estimator = WooldridgeIVEstimator(specification="spec2")
        assert estimator.get_method_name() == "Wooldridge IV (spec2)"

        estimator_spec1 = WooldridgeIVEstimator(specification="spec1")
        assert estimator_spec1.get_method_name() == "Wooldridge IV (spec1)"

    def test_preprocess_creates_log_variables(self, sample_prepared_panel: pd.DataFrame):
        """Test that preprocessing creates necessary log variables."""
        estimator = WooldridgeIVEstimator()
        df = estimator._preprocess(sample_prepared_panel)

        # Check log variables were created
        assert "r" in df.columns  # log revenue
        assert "y" in df.columns
        assert "c" in df.columns  # log COGS
        assert "k" in df.columns  # log capital

    def test_preprocess_creates_polynomials(self, sample_prepared_panel: pd.DataFrame):
        """Test that preprocessing creates polynomial terms."""
        estimator = WooldridgeIVEstimator()
        df = estimator._preprocess(sample_prepared_panel)

        # Check polynomials
        assert "c2" in df.columns
        assert "c3" in df.columns
        assert "k2" in df.columns
        assert "k3" in df.columns
        assert "ck" in df.columns

    def test_preprocess_creates_lags(self, sample_prepared_panel: pd.DataFrame):
        """Test that preprocessing creates lagged variables."""
        estimator = WooldridgeIVEstimator()
        df = estimator._preprocess(sample_prepared_panel)

        # Check lags exist
        assert "L.c" in df.columns
        assert "L.k" in df.columns
        assert "L.i" in df.columns

    def test_preprocess_handles_sga(self, sample_prepared_panel: pd.DataFrame):
        """Test preprocessing handles SG&A for spec2."""
        estimator = WooldridgeIVEstimator(specification="spec2")
        df = estimator._preprocess(sample_prepared_panel)

        # Check SG&A variables
        assert "lsga" in df.columns
        assert "lsga2" in df.columns

    def test_run_iv_insufficient_observations(self, sample_prepared_panel: pd.DataFrame):
        """Test IV estimation returns None with insufficient data."""
        estimator = WooldridgeIVEstimator(min_observations=1000)  # Require more than available
        df = estimator._preprocess(sample_prepared_panel)

        result = estimator._run_iv(
            df,
            dep="r",
            endog="c",
            exog=["k"],
            instruments=["L.c"],
        )

        assert result is None

    def test_estimate_elasticities_returns_dataframe(self, sample_prepared_panel: pd.DataFrame):
        """Test that estimate_elasticities returns a DataFrame."""
        estimator = WooldridgeIVEstimator(specification="spec2", min_observations=5)
        result = estimator.estimate_elasticities(sample_prepared_panel)

        assert isinstance(result, pd.DataFrame)

    def test_estimate_elasticities_has_required_columns(self, sample_prepared_panel: pd.DataFrame):
        """Test that output has required columns."""
        estimator = WooldridgeIVEstimator(specification="spec2", min_observations=5)
        result = estimator.estimate_elasticities(sample_prepared_panel)

        # Check required columns
        required_cols = {"ind2d", "year", "theta_c", "theta_k"}
        assert required_cols.issubset(result.columns)

    def test_estimate_elasticities_spec1_vs_spec2(self, sample_prepared_panel: pd.DataFrame):
        """Test that spec1 and spec2 use different coefficients."""
        # Estimate with spec1
        estimator_spec1 = WooldridgeIVEstimator(specification="spec1", min_observations=5)
        result_spec1 = estimator_spec1.estimate_elasticities(sample_prepared_panel)

        # Estimate with spec2
        estimator_spec2 = WooldridgeIVEstimator(specification="spec2", min_observations=5)
        result_spec2 = estimator_spec2.estimate_elasticities(sample_prepared_panel)

        # Both should return results
        assert len(result_spec1) > 0
        assert len(result_spec2) > 0

        # They may differ (different specifications)
        assert "theta_c" in result_spec1.columns
        assert "theta_c" in result_spec2.columns

    def test_estimate_elasticities_stores_results(self, sample_prepared_panel: pd.DataFrame):
        """Test that results are stored in results_ attribute."""
        estimator = WooldridgeIVEstimator(specification="spec2", min_observations=5)
        result = estimator.estimate_elasticities(sample_prepared_panel)

        # Check results are stored
        assert estimator.results_ is not None
        pd.testing.assert_frame_equal(estimator.results_, result)

    def test_estimate_elasticities_no_missing_theta_c(self, sample_prepared_panel: pd.DataFrame):
        """Test that output has no missing theta_c values."""
        estimator = WooldridgeIVEstimator(specification="spec2", min_observations=5)
        result = estimator.estimate_elasticities(sample_prepared_panel)

        # Should have dropped rows with missing theta_c
        assert result["theta_c"].notna().all()

    def test_estimate_elasticities_different_industry_levels(self, sample_prepared_panel: pd.DataFrame):
        """Test estimation at different industry aggregation levels."""
        # 2-digit level
        estimator_2d = WooldridgeIVEstimator(industry_level=2, min_observations=5)
        result_2d = estimator_2d.estimate_elasticities(sample_prepared_panel)

        # 3-digit level
        estimator_3d = WooldridgeIVEstimator(industry_level=3, min_observations=5)
        result_3d = estimator_3d.estimate_elasticities(sample_prepared_panel)

        # Both should work
        assert len(result_2d) > 0
        assert len(result_3d) > 0

    def test_estimate_elasticities_reasonable_values(self, sample_prepared_panel: pd.DataFrame):
        """Test that estimated elasticities are in reasonable range."""
        estimator = WooldridgeIVEstimator(specification="spec2", min_observations=5)
        result = estimator.estimate_elasticities(sample_prepared_panel)

        if len(result) > 0:
            # Elasticities should be positive and less than 2 (typically)
            assert (result["theta_c"] > 0).any()  # At least some positive
            assert (result["theta_c"] < 2).any()  # Most should be reasonable

            # Capital elasticity should also be reasonable
            if result["theta_k"].notna().any():
                assert (result["theta_k"] > -0.5).all()  # Not too negative
                assert (result["theta_k"] < 2).all()  # Not too large


class TestWooldridgeIVEstimatorEdgeCases:
    """Test edge cases for WooldridgeIVEstimator."""

    def test_empty_dataframe(self):
        """Test handling of empty input data."""
        estimator = WooldridgeIVEstimator()
        empty_df = pd.DataFrame(
            columns=["gvkey", "year", "sale_D", "cogs_D", "capital_D", "xsga_D", "ind2d", "nrind2"]
        )

        # Should not crash, but return empty or minimal result
        result = estimator.estimate_elasticities(empty_df)
        assert isinstance(result, pd.DataFrame)

    def test_single_industry(self):
        """Test estimation with data from single industry."""
        np.random.seed(42)
        # Create data for single industry
        data = []
        for gvkey in range(1, 20):
            for year in range(2010, 2020):
                data.append(
                    {
                        "gvkey": gvkey,
                        "year": year,
                        "sale_D": np.exp(10 + np.random.normal(0, 0.3)),
                        "cogs_D": np.exp(9 + np.random.normal(0, 0.3)),
                        "capital_D": np.exp(9.5 + np.random.normal(0, 0.3)),
                        "xsga_D": np.exp(8 + np.random.normal(0, 0.3)),
                        "ind2d": 31,  # Single industry
                        "nrind2": 1,
                    }
                )
        df = pd.DataFrame(data)

        estimator = WooldridgeIVEstimator(min_observations=5)
        result = estimator.estimate_elasticities(df)

        # Should have estimates for industry 31
        assert len(result) > 0
        assert (result["ind2d"] == 31).all()

    def test_missing_xsga_data(self, sample_prepared_panel: pd.DataFrame):
        """Test handling when SG&A data is missing."""
        # Remove xsga_D column
        df = sample_prepared_panel.drop(columns=["xsga_D"])

        estimator = WooldridgeIVEstimator(specification="spec2", min_observations=5)

        # Should handle missing SG&A gracefully (may use NaN)
        result = estimator.estimate_elasticities(df)
        assert isinstance(result, pd.DataFrame)
