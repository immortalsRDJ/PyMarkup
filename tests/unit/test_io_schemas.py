"""Unit tests for IO schemas (InputData and MarkupResults)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from PyMarkup.io import InputData, MarkupResults


class TestInputData:
    """Tests for InputData schema."""

    def test_from_dataframe_success(self, sample_compustat_data: pd.DataFrame):
        """Test creating InputData from valid DataFrame."""
        input_data = InputData.from_dataframe(sample_compustat_data)

        assert isinstance(input_data, InputData)
        assert len(input_data.gvkey) > 0
        assert len(input_data.sale) > 0

    def test_from_dataframe_missing_columns(self):
        """Test error when required columns are missing."""
        df = pd.DataFrame({"gvkey": [1, 2], "sale": [100, 200]})  # Missing cogs, ppegt, naics

        with pytest.raises(ValueError, match="Missing required columns"):
            InputData.from_dataframe(df)

    def test_from_compustat_success(self, temp_compustat_file: Path):
        """Test loading from Compustat Stata file."""
        input_data = InputData.from_compustat(temp_compustat_file)

        assert isinstance(input_data, InputData)
        assert len(input_data.gvkey) > 0

    def test_validate_year_range_invalid(self):
        """Test year validation rejects invalid years."""
        df = pd.DataFrame(
            {
                "gvkey": [1, 2],
                "year": [1800, 1900],  # Too old
                "sale": [100, 200],
                "cogs": [60, 120],
                "ppegt": [50, 100],
                "naics": [30, 31],
            }
        )

        with pytest.raises(ValidationError, match="Year outside valid range"):
            InputData.from_dataframe(df)

    def test_validate_positive_values(self):
        """Test that negative financial values are rejected."""
        df = pd.DataFrame(
            {
                "gvkey": [1, 2],
                "year": [2020, 2021],
                "sale": [-100, 200],  # Negative sale
                "cogs": [60, 120],
                "ppegt": [50, 100],
                "naics": [30, 31],
            }
        )

        with pytest.raises(ValidationError, match="Found negative values"):
            InputData.from_dataframe(df)

    def test_to_dataframe(self, sample_compustat_data: pd.DataFrame):
        """Test conversion back to DataFrame."""
        input_data = InputData.from_dataframe(sample_compustat_data)
        df = input_data.to_dataframe()

        # Check it's a DataFrame
        assert isinstance(df, pd.DataFrame)

        # Check columns exist
        required_cols = {"gvkey", "year", "sale", "cogs", "ppegt", "naics"}
        assert required_cols.issubset(df.columns)

        # Check data is preserved
        assert len(df) == len(sample_compustat_data)

    def test_optional_fields(self):
        """Test that optional fields work correctly."""
        df = pd.DataFrame(
            {
                "gvkey": [1, 2],
                "year": [2020, 2021],
                "sale": [100, 200],
                "cogs": [60, 120],
                "ppegt": [50, 100],
                "naics": [30, 31],
                "xsga": [10, 20],  # Optional
                "emp": [50, 100],  # Optional
            }
        )

        input_data = InputData.from_dataframe(df)

        # Optional fields should be included
        assert input_data.xsga is not None
        assert input_data.emp is not None

        # They should be in to_dataframe output
        df_out = input_data.to_dataframe()
        assert "xsga" in df_out.columns
        assert "emp" in df_out.columns

    def test_fyear_renamed_to_year(self):
        """Test that 'fyear' column is properly renamed to 'year'."""
        df = pd.DataFrame(
            {
                "gvkey": [1, 2],
                "fyear": [2020, 2021],  # Use 'fyear' instead of 'year'
                "sale": [100, 200],
                "cogs": [60, 120],
                "ppegt": [50, 100],
                "naics": [30, 31],
            }
        )

        input_data = InputData.from_dataframe(df)
        assert len(input_data.year) == 2


class TestMarkupResults:
    """Tests for MarkupResults schema."""

    def test_from_pipeline(self, sample_firm_markups: pd.DataFrame, sample_elasticities: pd.DataFrame):
        """Test creating MarkupResults from pipeline outputs."""
        markups = {"wooldridge_iv": sample_firm_markups}
        elasticities = {"wooldridge_iv": sample_elasticities}

        # Create minimal config
        config = {"method": "wooldridge_iv"}

        results = MarkupResults.from_pipeline(markups, elasticities, config)

        assert isinstance(results, MarkupResults)
        assert "wooldridge_iv" in results.firm_markups
        assert "wooldridge_iv" in results.elasticities
        assert "methods" in results.metadata
        assert results.metadata["methods"] == ["wooldridge_iv"]

    def test_save_csv(
        self,
        temp_data_dir: Path,
        sample_firm_markups: pd.DataFrame,
        sample_elasticities: pd.DataFrame,
    ):
        """Test saving results to CSV."""
        markups = {"wooldridge_iv": sample_firm_markups}
        elasticities = {"wooldridge_iv": sample_elasticities}
        config = {"method": "wooldridge_iv"}

        results = MarkupResults.from_pipeline(markups, elasticities, config)

        output_dir = temp_data_dir / "output"
        results.save(output_dir, format="csv")

        # Check files were created
        assert (output_dir / "markups_wooldridge_iv.csv").exists()
        assert (output_dir / "elasticities_wooldridge_iv.csv").exists()

        # Check files can be read back
        df_markups = pd.read_csv(output_dir / "markups_wooldridge_iv.csv")
        assert len(df_markups) == len(sample_firm_markups)

    def test_save_parquet(
        self,
        temp_data_dir: Path,
        sample_firm_markups: pd.DataFrame,
        sample_elasticities: pd.DataFrame,
    ):
        """Test saving results to Parquet."""
        markups = {"wooldridge_iv": sample_firm_markups}
        elasticities = {"wooldridge_iv": sample_elasticities}
        config = {"method": "wooldridge_iv"}

        results = MarkupResults.from_pipeline(markups, elasticities, config)

        output_dir = temp_data_dir / "output"
        results.save(output_dir, format="parquet")

        # Check files were created
        assert (output_dir / "markups_wooldridge_iv.parquet").exists()
        assert (output_dir / "elasticities_wooldridge_iv.parquet").exists()

    def test_compare_methods(self, sample_firm_markups: pd.DataFrame, sample_elasticities: pd.DataFrame):
        """Test comparing multiple estimation methods."""
        # Create results from two methods
        markups = {
            "wooldridge_iv": sample_firm_markups,
            "cost_share": sample_firm_markups.copy(),  # Reuse same data for simplicity
        }
        elasticities = {
            "wooldridge_iv": sample_elasticities,
            "cost_share": sample_elasticities.copy(),
        }
        config = {"method": "all"}

        results = MarkupResults.from_pipeline(markups, elasticities, config)
        comparison = results.compare_methods()

        # Check comparison has both methods
        assert isinstance(comparison, pd.DataFrame)
        assert len(comparison) == 2
        assert set(comparison["method"]) == {"wooldridge_iv", "cost_share"}

        # Check it has expected columns
        expected_cols = {"method", "n_firms", "n_firm_years", "mean_markup", "median_markup", "std_markup"}
        assert expected_cols.issubset(comparison.columns)

    def test_plot_aggregate(
        self,
        temp_data_dir: Path,
        sample_firm_markups: pd.DataFrame,
        sample_elasticities: pd.DataFrame,
    ):
        """Test plotting aggregate markup time series."""
        markups = {"wooldridge_iv": sample_firm_markups}
        elasticities = {"wooldridge_iv": sample_elasticities}
        config = {"method": "wooldridge_iv"}

        results = MarkupResults.from_pipeline(markups, elasticities, config)

        # Test plot without saving
        fig = results.plot_aggregate()
        assert fig is not None

        # Test plot with saving
        save_path = temp_data_dir / "test_plot.png"
        fig = results.plot_aggregate(save_path=save_path)
        assert save_path.exists()

    def test_plot_aggregate_specific_method(
        self,
        sample_firm_markups: pd.DataFrame,
        sample_elasticities: pd.DataFrame,
    ):
        """Test plotting specific method only."""
        markups = {
            "wooldridge_iv": sample_firm_markups,
            "cost_share": sample_firm_markups.copy(),
        }
        elasticities = {
            "wooldridge_iv": sample_elasticities,
            "cost_share": sample_elasticities.copy(),
        }
        config = {"method": "all"}

        results = MarkupResults.from_pipeline(markups, elasticities, config)

        # Plot only one method
        fig = results.plot_aggregate(method="wooldridge_iv")
        assert fig is not None
