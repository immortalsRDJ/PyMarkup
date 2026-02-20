# PyMarkup

A Python toolkit for estimating firm-level markups using production function-based marginal cost recovery.

## Installation

```bash
git clone https://github.com/immortalsRDJ/PyMarkup
cd PyMarkup
uv sync
```

For WRDS data downloads, add the `wrds` extra:

```bash
uv sync --extra wrds
```

## Quick Start

### Option 1: Command Line (Recommended)

```bash
# 1. Set up config file
cp config.example.yaml config.yaml
# Edit config.yaml with your API keys and settings

# 2. Run the full pipeline
uv run pymarkup run-all --config config.yaml

# Or skip data download if you already have the data
uv run pymarkup run-all --config config.yaml --skip-download
```

### Option 2: Python Script

```python
from PyMarkup import MarkupPipeline, PipelineConfig, EstimatorConfig

config = PipelineConfig(
    compustat_path="Input/DLEU/Compustat_annual.csv",
    macro_vars_path="Input/DLEU/macro_vars_new.xlsx",
    estimator=EstimatorConfig(method="wooldridge_iv"),
)

pipeline = MarkupPipeline(config)
results = pipeline.run()
results.save(output_dir="Output/", format="csv")
```

## Command Line Reference

### Full Pipeline

```bash
# Run everything (download + estimate + figures)
uv run pymarkup run-all --config config.yaml

# Skip all downloads (use existing data)
uv run pymarkup run-all --config config.yaml --skip-download

# Skip only Compustat download (no WRDS credentials needed)
uv run pymarkup run-all --config config.yaml --skip-compustat

# Skip figure generation
uv run pymarkup run-all --config config.yaml --no-figures

# Verbose output for debugging
uv run pymarkup run-all --config config.yaml -v
```

### Individual Commands

```bash
# Download data only
uv run pymarkup download ppi                        # PPI (no credentials needed)
uv run pymarkup download cpi --config config.yaml   # CPI (needs FRED API key)
uv run pymarkup download all --config config.yaml   # All datasets

# Run estimation only (requires existing data)
uv run pymarkup estimate --config config.yaml

# Validate input data
uv run pymarkup validate Input/DLEU/Compustat_annual.csv

# Check version
uv run pymarkup version
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

#### SG&A Configuration

All three estimators support including SG&A (Selling, General & Administrative expenses) as a third input in the production function:

| Estimator | Parameter | Options | Default |
|-----------|-----------|---------|---------|
| Wooldridge IV | `specification` | `"spec1"` (COGS+K), `"spec2"` (COGS+K+SG&A) | `"spec2"` |
| Cost Share | `include_sga` | `True`, `False` | `False` |
| ACF | `include_sga` | `True`, `False` | `False` |

```python
from PyMarkup.estimators import ACFEstimator, CostShareEstimator, WooldridgeIVEstimator

# Wooldridge IV: use spec2 for 3-input (COGS + Capital + SG&A)
iv_est = WooldridgeIVEstimator(specification="spec2")

# Cost Share: include SG&A in cost share calculation
cs_est = CostShareEstimator(include_sga=True)

# ACF: include SG&A as third input
acf_est = ACFEstimator(include_sga=True)
```

Via pipeline config:

```python
from PyMarkup import PipelineConfig, EstimatorConfig

config = PipelineConfig(
    compustat_path="Input/DLEU/Compustat_annual.csv",
    macro_vars_path="Input/DLEU/macro_vars_new.xlsx",
    estimator=EstimatorConfig(
        method="all",
        iv_specification="spec2",    # Wooldridge IV with SG&A
        cs_include_sga=True,         # Cost Share with SG&A
        acf_include_sga=True,        # ACF with SG&A
    ),
)
```

#### Aggregation Weights

When aggregating firm-level markups to industry or economy level, you can choose the weighting scheme:

| Weight Type | Formula | Use Case |
|-------------|---------|----------|
| `"revenue"` (default) | `firm_revenue / total_revenue` | Standard approach, larger firms weighted more |
| `"cost"` | `firm_cogs / total_cogs` | Weight by production scale |

```python
from PyMarkup.core.markup_calculation import aggregate_markups

# Revenue-weighted aggregation (default)
agg = aggregate_markups(
    firm_markups, by="year", method="weighted_mean",
    weight_type="revenue", panel_data=panel_data
)

# Cost-weighted aggregation
agg = aggregate_markups(
    firm_markups, by="year", method="weighted_mean",
    weight_type="cost", panel_data=panel_data
)
```

Via pipeline config:
```python
config = PipelineConfig(
    ...
    aggregation_weight="revenue",  # or "cost"
)
```

### 4. Markup Calculation

Computes firm-level markups using the De Loecker & Warzynski formula:

```
markup = θ / cost_share
where cost_share = COGS / Revenue
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
