# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Rules

**DO NOT delete old version code.** The numbered scripts (0.0, 0.1, 0.2, etc.) are legacy code that should be preserved. New functionality goes in the package modules (`data/`, `estimators/`, `pipeline/`, etc.), not by replacing old scripts.

## Development Commands

```bash
just test              # Run tests with Python 3.13
just test tests/test_estimators.py::test_wooldridge_iv  # Run single test
just testall           # Run tests for Python 3.10-3.13
just qa                # Run all QA checks (format, lint, type check, test)
just coverage          # Run coverage analysis
just pdb               # Drop into debugger on test failure
just build             # Build the package
uv sync                # Install dependencies
uv sync --extra wrds   # Include WRDS support
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

## Pipeline Architecture (5 Steps)

The `MarkupPipeline` class orchestrates a 5-step research workflow:

1. **Data Download** (`run_download()`) - Fetch Compustat, CPI, PPI from WRDS/FRED/BLS
2. **Data Preparation** (`run_data_preparation()`) - Dedupe, deflate, trim outliers → `panel_data.csv`
3. **Elasticity Estimation** (`run_estimation()`) - Estimate θ by industry-year → `elasticities_{method}.csv`
4. **Markup Calculation** (`run_markup_calculation()`) - `markup = θ / cost_share` → `markups_{method}.csv`
5. **Decomposition** (`run_decomposition()`) - Olley-Pakes decomposition → `decomposition_{method}.csv`

```python
from PyMarkup import MarkupPipeline, PipelineConfig, EstimatorConfig

config = PipelineConfig(
    compustat_path="Input/DLEU/Compustat_annual.csv",
    macro_vars_path="Input/DLEU/macro_vars_new.xlsx",
    estimator=EstimatorConfig(method="wooldridge_iv"),
)
pipeline = MarkupPipeline(config)
results = pipeline.run()
```

## Figure Generation

### Aggregate Markup Plot (`core/figures.py`)
- `plot_aggregate_markup_single_method()`: Time series with DLEU benchmark comparison
- Lines: DLEU benchmark, Replication (all firms), PPI-matched firms
- Output: `Output/figures/Aggregate Markup Comparison - {method} (YYYY-YYYY, Annual).pdf`

### PPI vs Markup Scatter (`core/figures.py`)
- `plot_markup_vs_ppi()`: Industry CAGR of PPI vs CAGR of markups
- Output: `Output/figures/ppi_vs_markup_{method}.pdf`

### Decomposition Plot (`decomposition/visualization.py`)
Dynamic Olley-Pakes decomposition showing counterfactual markup paths:

```python
from PyMarkup import plot_decomposition

plot_decomposition(
    decomposition_df,
    cumulative=True,           # Plot cumulative changes
    base_markup=1.21,          # Starting markup level (e.g., 1980 value)
    save_path="Output/figures/Decomposition.pdf"
)
```

**Lines (DLEU Figure IV style):**
- **Red solid**: Markup (benchmark) = actual aggregate change
- **Blue dashed**: Within = base + cumsum(within component)
- **Black dotted**: Reallocation = base + cumsum(reallocation component)
- **Green dash-dot**: Net Entry = base + cumsum(net_entry component)

When `base_markup` is provided, all 4 lines start at the same baseline, showing "what would markup have been if only this component operated?"

**Decomposition formula:**
```
ΔMarkup(t) = Within + Reallocation + Net_Entry
```
- **Within**: Markup changes within continuing firms at base-period market shares
- **Reallocation**: Market share shifts toward/away from high/low-markup firms
- **Net Entry**: Markup difference between entrants vs exiters

### Plot Styling
All figures use consistent styling via `_apply_decomp_style()` or `_apply_agg_style()`:
- Seaborn whitegrid, 26pt fonts, (15,10) figsize, 3pt linewidth
- Color cycle: `['#252525', '#636363', '#969696', '#bdbdbd']`
