"""Unit tests for data downloading and loading functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from PyMarkup.data import load_cpi, load_ppi


class TestLoadPPI:
    """Tests for load_ppi function."""

    @pytest.fixture
    def sample_ppi_annual(self, temp_data_dir: Path) -> Path:
        """Create sample PPI annual file."""
        ppi_dir = temp_data_dir / "PPI"
        ppi_dir.mkdir(exist_ok=True)

        df = pd.DataFrame({
            "year": [2018, 2019, 2020, 2021],
            "naics_code": ["11", "11", "22", "22"],
            "PPI": [100.0, 105.0, 102.0, 107.0]
        })
        df.to_csv(ppi_dir / "PPI_annual.csv", index=False)
        return ppi_dir

    @pytest.fixture
    def sample_ppi_quarterly(self, temp_data_dir: Path) -> Path:
        """Create sample PPI quarterly file."""
        ppi_dir = temp_data_dir / "PPI"
        ppi_dir.mkdir(exist_ok=True)

        df = pd.DataFrame({
            "year": [2020, 2020, 2020, 2020],
            "quarter": [1, 2, 3, 4],
            "naics_code": ["11", "11", "11", "11"],
            "PPI": [100.0, 101.0, 102.0, 103.0],
            "date": ["2020Q1", "2020Q2", "2020Q3", "2020Q4"]
        })
        df.to_csv(ppi_dir / "PPI_quarterly.csv", index=False)
        return ppi_dir

    def test_load_ppi_annual_success(self, sample_ppi_annual: Path):
        """Test successful loading of annual PPI data."""
        df = load_ppi(sample_ppi_annual, frequency="annual")

        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) == {"year", "naics_code", "PPI"}
        assert len(df) == 4
        assert df["year"].tolist() == [2018, 2019, 2020, 2021]

    def test_load_ppi_quarterly_success(self, sample_ppi_quarterly: Path):
        """Test successful loading of quarterly PPI data."""
        df = load_ppi(sample_ppi_quarterly, frequency="quarterly")

        assert isinstance(df, pd.DataFrame)
        assert "quarter" in df.columns
        assert "date" in df.columns
        assert len(df) == 4

    def test_load_ppi_with_file_path(self, sample_ppi_annual: Path):
        """Test loading PPI when given specific file path."""
        file_path = sample_ppi_annual / "PPI_annual.csv"
        df = load_ppi(file_path)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_load_ppi_file_not_found(self, temp_data_dir: Path):
        """Test error when PPI file doesn't exist."""
        nonexistent = temp_data_dir / "nonexistent"

        with pytest.raises(FileNotFoundError, match="PPI file not found"):
            load_ppi(nonexistent, frequency="annual")

    def test_load_ppi_invalid_frequency(self, sample_ppi_annual: Path):
        """Test error with invalid frequency parameter."""
        with pytest.raises(ValueError, match="frequency must be"):
            load_ppi(sample_ppi_annual, frequency="monthly")

    def test_load_ppi_drops_unnamed_columns(self, temp_data_dir: Path):
        """Test that unnamed index columns are removed."""
        ppi_dir = temp_data_dir / "PPI"
        ppi_dir.mkdir(exist_ok=True)

        # Create file with unnamed index column
        df = pd.DataFrame({
            "Unnamed: 0": [0, 1, 2],
            "year": [2020, 2021, 2022],
            "naics_code": ["11", "11", "11"],
            "PPI": [100.0, 105.0, 110.0]
        })
        df.to_csv(ppi_dir / "PPI_annual.csv", index=False)

        result = load_ppi(ppi_dir, frequency="annual")

        assert "Unnamed: 0" not in result.columns
        assert set(result.columns) == {"year", "naics_code", "PPI"}


