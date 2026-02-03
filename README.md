# PyMarkup

A Python toolkit for estimating firm-level markups using production function-based marginal cost recovery.

## Installation

```bash
git clone https://github.com/immortalsRDJ/PyMarkup
cd PyMarkup
uv sync --python 3.10
```

For WRDS data downloads: `uv sync --extra wrds`

## Pipeline

```
1. Data Download  →  2. Data Preparation  →  3. Elasticity Estimation (θ)
       →  4. Markup Calculation  →  5. Figures  →  6. Decomposition
```

### 1. Data Download

| Source | Credentials | Module |
|--------|-------------|--------|
| Compustat (WRDS) | WRDS account | `download_compustat()` |
| CPI (FRED) | FRED API key | `download_cpi()` |
| PPI (BLS) | None | `download_ppi()` |

Configure via `config.yaml` (copy from `config.example.yaml`) or environment variables (`FRED_API_KEY`, `WRDS_USERNAME`).

### 2. Data Preparation

Cleans Compustat panel: deduplicates, extracts NAICS codes, deflates by GDP, computes market shares, trims outliers.

### 3. Elasticity Estimation

Estimates output elasticity of variable inputs (θ_c) at the industry-year level:

| Method | Class | Use Case |
|--------|-------|----------|
| Wooldridge IV | `WooldridgeIVEstimator` | Main method, addresses endogeneity via IV/2SLS |
| Cost Share | `CostShareEstimator` | Fast baseline, no regression needed |
| ACF | `ACFEstimator` | Robustness, two-stage GMM with control function |

### 4. Markup Calculation

```
markup = θ_c / cost_share
where cost_share = COGS / (COGS + capital_expense [+ SG&A])
```

### 5. Figures

| Figure | Function | Description |
|--------|----------|-------------|
| Aggregate Markup | `plot_aggregate_markup()` | Time series comparing DLEU benchmark, replication, PPI-matched firms |
| PPI vs Markup | `plot_markup_vs_ppi()` | Scatter of firm-level CAGR with weighted OLS regression |

Data preparation for the scatter plot (CAGR computation, firm filtering) is handled by `prepare_scatter_data()`.

### 6. Decomposition

Dynamic Olley-Pakes decomposition of period-to-period aggregate markup changes:

```
Δμ_t = Δwithin + Δreallocation + Δnet_entry
```

| Component | Formula | Interpretation |
|-----------|---------|----------------|
| Within | Σ m_{i,t-1} · Δμ_{i,t} | Markup changes at base-period shares |
| Reallocation | Σ μ̃_{i,t-1} · Δm_{i,t} + Σ Δμ · Δm | Market share shifts toward high/low-markup firms |
| Net Entry | Σ_{E} μ̃ · m - Σ_{X} μ̃ · m | Difference between entrants and exiters |

Visualization: `plot_decomposition()` (4-line cumulative chart), `plot_component_contributions()` (stacked bar).

## Quick Start

### Full Pipeline

```python
from PyMarkup import MarkupPipeline, PipelineConfig, EstimatorConfig

config = PipelineConfig(
    compustat_path="Input/DLEU/Compustat_annual.dta",
    macro_vars_path="Input/DLEU/macro_vars_new.xlsx",
    estimator=EstimatorConfig(method="all"),
)

pipeline = MarkupPipeline(config)
results = pipeline.run()
results.save(output_dir="Output/", format="csv")
```

### Individual Estimators

```python
from PyMarkup.estimators import WooldridgeIVEstimator, CostShareEstimator, ACFEstimator
from PyMarkup.io import InputData

data = InputData.from_compustat("Input/DLEU/Compustat_annual.dta")

# Wooldridge IV (main method)
estimator = WooldridgeIVEstimator(specification="spec2")
elasticities = estimator.estimate_elasticities(data)

# Cost Share (fast baseline)
cs = CostShareEstimator()
cs_elasticities = cs.estimate_elasticities(data)

# ACF (robustness)
acf = ACFEstimator(include_market_share=True)
acf_elasticities = acf.estimate_elasticities(data)
```

### Decomposition

```python
from PyMarkup.decomposition import OlleyPakesDecomposition, plot_decomposition

op = OlleyPakesDecomposition()
decomp_results = op.decompose(firm_markups)
print(decomp_results[["unweighted_mean", "op_covariance"]])

plot_decomposition(decomp_results, output_path="Output/decomposition.pdf")
```

### Data Download

```python
from PyMarkup.data import download_compustat, download_cpi, download_ppi, load_config

config = load_config("config.yaml")
download_compustat(config)  # Requires WRDS credentials
download_cpi(config)        # Requires FRED API key
download_ppi(config)        # No credentials needed
```

## Configuration

### Credentials (`config.yaml`)

```yaml
fred_api_key: "your-fred-api-key"
wrds_username: "your-wrds-username"
```

Or via environment variables: `FRED_API_KEY`, `WRDS_USERNAME`.


## Project Structure

```
src/PyMarkup/
├── core/              # Data preparation, markup calculation, figures
├── data/              # Data downloaders and loaders
├── estimators/        # WooldridgeIV, CostShare, ACF estimators
├── pipeline/          # MarkupPipeline orchestrator, config
├── decomposition/     # Dynamic Olley-Pakes decomposition + visualization
├── io/                # I/O schemas (Pydantic)
└── cli/               # CLI commands

Input/                 # Raw data (not version controlled)
Intermediate/          # Generated datasets, theta estimates
Output/                # Figures and tables
```

## License

MIT License
