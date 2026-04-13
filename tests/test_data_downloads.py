"""Tests for data downloading module.

Run with:
    uv run pytest tests/test_data_downloads.py -v

Or run individual tests:
    uv run pytest tests/test_data_downloads.py::test_download_ppi -v
    uv run pytest tests/test_data_downloads.py::test_download_cpi -v
    uv run pytest tests/test_data_downloads.py::test_download_compustat -v
"""

import logging
from pathlib import Path

import pandas as pd
import pytest

from PyMarkup.data import (
    DataConfig,
    download_cpi,
    download_ppi,
    load_config,
    load_cpi,
    load_ppi,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def config() -> DataConfig:
    """Load config from config.yaml or environment."""
    return load_config()


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory for tests."""
    return tmp_path / "test_data"


# =============================================================================
# PPI Tests (no API key required)
# =============================================================================


class TestPPIDownload:
    """Tests for PPI download functionality."""

    def test_download_ppi(self, config: DataConfig, temp_output_dir: Path) -> None:
        """Test PPI download from BLS."""
        annual_path, quarterly_path = download_ppi(config, output_dir=temp_output_dir)

        # Check files exist
        assert annual_path.exists(), f"Annual PPI file not created: {annual_path}"
        assert quarterly_path.exists(), f"Quarterly PPI file not created: {quarterly_path}"

        # Check file contents
        df_annual = pd.read_csv(annual_path)
        df_quarterly = pd.read_csv(quarterly_path)

        # Validate annual data
        assert len(df_annual) > 0, "Annual PPI data is empty"
        assert "year" in df_annual.columns, "Annual PPI missing 'year' column"
        assert "naics_code" in df_annual.columns, "Annual PPI missing 'naics_code' column"
        assert "PPI" in df_annual.columns, "Annual PPI missing 'PPI' column"

        # Validate quarterly data
        assert len(df_quarterly) > 0, "Quarterly PPI data is empty"
        assert "quarter" in df_quarterly.columns, "Quarterly PPI missing 'quarter' column"

        logger.info(f"PPI Annual: {len(df_annual)} rows, years {df_annual['year'].min()}-{df_annual['year'].max()}")
        logger.info(f"PPI Quarterly: {len(df_quarterly)} rows")

    def test_load_ppi_annual(self, config: DataConfig) -> None:
        """Test loading existing PPI annual data."""
        ppi_path = config.data_dir / "PPI" / "PPI_annual.csv"
        if not ppi_path.exists():
            pytest.skip(f"PPI annual file not found: {ppi_path}")

        df = load_ppi(ppi_path, frequency="annual")
        assert len(df) > 0
        assert {"year", "naics_code", "PPI"}.issubset(df.columns)

    def test_load_ppi_quarterly(self, config: DataConfig) -> None:
        """Test loading existing PPI quarterly data."""
        ppi_path = config.data_dir / "PPI" / "PPI_quarterly.csv"
        if not ppi_path.exists():
            pytest.skip(f"PPI quarterly file not found: {ppi_path}")

        df = load_ppi(ppi_path, frequency="quarterly")
        assert len(df) > 0
        assert {"year", "quarter", "naics_code", "PPI"}.issubset(df.columns)


# =============================================================================
# CPI Tests (requires FRED API key)
# =============================================================================


class TestCPIDownload:
    """Tests for CPI download functionality."""

    def test_download_cpi(self, config: DataConfig, temp_output_dir: Path) -> None:
        """Test CPI download from FRED."""
        if not config.fred_api_key:
            pytest.skip("FRED API key not configured - set fred_api_key in config.yaml")

        annual_path, quarterly_path = download_cpi(config, output_dir=temp_output_dir)

        # Check files exist
        assert annual_path.exists(), f"Annual CPI file not created: {annual_path}"
        assert quarterly_path.exists(), f"Quarterly CPI file not created: {quarterly_path}"

        # Check file contents
        df_annual = pd.read_csv(annual_path)
        df_quarterly = pd.read_csv(quarterly_path)

        # Validate annual data
        assert len(df_annual) > 0, "Annual CPI data is empty"
        assert "year" in df_annual.columns, "Annual CPI missing 'year' column"
        assert "CPI" in df_annual.columns, "Annual CPI missing 'CPI' column"

        # Validate quarterly data
        assert len(df_quarterly) > 0, "Quarterly CPI data is empty"
        assert "quarter" in df_quarterly.columns, "Quarterly CPI missing 'quarter' column"
        assert "CPI" in df_quarterly.columns, "Quarterly CPI missing 'CPI' column"

        logger.info(f"CPI Annual: {len(df_annual)} rows, years {df_annual['year'].min()}-{df_annual['year'].max()}")
        logger.info(f"CPI Quarterly: {len(df_quarterly)} rows")

    def test_load_cpi_annual(self, config: DataConfig) -> None:
        """Test loading existing CPI annual data."""
        cpi_path = config.data_dir / "CPI" / "CPI_annual.csv"
        if not cpi_path.exists():
            pytest.skip(f"CPI annual file not found: {cpi_path}")

        df = load_cpi(cpi_path, frequency="annual")
        assert len(df) > 0
        assert {"year", "CPI"}.issubset(df.columns)

    def test_load_cpi_quarterly(self, config: DataConfig) -> None:
        """Test loading existing CPI quarterly data."""
        cpi_path = config.data_dir / "CPI" / "CPI_quarterly.csv"
        if not cpi_path.exists():
            pytest.skip(f"CPI quarterly file not found: {cpi_path}")

        df = load_cpi(cpi_path, frequency="quarterly")
        assert len(df) > 0
        assert {"quarter", "CPI"}.issubset(df.columns)


# =============================================================================
# Compustat Tests (requires WRDS credentials)
# =============================================================================


class TestCompustatDownload:
    """Tests for Compustat download functionality."""

    def test_download_compustat(self, config: DataConfig, temp_output_dir: Path) -> None:
        """Test Compustat download from WRDS.

        This test requires:
        1. wrds package installed (uv sync --extra wrds)
        2. WRDS credentials configured (wrds_username in config.yaml or .pgpass file)
        3. Interactive terminal for password input (skip in CI)
        """
        import os
        import sys

        try:
            import wrds
        except ImportError:
            pytest.skip("wrds package not installed - install with: uv sync --extra wrds")

        # Skip if no WRDS username configured and no .pgpass file
        pgpass_path = Path.home() / ".pgpass"
        if not config.wrds_username and not pgpass_path.exists():
            pytest.skip("WRDS credentials not configured - set wrds_username in config.yaml or create .pgpass file")

        # Skip if running in non-interactive environment (CI, pytest without -s)
        if not sys.stdin.isatty():
            pytest.skip("Skipping interactive WRDS test - run with 'pytest -s' for interactive mode")

        from PyMarkup.data import download_compustat

        try:
            annual_path, quarterly_path = download_compustat(config, output_dir=temp_output_dir)
        except (EOFError, OSError) as e:
            pytest.skip(f"Interactive input not available: {e}")
        except Exception as e:
            if "WRDS" in str(e) or "authentication" in str(e).lower() or "SSL" in str(e):
                pytest.skip(f"WRDS connection failed: {e}")
            raise

        # Check files exist
        assert annual_path.exists(), f"Annual Compustat file not created: {annual_path}"
        assert quarterly_path.exists(), f"Quarterly Compustat file not created: {quarterly_path}"

        # Check file contents
        df_annual = pd.read_stata(annual_path)
        df_quarterly = pd.read_stata(quarterly_path)

        # Validate annual data
        assert len(df_annual) > 0, "Annual Compustat data is empty"
        assert "gvkey" in df_annual.columns, "Annual Compustat missing 'gvkey' column"
        assert "fyear" in df_annual.columns, "Annual Compustat missing 'fyear' column"

        # Validate quarterly data
        assert len(df_quarterly) > 0, "Quarterly Compustat data is empty"
        assert "gvkey" in df_quarterly.columns, "Quarterly Compustat missing 'gvkey' column"

        logger.info(f"Compustat Annual: {len(df_annual)} rows")
        logger.info(f"Compustat Quarterly: {len(df_quarterly)} rows")


# =============================================================================
# Config Tests
# =============================================================================


class TestConfig:
    """Tests for configuration loading."""

    def test_load_config(self) -> None:
        """Test config loading."""
        config = load_config()
        assert isinstance(config, DataConfig)
        assert config.data_dir is not None
        assert config.ppi_url.startswith("https://")

    def test_config_validation_fred(self) -> None:
        """Test config validation for FRED API key."""
        config = DataConfig(fred_api_key="")
        with pytest.raises(ValueError, match="FRED API key required"):
            config.validate(require_fred=True)

    def test_config_validation_wrds(self) -> None:
        """Test config validation for WRDS username."""
        config = DataConfig(wrds_username="")
        with pytest.raises(ValueError, match="WRDS username required"):
            config.validate(require_wrds=True)


# =============================================================================
# Run as script
# =============================================================================

if __name__ == "__main__":
    """Run tests directly with python."""
    import sys

    # Simple test runner when run directly
    print("=" * 60)
    print("PyMarkup Data Module Tests")
    print("=" * 60)

    config = load_config()
    print(f"\nConfig loaded:")
    print(f"  - Data dir: {config.data_dir}")
    print(f"  - FRED API key: {'configured' if config.fred_api_key else 'NOT SET'}")
    print(f"  - WRDS username: {config.wrds_username or 'NOT SET'}")

    print("\n" + "=" * 60)
    print("Testing PPI Download (no API key required)")
    print("=" * 60)
    try:
        annual, quarterly = download_ppi(config)
        print(f"SUCCESS: PPI downloaded to {annual.parent}")
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

    if config.fred_api_key:
        print("\n" + "=" * 60)
        print("Testing CPI Download (FRED API)")
        print("=" * 60)
        try:
            annual, quarterly = download_cpi(config)
            print(f"SUCCESS: CPI downloaded to {annual.parent}")
        except Exception as e:
            print(f"FAILED: {e}")
    else:
        print("\n[SKIPPED] CPI test - no FRED API key configured")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