class TestLoadCPI:
    """Tests for load_cpi function."""

    @pytest.fixture
    def sample_cpi_annual(self, temp_data_dir: Path) -> Path:
        """Create sample CPI annual file."""
        cpi_dir = temp_data_dir / "CPI"
        cpi_dir.mkdir(exist_ok=True)

        df = pd.DataFrame({
            "year": [2018, 2019, 2020, 2021],
            "CPI": [250.0, 255.0, 258.0, 270.0]
        })
        df.to_csv(cpi_dir / "CPI_annual.csv", index=False)
        return cpi_dir

    @pytest.fixture
    def sample_cpi_quarterly(self, temp_data_dir: Path) -> Path:
        """Create sample CPI quarterly file."""
        cpi_dir = temp_data_dir / "CPI"
        cpi_dir.mkdir(exist_ok=True)

        df = pd.DataFrame({
            "quarter": ["2020Q1", "2020Q2", "2020Q3", "2020Q4"],
            "CPI": [250.0, 252.0, 255.0, 258.0]
        })
        df.to_csv(cpi_dir / "CPI_quarterly.csv", index=False)
        return cpi_dir

    def test_load_cpi_annual_success(self, sample_cpi_annual: Path):
        """Test successful loading of annual CPI data."""
        df = load_cpi(sample_cpi_annual, frequency="annual")

        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) == {"year", "CPI"}
        assert len(df) == 4
        assert df["year"].tolist() == [2018, 2019, 2020, 2021]

    def test_load_cpi_quarterly_success(self, sample_cpi_quarterly: Path):
        """Test successful loading of quarterly CPI data."""
        df = load_cpi(sample_cpi_quarterly, frequency="quarterly")

        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) == {"quarter", "CPI"}
        assert len(df) == 4
        assert all(df["quarter"].str.match(r"\d{4}Q[1-4]"))

    def test_load_cpi_with_file_path(self, sample_cpi_annual: Path):
        """Test loading CPI when given specific file path."""
        file_path = sample_cpi_annual / "CPI_annual.csv"
        df = load_cpi(file_path)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_load_cpi_file_not_found(self, temp_data_dir: Path):
        """Test error when CPI file doesn't exist."""
        nonexistent = temp_data_dir / "nonexistent"

        with pytest.raises(FileNotFoundError, match="CPI file not found"):
            load_cpi(nonexistent, frequency="annual")

    def test_load_cpi_invalid_frequency(self, sample_cpi_annual: Path):
        """Test error with invalid frequency parameter."""
        with pytest.raises(ValueError, match="frequency must be"):
            load_cpi(sample_cpi_annual, frequency="daily")


class TestPPIProcessing:
    """Tests for PPI data processing logic."""

    @pytest.fixture
    def sample_ppi_raw_data(self, temp_data_dir: Path) -> Path:
        """Create sample raw PPI data mimicking BLS format."""
        raw_data = """series_id\tyear\tperiod\tvalue
PCU11----11----\t2020\tM01\t100.0
PCU11----11----\t2020\tM03\t101.5
PCU11----11----\t2020\tM06\t102.0
PCU11----11----\t2020\tM09\t103.5
PCU11----11----\t2020\tM12\t105.0
PCU11----11----\t2021\tM03\t106.0
PCU2211--2211--\t2020\tM03\t98.5
PCU2211--2211--\t2020\tM12\t102.0
PCU331---331---\t2020\tM12\t110.0
PCU-invalid-\t2020\tM12\t95.0
PCU33----33----\t2020\tM02\t100.0"""

        ppi_dir = temp_data_dir / "PPI"
        ppi_dir.mkdir(exist_ok=True)
        file_path = ppi_dir / "pc.data.0.Current.txt"
        file_path.write_text(raw_data)
        return file_path

    def test_ppi_raw_data_format(self, sample_ppi_raw_data: Path):
        """Test that raw PPI data can be read correctly."""
        df = pd.read_csv(sample_ppi_raw_data, sep=r"\s+", dtype=str, engine="python")

        assert "series_id" in df.columns
        assert "year" in df.columns
        assert "period" in df.columns
        assert "value" in df.columns
        assert len(df) > 0

    def test_ppi_naics_extraction(self, sample_ppi_raw_data: Path):
        """Test NAICS code extraction from series_id."""
        df = pd.read_csv(sample_ppi_raw_data, sep=r"\s+", dtype=str, engine="python")

        # Extract NAICS (positions 3-9, remove dashes)
        df["naics_code"] = (
            df["series_id"].str.slice(start=3, stop=9).str.replace("-", "", regex=False)
        )

        # Filter valid NAICS (2-6 digits)
        valid_naics = df[df["naics_code"].str.match(r"^\d{2,6}$")]

        assert len(valid_naics) > 0
        assert all(valid_naics["naics_code"].str.len() >= 2)
        assert all(valid_naics["naics_code"].str.len() <= 6)
        assert "invalid" not in valid_naics["naics_code"].values

    def test_ppi_quarter_end_filtering(self, sample_ppi_raw_data: Path):
        """Test that only quarter-end months are retained."""
        df = pd.read_csv(sample_ppi_raw_data, sep=r"\s+", dtype=str, engine="python")

        valid_months = ["M03", "M06", "M09", "M12"]
        df_filtered = df[df["period"].isin(valid_months)]

        assert set(df_filtered["period"]) <= set(valid_months)
        assert "M01" not in df_filtered["period"].values
        assert "M02" not in df_filtered["period"].values

    def test_ppi_quarter_mapping(self, sample_ppi_raw_data: Path):
        """Test month to quarter mapping."""
        month_to_q = {"M03": 1, "M06": 2, "M09": 3, "M12": 4}

        df = pd.read_csv(sample_ppi_raw_data, sep=r"\s+", dtype=str, engine="python")
        df = df[df["period"].isin(month_to_q.keys())]
        df["quarter"] = df["period"].map(month_to_q)

        assert set(df["quarter"]) == {1, 2, 3, 4}
        assert df[df["period"] == "M03"]["quarter"].iloc[0] == 1
        assert df[df["period"] == "M12"]["quarter"].iloc[0] == 4


