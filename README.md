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

<!-- ## Development

```bash
just test       # Run tests
just qa         # Run all QA checks (format, lint, type check, test)
just coverage   # Run coverage analysis
``` -->

## License

MIT License
