"""Shared pytest fixtures for PyMarkup tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_compustat_data() -> pd.DataFrame:
    """
    Create sample Compustat-like data for testing.

    Returns a minimal panel dataset with required columns.
    """
    np.random.seed(42)
    n_firms = 50
    n_years = 10
    years = range(2010, 2010 + n_years)

    data = []
    for gvkey in range(1, n_firms + 1):
        for year in years:
            # Generate realistic-ish financial data
            sale = np.exp(10 + 0.05 * year + np.random.normal(0, 0.5))
            cogs = sale * (0.6 + np.random.normal(0, 0.1))
            ppegt = sale * (0.8 + np.random.normal(0, 0.2))
            xsga = sale * (0.15 + np.random.normal(0, 0.05))

            # Assign to industries (2-digit NAICS)
            naics = int(30 + (gvkey % 20))  # Industries 30-49

            data.append(
                {
                    "gvkey": gvkey,
                    "fyear": year,
                    "year": year,
                    "sale": max(sale, 0),
                    "cogs": max(cogs, 0),
                    "ppegt": max(ppegt, 0),
                    "xsga": max(xsga, 0),
                    "naics": naics,
                    "emp": int(50 + np.random.normal(0, 10)),
                }
            )

    return pd.DataFrame(data)


@pytest.fixture
def sample_macro_vars() -> pd.DataFrame:
    """Create sample macro variables data."""
    years = range(2005, 2025)
    return pd.DataFrame(
        {
            "year": years,
            "USGDP": [15000 + i * 500 for i in range(len(years))],  # Growing GDP
            "usercost": [0.05 + 0.001 * i for i in range(len(years))],  # Slowly increasing
        }
    )


@pytest.fixture
def sample_prepared_panel() -> pd.DataFrame:
    """
    Create a sample prepared panel (post data_preparation).

    Includes deflated variables, industry codes, etc.
    """
    np.random.seed(42)
    n_firms = 30
    n_years = 10
    years = range(2010, 2010 + n_years)

    data = []
    for gvkey in range(1, n_firms + 1):
        for year in years:
            sale_D = np.exp(10 + 0.05 * (year - 2010) + np.random.normal(0, 0.3))
            cogs_D = sale_D * (0.6 + np.random.normal(0, 0.05))
            capital_D = sale_D * (0.8 + np.random.normal(0, 0.1))
            xsga_D = sale_D * (0.15 + np.random.normal(0, 0.03))

            # Industry assignments
            ind2d = int(11 + (gvkey % 15))  # Industries 11-25
            nrind2 = ind2d - 10  # Numeric codes 1-15

            data.append(
                {
                    "gvkey": gvkey,
                    "year": year,
                    "sale_D": max(sale_D, 1),
                    "cogs_D": max(cogs_D, 1),
                    "capital_D": max(capital_D, 1),
                    "xsga_D": max(xsga_D, 0),
                    "ind2d": ind2d,
                    "nrind2": nrind2,
                    "ind3d": ind2d * 10,  # Dummy 3-digit
                    "nrind3": nrind2,
                    "ind4d": ind2d * 100,  # Dummy 4-digit
                    "nrind4": nrind2,
                    "ms2d": 0.01,  # Market share for ACF
                    "ms3d": 0.01,
                    "ms4d": 0.01,
                }
            )

    return pd.DataFrame(data)


@pytest.fixture
def sample_elasticities() -> pd.DataFrame:
    """Create sample elasticity estimates."""
    industries = range(11, 26)
    years = range(2010, 2020)

    data = []
    for ind in industries:
        for year in years:
            data.append(
                {
                    "ind2d": ind,
                    "year": year,
                    "theta_c": 0.6 + np.random.normal(0, 0.05),  # COGS elasticity
                    "theta_k": 0.3 + np.random.normal(0, 0.05),  # Capital elasticity
                }
            )

    return pd.DataFrame(data)


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test data files."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def temp_compustat_file(temp_data_dir: Path, sample_compustat_data: pd.DataFrame) -> Path:
    """Create a temporary Compustat Stata file."""
    file_path = temp_data_dir / "compustat.dta"
    sample_compustat_data.to_stata(file_path, write_index=False)
    return file_path


@pytest.fixture
def temp_macro_vars_file(temp_data_dir: Path, sample_macro_vars: pd.DataFrame) -> Path:
    """Create a temporary macro variables Excel file."""
    file_path = temp_data_dir / "macro_vars.xlsx"
    sample_macro_vars.to_excel(file_path, index=False)
    return file_path


@pytest.fixture
def sample_firm_markups() -> pd.DataFrame:
    """Create sample firm-level markup data."""
    np.random.seed(42)
    n_firms = 20
    years = range(2010, 2020)

    data = []
    for gvkey in range(1, n_firms + 1):
        for year in years:
            markup = 1.2 + np.random.normal(0, 0.1)
            theta_c = 0.65 + np.random.normal(0, 0.05)
            cost_share = 0.55 + np.random.normal(0, 0.05)

            data.append(
                {
                    "gvkey": gvkey,
                    "year": year,
                    "markup": max(markup, 1.0),
                    "theta_c": theta_c,
                    "cost_share": cost_share,
                }
            )

    return pd.DataFrame(data)
