# PyMarkup

A Python toolkit for estimating firm-level markups using production function-based marginal cost recovery.

## Installation

```bash
git clone https://github.com/immortalsRDJ/PyMarkup
cd PyMarkup
uv sync --python 3.10
```

For WRDS data downloads, add the `wrds` extra:

```bash
uv sync --extra wrds
```

## Quick Start

### Option 1: Run Everything in One Go

The easiest way to use PyMarkup is with `run_all()`, which handles the entire pipeline:

```python
from PyMarkup import MarkupPipeline, PipelineConfig

config = PipelineConfig(
    compustat_path="Input/DLEU/Compustat_annual.csv",
    macro_vars_path="Input/DLEU/macro_vars_new.xlsx",
    fred_api_key="your-fred-api-key",      # Or set FRED_API_KEY env var
    data_dir="Input",
)

pipeline = MarkupPipeline(config)
results = pipeline.run_all(
    download=True,           # Download data from WRDS/FRED/BLS
    skip_compustat=True,     # Skip if you already have Compustat data
    generate_figures=True,   # Generate output figures
)
results.save(output_dir="Output/", format="csv")
```

### Option 2: Command Line

```bash
# Full pipeline with config file
pymarkup run-all --config config.yaml

# Skip download step (use existing data)
pymarkup run-all --config config.yaml --skip-download

# Skip only Compustat download (no WRDS credentials needed)
pymarkup run-all --config config.yaml --skip-compustat
```

### Option 3: Step by Step

If you prefer more control, run each step separately:

```python
from PyMarkup import MarkupPipeline, PipelineConfig, EstimatorConfig

config = PipelineConfig(
    compustat_path="Input/DLEU/Compustat_annual.csv",
    macro_vars_path="Input/DLEU/macro_vars_new.xlsx",
    estimator=EstimatorConfig(method="wooldridge_iv"),
)

pipeline = MarkupPipeline(config)
results = pipeline.run()  # Runs data prep -> estimation -> markup calculation
results.save(output_dir="Output/", format="csv")
```

## Configuration

### Setting Up Credentials

1. Copy the example config file:
   ```bash
   cp config.example.yaml config.yaml
   ```

2. Edit `config.yaml` with your credentials:
   ```yaml
   fred_api_key: "your-fred-api-key"
   wrds_username: "your-wrds-username"
   ```

Alternatively, set environment variables: `FRED_API_KEY`, `WRDS_USERNAME`

### Data Requirements

| Data Source | Credentials | How to Get |
|-------------|-------------|------------|
| Compustat (WRDS) | WRDS account | Register at [WRDS](https://wrds-www.wharton.upenn.edu/) |
| CPI (FRED) | FRED API key | Free at [FRED](https://fred.stlouisfed.org/docs/api/api_key.html) |
| PPI (BLS) | None | Public data |
| Macro variables | N/A | Included in repo: `Input/DLEU/macro_vars_new.xlsx` |
| NAICS descriptions | N/A | Included in repo: `Input/Other/NAICS_2D_Description.xlsx` |

## Pipeline Overview

```
Download -> Data Preparation -> Elasticity Estimation -> Markup Calculation -> Figures
```

### 1. Data Download

Downloads raw data from external sources:

```python
from PyMarkup.data import download_compustat, download_cpi, download_ppi, load_config

config = load_config("config.yaml")
download_ppi(config)        # No credentials needed
download_cpi(config)        # Requires FRED API key
download_compustat(config)  # Requires WRDS credentials
```

### 2. Data Preparation

Cleans and prepares the Compustat panel:
- Deduplicates firm-year observations
- Extracts NAICS industry codes
- Deflates monetary values by GDP
- Computes market shares
- Trims outliers

### 3. Elasticity Estimation

Estimates output elasticity of variable inputs (θ) at the industry-year level:

| Method | Class | Use Case |
|--------|-------|----------|
| Wooldridge IV | `WooldridgeIVEstimator` | Main method, addresses endogeneity via IV/2SLS |
| Cost Share | `CostShareEstimator` | Fast baseline, no regression needed |
| ACF | `ACFEstimator` | Robustness, two-stage GMM with control function |

```python
from PyMarkup.estimators import WooldridgeIVEstimator

estimator = WooldridgeIVEstimator(specification="spec2")
elasticities = estimator.estimate_elasticities(panel_data)
```

### 4. Markup Calculation

Computes firm-level markups:

```
markup = θ / cost_share
where cost_share = COGS / (COGS + capital_expense)
```

### 5. Figures

| Figure | Function | Description |
|--------|----------|-------------|
| Aggregate Markup | `plot_aggregate_markup()` | Time series of aggregate markups |
| PPI vs Markup | `plot_markup_vs_ppi()` | Scatter plot with weighted OLS regression |

### 6. Decomposition (Optional)

Dynamic Olley-Pakes decomposition of aggregate markup changes:

```python
from PyMarkup.decomposition import OlleyPakesDecomposition, plot_decomposition

op = OlleyPakesDecomposition()
decomp_results = op.decompose(firm_markups)
plot_decomposition(decomp_results, output_path="Output/decomposition.pdf")
```

## CLI Reference

```bash
# Run full pipeline
pymarkup run-all --config config.yaml [OPTIONS]
  --skip-download      Skip data download step
  --skip-compustat     Skip Compustat download only
  --skip-cpi           Skip CPI download only
  --skip-ppi           Skip PPI download only
  --no-figures         Skip figure generation
  --output PATH        Output directory (default: Output/)

# Run estimation only (requires existing data)
pymarkup estimate --config config.yaml

# Download data only
pymarkup download all --config config.yaml
pymarkup download ppi                        # PPI only, no credentials
pymarkup download cpi --config config.yaml   # CPI only

# Validate input data
pymarkup validate Input/DLEU/Compustat_annual.csv
```

## Project Structure

```
src/PyMarkup/
├── core/              # Data preparation, markup calculation, figures
├── data/              # Data downloaders and loaders
├── estimators/        # WooldridgeIV, CostShare, ACF estimators
├── pipeline/          # MarkupPipeline orchestrator, config
├── decomposition/     # Dynamic Olley-Pakes decomposition
├── io/                # I/O schemas (Pydantic)
└── cli/               # CLI commands

Input/                 # Raw data (not version controlled)
Intermediate/          # Generated datasets, theta estimates
Output/                # Figures and tables
```

## License

MIT License
