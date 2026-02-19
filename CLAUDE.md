# CLAUDE.md

## Important Rules

**DO NOT delete old version code.** The numbered scripts (0.0, 0.1, 0.2, etc.) are legacy code that should be preserved. New functionality goes in the package modules (`data/`, `estimators/`, `pipeline/`, etc.), not by replacing old scripts.

## Development Commands

```bash
just test       # Run tests with Python 3.13
just testall    # Run tests for Python 3.10-3.13
just qa         # Run all QA checks (format, lint, type check, test)
just coverage   # Run coverage analysis
just build      # Build the package
```

## Directory Structure

```
src/PyMarkup/
├── __init__.py              # Public API exports
├── _version.py              # Version
├── 0.0-0.5, 1-4 *.py        # Legacy numbered scripts (DO NOT DELETE)
├── requirements.txt         # Legacy pip requirements (keep for venv compatibility)
├── path_plot_config.py      # Centralized paths and plot config
├── core/                    # Data preparation, markup calculation
├── data/                    # NEW: Data downloaders and loaders
│   ├── config.py            # DataConfig, load_config()
│   ├── downloaders.py       # download_compustat(), download_cpi(), download_ppi()
│   └── loaders.py           # load_compustat(), load_cpi(), load_ppi()
├── estimators/              # WooldridgeIV, CostShare, ACF estimators
├── pipeline/                # MarkupPipeline orchestrator, config
├── io/                      # I/O schemas (Pydantic)
└── cli/                     # CLI commands
```

Data directories (not version controlled):
- `Input/`: Raw data (Compustat, CPI, PPI, macro variables)
- `Intermediate/`: Generated datasets (trimmed panels, theta estimates)
- `Output/`: Final figures and tables

## Configuration

API keys can be configured via `config.yaml` (copy from `config.example.yaml`):

```yaml
fred_api_key: "your-fred-api-key"
wrds_username: "your-wrds-username"
```

Or via environment variables: `FRED_API_KEY`, `WRDS_USERNAME`

## Legacy vs New Pipeline

**Legacy (numbered scripts):** Run via `run_all.py` or individually
- `0.0 Download Compustat.py` - WRDS download
- `0.1 Download CPI.py` - FRED download
- `0.2 PPI Data Preparation.py` - BLS download (uses playwright browser)
- `0.3 theta_estimation.py` - Estimate elasticities
- `0.4 Create Main Datasets.py` - Merge datasets

**New (package modules):** Import and use programmatically
```python
from PyMarkup.data import download_ppi, download_cpi, download_compustat, load_config
config = load_config()
download_ppi(config)       # Uses requests, no browser needed
download_cpi(config)       # Uses fredapi
download_compustat(config) # Uses wrds library, prompts for credentials interactively
```

Output files (all CSV format):
| Downloader | Output Files |
|------------|--------------|
| `download_compustat()` | `Input/DLEU/Compustat_annual.csv`, `Compustat_quarterly.csv` |
| `download_cpi()` | `Input/CPI/CPI_annual.csv`, `CPI_quarterly.csv` |
| `download_ppi()` | `Input/PPI/PPI_annual.csv`, `PPI_quarterly.csv` |

Key improvements in new downloaders:
- **No browser required**: PPI download uses `requests` instead of playwright
- **Interactive credentials**: Compustat prompts for WRDS username/password if not in `.pgpass`
- **Better error handling**: Graceful skips in tests when credentials unavailable

## Estimators

| Method | Class | Use Case |
|--------|-------|----------|
| Wooldridge IV | `WooldridgeIVEstimator` | Main research method, addresses endogeneity |
| Cost Share | `CostShareEstimator` | Fast benchmarking, no estimation needed |
| ACF | `ACFEstimator` | Robustness checks, handles selection bias |

### SG&A Configuration

All estimators support including SG&A as a third input:

| Estimator | Parameter | Options |
|-----------|-----------|---------|
| Wooldridge IV | `specification` | `"spec1"` (no SG&A), `"spec2"` (with SG&A) |
| Cost Share | `include_sga` | `True` / `False` |
| ACF | `include_sga` | `True` / `False` |

Config options: `iv_specification`, `cs_include_sga`, `acf_include_sga`

## Data Requirements

- WRDS credentials for Compustat download
- FRED API key for CPI download
- `Input/DLEU/macro_vars_new.xlsx`: Macro variables (USGDP, usercost)
- `Input/Other/NAICS_2D_Description.xlsx`: Industry code lookup
