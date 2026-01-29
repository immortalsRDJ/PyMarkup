# PyMarkup-estimator

A Python toolkit for estimating firm-level markups using production function-based marginal cost recovery.

## Installation

```bash
pip install PyMarkup
# or
uv add PyMarkup
```

From source:
```bash
git clone https://github.com/immortalsRDJ/PyMarkup
cd PyMarkup
uv sync --python 3.10  # Python 3.10 recommended for compatibility
```

## Data Download

PyMarkup includes data downloaders for Compustat, CPI, and PPI. Some require registered accounts:

| Data Source | Account Required | Registration |
|-------------|------------------|--------------|
| **Compustat** | WRDS account | [wrds-www.wharton.upenn.edu](https://wrds-www.wharton.upenn.edu) (institutional access) |
| **CPI** | FRED API key | [fred.stlouisfed.org/docs/api](https://fred.stlouisfed.org/docs/api/api_key.html) (free) |
| **PPI** | None | Public BLS data |

```python
from PyMarkup.data import download_compustat, download_cpi, download_ppi, load_config

# Download PPI (no account needed)
download_ppi()

# Download CPI (requires FRED API key in config.yaml or FRED_API_KEY env var)
download_cpi()

# Download Compustat (prompts for WRDS username/password interactively)
download_compustat()
```

To use WRDS, install the optional dependency:
```bash
uv sync --extra wrds
```

## Quick Start

### High-level Pipeline API

```python
from PyMarkup import MarkupPipeline, PipelineConfig, EstimatorConfig

config = PipelineConfig(
    compustat_path="Input/DLEU/Compustat_annual.dta",
    macro_vars_path="Input/DLEU/macro_vars_new.xlsx",
    estimator=EstimatorConfig(
        method="wooldridge_iv",  # or "cost_share", "acf", "all"
        iv_specification="spec2",
        window_years=5,
    ),
    output_dir="output/",
)

pipeline = MarkupPipeline(config)
results = pipeline.run()
```

### Low-level Estimator API

```python
from PyMarkup.estimators import WooldridgeIVEstimator, CostShareEstimator, ACFEstimator
from PyMarkup.core.data_preparation import create_compustat_panel

panel = create_compustat_panel(
    compustat_path="Input/DLEU/Compustat_annual.dta",
    macro_path="Input/DLEU/macro_vars_new.xlsx",
)

# Wooldridge IV (main method)
iv = WooldridgeIVEstimator(specification="spec2", window_years=5)
elasticities = iv.estimate_elasticities(panel)

# Cost Share (fast baseline)
cs = CostShareEstimator(include_sga=False, aggregation="median")
cs_results = cs.estimate_elasticities(panel)

# ACF (robustness check)
acf = ACFEstimator(window_years=5, include_market_share=True)
acf_results = acf.estimate_elasticities(panel)
```

### CLI

```bash
pymarkup estimate --config config.yaml
pymarkup estimate --method wooldridge_iv --compustat data.dta --macro-vars macro.xlsx
pymarkup validate Input/DLEU/Compustat_annual.dta
```

## Estimation Methods

| Method | Class | Description |
|--------|-------|-------------|
| **Wooldridge IV** | `WooldridgeIVEstimator` | IV/GMM with lagged COGS instrument. Two specs: COGS+K or COGS+K+SGA |
| **Cost Share** | `CostShareEstimator` | Direct accounting: theta = COGS/(COGS+K_expense) |
| **ACF** | `ACFEstimator` | Ackerberg-Caves-Frazer two-stage GMM with productivity proxy |

### Estimator Parameters

**WooldridgeIVEstimator**
```python
WooldridgeIVEstimator(
    specification="spec2",   # "spec1" (COGS+K), "spec2" (COGS+K+SGA), or "both"
    window_years=5,          # Rolling window size (±2 years)
    industry_level=2,        # NAICS digits (2, 3, or 4)
    min_observations=15,     # Minimum obs per window
)
```

**CostShareEstimator**
```python
CostShareEstimator(
    include_sga=False,       # Include SG&A in total costs
    aggregation="median",    # "median", "mean", or "weighted_mean"
    industry_level=2,        # NAICS digits (2, 3, or 4)
)
```

**ACFEstimator**
```python
ACFEstimator(
    window_years=5,          # Rolling window size
    include_market_share=True,  # Include market share controls
    industry_level=2,        # NAICS digits (2, 3, or 4)
    min_observations=15,     # Minimum obs per window
)
```

### Saving Results

All estimators have an optional `save()` method to persist theta estimates:

```python
from PyMarkup.estimators import WooldridgeIVEstimator

estimator = WooldridgeIVEstimator()
result = estimator.estimate_elasticities(panel_data)

# Save to Intermediate/ directory (optional)
estimator.save(
    output_dir="Intermediate/",
    suffix="DEUSample",      # Creates theta_W_s_window_DEUSample.dta
    format="dta",            # "dta" (Stata), "csv", or "parquet"
)
```

**Output filenames by estimator:**
| Estimator | Filename Pattern |
|-----------|------------------|
| `WooldridgeIVEstimator` | `theta_W_s_window_{suffix}.{format}` |
| `CostShareEstimator` | `theta_c_{suffix}.{format}` |
| `ACFEstimator` | `theta_acf_{suffix}.{format}` |

### Output Format

The `estimate_elasticities()` method returns a DataFrame with:

| Column | Description |
|--------|-------------|
| `ind2d` | 2-digit NAICS industry code |
| `year` | Fiscal year |
| `theta_c` | Output elasticity w.r.t. COGS (variable input) |
| `theta_k` | Output elasticity w.r.t. capital (IV/ACF only) |

### Computing Markups

Once you have theta estimates, compute firm-level markups:

```python
# Merge theta back to firm data
firm_data = firm_data.merge(result, on=["ind2d", "year"], how="left")

# Markup = theta * (Revenue / COGS)
firm_data["markup"] = firm_data["theta_c"] * (firm_data["sale_D"] / firm_data["cogs_D"])
```

<!-- ## Development

```bash
just test       # Run tests
just qa         # Run all QA checks (format, lint, type check, test)
just coverage   # Run coverage analysis
``` -->

## License

MIT License