class TestCPIProcessing:
    """Tests for CPI data processing logic."""

    def test_cpi_annual_january_only(self, temp_data_dir: Path):
        """Test that annual CPI contains only January data."""
        # Create sample monthly data
        dates = pd.date_range(start="2020-01-01", end="2020-12-01", freq="MS")
        df = pd.DataFrame({
            "Date": dates,
            "CPI": np.linspace(250, 260, len(dates))
        })
        df["year"] = df["Date"].dt.year
        df["month"] = df["Date"].dt.month

        # Filter to January only (as the script does)
        df_annual = df[df["month"] == 1][["year", "CPI"]]

        assert len(df_annual) == 1
        assert df_annual["year"].iloc[0] == 2020

    def test_cpi_quarterly_format(self):
        """Test quarterly CPI format (YYYYQN)."""
        # Create sample data
        df = pd.DataFrame({
            "Date": pd.date_range(start="2020-01-01", end="2020-10-01", freq="QS"),
            "CPI": [250.0, 252.0, 255.0, 258.0]
        })
        df["year"] = df["Date"].dt.year.astype(str)
        df["month"] = df["Date"].dt.month

        # Map to quarters
        df["quarter"] = None
        df.loc[df["month"] == 1, "quarter"] = df["year"] + "Q1"
        df.loc[df["month"] == 4, "quarter"] = df["year"] + "Q2"
        df.loc[df["month"] == 7, "quarter"] = df["year"] + "Q3"
        df.loc[df["month"] == 10, "quarter"] = df["year"] + "Q4"

        df_quarterly = df.dropna(subset=["quarter"])

        assert all(df_quarterly["quarter"].str.match(r"^\d{4}Q[1-4]$"))
        assert "2020Q1" in df_quarterly["quarter"].values


class TestDownloadCompustat:
    """Tests for Compustat download function."""

    @pytest.fixture
    def mock_wrds_connection(self) -> Mock:
        """Create mock WRDS connection."""
        mock_conn = Mock()

        # Mock NAICS data
        naics_df = pd.DataFrame({
            "gvkey": [1, 2, 3],
            "naics": ["3111", "3331", "2211"]
        })

        # Mock annual data
        annual_df = pd.DataFrame({
            "gvkey": [1, 2, 3],
            "fyear": [2020, 2020, 2020],
            "sale": [1000, 2000, 500],
            "cogs": [600, 1200, 300],
            "ppegt": [500, 1000, 250],
            "xsga": [100, 200, 50],
            "consol": ["C", "C", "C"],
            "popsrc": ["D", "D", "D"],
            "datafmt": ["STD", "STD", "STD"],
            "conm": ["Co A", "Co B", "Co C"],
            "indfmt": ["INDL", "INDL", "INDL"],
            "xlr": [50, 100, 25],
            "xrd": [10, 20, 5],
            "xad": [5, 10, 3],
            "dvt": [20, 40, 10],
            "intan": [100, 200, 50],
            "mkvalt": [2000, 4000, 1000],
            "tie": [5.0, 6.0, 4.0],
            "emp": [100, 200, 50],
            "ppent": [450, 900, 230]
        })

        # Mock quarterly data
        quarterly_df = pd.DataFrame({
            "gvkey": [1, 2],
            "fyearq": [2020, 2020],
            "fqtr": [1, 1],
            "saleq": [250, 500],
            "cogsq": [150, 300],
            "ppegtq": [505, 1010],
            "xsgaq": [25, 50],
            "consol": ["C", "C"],
            "popsrc": ["D", "D"],
            "datafmt": ["STD", "STD"],
            "conm": ["Co A", "Co B"],
            "indfmt": ["INDL", "INDL"]
        })

        def raw_sql_side_effect(query):
            if "comp.company" in query:
                return naics_df
            elif "comp.funda" in query:
                return annual_df
            elif "comp.fundq" in query:
                return quarterly_df
            return pd.DataFrame()

        mock_conn.raw_sql.side_effect = raw_sql_side_effect
        mock_conn.close = Mock()
        return mock_conn

    @patch("PyMarkup.data.downloaders.wrds")
    def test_download_compustat_success(
        self,
        mock_wrds_module: Mock,
        mock_wrds_connection: Mock,
        temp_data_dir: Path
    ):
        """Test successful Compustat download."""
        from PyMarkup.data import download_compustat

        mock_wrds_module.Connection.return_value = mock_wrds_connection

        output_dir = temp_data_dir / "DLEU"
        download_compustat(output_dir)

        # Check that files were created
        assert (output_dir / "Compustat_annual.dta").exists()
        assert (output_dir / "Compustat_quarterly.dta").exists()

        # Verify data
        df_annual = pd.read_stata(output_dir / "Compustat_annual.dta")
        assert "gvkey" in df_annual.columns
        assert "naics" in df_annual.columns
        assert len(df_annual) > 0

    @patch("PyMarkup.data.downloaders.wrds", None)
    def test_download_compustat_no_wrds_package(self, temp_data_dir: Path):
        """Test error when wrds package not installed."""
        from PyMarkup.data import download_compustat

        with pytest.raises(ImportError, match="wrds package required"):
            download_compustat(temp_data_dir / "DLEU")


