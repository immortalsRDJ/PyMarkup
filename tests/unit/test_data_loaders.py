"""Unit tests for data loading functions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from PyMarkup.data.loaders import load_compustat, load_macro_vars


class TestLoadCompustat:
    """Tests for load_compustat function."""

    def test_load_compustat_success(self, temp_compustat_file: Path):
        """Test successful loading of Compustat data."""
        df = load_compustat(temp_compustat_file)

        # Check it returns a DataFrame
        assert isinstance(df, pd.DataFrame)

        # Check required columns exist
        required_cols = {"gvkey", "sale", "cogs", "ppegt", "naics"}
        assert required_cols.issubset(df.columns)

        # Check data is not empty
        assert len(df) > 0

    def test_load_compustat_file_not_found(self, temp_data_dir: Path):
        """Test error handling when file doesn't exist."""
        nonexistent_file = temp_data_dir / "does_not_exist.dta"

        with pytest.raises(FileNotFoundError, match="Compustat file not found"):
            load_compustat(nonexistent_file)

    def test_load_compustat_data_types(self, temp_compustat_file: Path):
        """Test that loaded data has correct types."""
        df = load_compustat(temp_compustat_file)

        # Numeric columns should be numeric
        assert pd.api.types.is_numeric_dtype(df["sale"])
        assert pd.api.types.is_numeric_dtype(df["cogs"])
        assert pd.api.types.is_numeric_dtype(df["ppegt"])


class TestLoadMacroVars:
    """Tests for load_macro_vars function."""

    def test_load_macro_vars_success(self, temp_macro_vars_file: Path):
        """Test successful loading of macro variables."""
        df = load_macro_vars(temp_macro_vars_file)

        # Check it returns a DataFrame
        assert isinstance(df, pd.DataFrame)

        # Check required columns
        required_cols = {"year", "USGDP", "usercost"}
        assert set(df.columns) == required_cols

        # Check data is not empty
        assert len(df) > 0

    def test_load_macro_vars_file_not_found(self, temp_data_dir: Path):
        """Test error handling when file doesn't exist."""
        nonexistent_file = temp_data_dir / "does_not_exist.xlsx"

        with pytest.raises(FileNotFoundError, match="Macro variable file not found"):
            load_macro_vars(nonexistent_file)

    def test_load_macro_vars_missing_columns(self, temp_data_dir: Path):
        """Test error when required columns are missing."""
        # Create Excel file with wrong columns
        bad_file = temp_data_dir / "bad_macro.xlsx"
        df = pd.DataFrame({"year": [2020, 2021], "GDP": [1000, 1100]})  # Wrong column name
        df.to_excel(bad_file, index=False)

        with pytest.raises(ValueError, match="must contain columns"):
            load_macro_vars(bad_file)

    def test_load_macro_vars_data_types(self, temp_macro_vars_file: Path):
        """Test that loaded data has correct types."""
        df = load_macro_vars(temp_macro_vars_file)

        # Year should be numeric
        assert pd.api.types.is_numeric_dtype(df["year"])
        # USGDP should be numeric
        assert pd.api.types.is_numeric_dtype(df["USGDP"])
        # usercost should be numeric
        assert pd.api.types.is_numeric_dtype(df["usercost"])

    def test_load_macro_vars_strips_whitespace(self, temp_data_dir: Path):
        """Test that column names are properly stripped."""
        # Create Excel file with spaces in column names
        file_with_spaces = temp_data_dir / "macro_spaces.xlsx"
        df = pd.DataFrame(
            {
                "year  ": [2020, 2021],  # Extra spaces
                " USGDP": [1000, 1100],
                "usercost ": [0.05, 0.06],
            }
        )
        df.to_excel(file_with_spaces, index=False)

        # Should load successfully and strip spaces
        result = load_macro_vars(file_with_spaces)
        assert set(result.columns) == {"year", "USGDP", "usercost"}