class TestDownloadCPI:
    """Tests for CPI download function."""

    @patch("PyMarkup.data.downloaders.Fred")
    def test_download_cpi_success(self, mock_fred_class: Mock, temp_data_dir: Path):
        """Test successful CPI download."""
        from PyMarkup.data import download_cpi

        # Mock FRED API response
        dates = pd.date_range(start="2020-01-01", end="2021-12-01", freq="MS")
        mock_series = pd.Series(np.linspace(250, 280, len(dates)), index=dates)
        mock_series.name = "CPI"

        mock_fred_instance = Mock()
        mock_fred_instance.get_series.return_value = mock_series
        mock_fred_class.return_value = mock_fred_instance

        output_dir = temp_data_dir / "CPI"
        download_cpi(output_dir, fred_api_key="test_key")

        # Check files created
        assert (output_dir / "CPI_annual.csv").exists()
        assert (output_dir / "CPI_quarterly.csv").exists()

        # Verify annual data
        df_annual = pd.read_csv(output_dir / "CPI_annual.csv")
        assert set(df_annual.columns) == {"year", "CPI"}
        assert len(df_annual) > 0

        # Verify quarterly data
        df_quarterly = pd.read_csv(output_dir / "CPI_quarterly.csv")
        assert set(df_quarterly.columns) == {"quarter", "CPI"}
        assert all(df_quarterly["quarter"].str.match(r"\d{4}Q[1-4]"))

    @patch("PyMarkup.data.downloaders.Fred", None)
    def test_download_cpi_no_fredapi_package(self, temp_data_dir: Path):
        """Test error when fredapi package not installed."""
        from PyMarkup.data import download_cpi

        with pytest.raises(ImportError, match="fredapi package required"):
            download_cpi(temp_data_dir / "CPI", fred_api_key="test")


class TestDataIntegration:
    """Integration tests for data loading consistency."""

    def test_all_data_has_year_column(self, temp_data_dir: Path):
        """Test that all annual datasets have year column for merging."""
        # Create sample data files
        cpi_dir = temp_data_dir / "CPI"
        ppi_dir = temp_data_dir / "PPI"
        cpi_dir.mkdir(exist_ok=True)
        ppi_dir.mkdir(exist_ok=True)

        pd.DataFrame({"year": [2020], "CPI": [250.0]}).to_csv(
            cpi_dir / "CPI_annual.csv", index=False
        )
        pd.DataFrame({"year": [2020], "naics_code": ["11"], "PPI": [100.0]}).to_csv(
            ppi_dir / "PPI_annual.csv", index=False
        )

        # Load and check
        cpi = load_cpi(cpi_dir, frequency="annual")
        ppi = load_ppi(ppi_dir, frequency="annual")

        assert "year" in cpi.columns
        assert "year" in ppi.columns
        assert cpi["year"].dtype in [np.int64, np.int32]
        assert ppi["year"].dtype in [np.int64, np.int32]

    def test_quarterly_data_format_consistency(self, temp_data_dir: Path):
        """Test that quarterly datasets have consistent formats."""
        cpi_dir = temp_data_dir / "CPI"
        ppi_dir = temp_data_dir / "PPI"
        cpi_dir.mkdir(exist_ok=True)
        ppi_dir.mkdir(exist_ok=True)

        # Create quarterly files
        pd.DataFrame({"quarter": ["2020Q1"], "CPI": [250.0]}).to_csv(
            cpi_dir / "CPI_quarterly.csv", index=False
        )
        pd.DataFrame({
            "year": [2020],
            "quarter": [1],
            "naics_code": ["11"],
            "PPI": [100.0],
            "date": ["2020Q1"]
        }).to_csv(ppi_dir / "PPI_quarterly.csv", index=False)

        cpi = load_cpi(cpi_dir, frequency="quarterly")
        ppi = load_ppi(ppi_dir, frequency="quarterly")

        # Both should have quarter information
        assert "quarter" in cpi.columns or "quarter" in ppi.columns
