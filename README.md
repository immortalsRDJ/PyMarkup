# PyMarkup-estimator

![PyPI version](https://img.shields.io/pypi/v/PyMarkup-estimator.svg)
[![Documentation Status](https://readthedocs.org/projects/PyMarkup-estimator/badge/?version=latest)](https://PyMarkup-estimator.readthedocs.io/en/latest/?version=latest)
[![Tests](https://github.com/immortalsRDJ/PyMarkup-estimator/workflows/Tests/badge.svg)](https://github.com/immortalsRDJ/PyMarkup-estimator/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Python toolkit for estimating firm-level markups using production function-based marginal cost recovery.

* PyPI package: https://pypi.org/project/PyMarkup-estimator/
* GitHub repository: https://github.com/immortalsRDJ/PyMarkup-estimator
* Free software: MIT License
* Documentation: https://PyMarkup-estimator.readthedocs.io

## Key Features

- **Three Production Function Estimators**: Compare results across multiple methods
  - **Wooldridge IV**: IV/GMM with lagged COGS as instrument, rolling 5-year windows by industry (main method, addresses simultaneity bias)
  - **Cost Share**: Direct accounting approach assuming perfect competition (quick benchmark)
  - **ACF**: Ackerberg-Caves-Frazer two-stage GMM with productivity proxy (robustness check)

- **Flexible Configuration**: YAML config files or programmatic Python API

- **Industry-Level Estimation**: Rolling windows with configurable minimum observation thresholds

- **Clean Modular Architecture**: Separation between core logic, estimators, pipeline orchestration, and I/O

- **Rich Output Options**:
  - Save to CSV, Parquet, or Stata formats
  - Plot aggregate markup time series
  - Compare methods with summary statistics
  - Full type hints and validation with Pydantic

- **Command-Line Interface**: Run complete pipeline with a single command

- **Intermediate Results**: Optionally save panel data, elasticities, and markups at each step

## Quick Start

### Installation

```bash
pip install PyMarkup-estimator
```

**Note:** The package name is `PyMarkup-estimator`, but you import it as `PyMarkup`:
```python
from PyMarkup import MarkupPipeline  # Import name stays the same!
```

### Python API

```python
from PyMarkup import MarkupPipeline, PipelineConfig, EstimatorConfig

# Configure pipeline
config = PipelineConfig(
    compustat_path="data/compustat.dta",
    macro_vars_path="data/macro_vars.xlsx",
    estimator=EstimatorConfig(
        method="wooldridge_iv",  # or "cost_share", "acf", "all"
        iv_specification="spec2",
        window_years=5
    ),
    output_dir="output/"
)

# Run pipeline
pipeline = MarkupPipeline(config)
results = pipeline.run()

# Save and analyze results
results.save("output/", format="csv")
comparison = results.compare_methods()
fig = results.plot_aggregate()
```

### Command Line

```bash
# Using config file
pymarkup estimate --config config.yaml

# Direct parameters
pymarkup estimate --method wooldridge_iv \
    --compustat data/compustat.dta \
    --macro-vars data/macro_vars.xlsx \
    --output results/
```

## How It Works

The `MarkupPipeline` orchestrates a 3-step workflow:

1. **Data Preparation**: Load Compustat panel, merge macro variables, deflate to real terms, apply percentile trimming
2. **Elasticity Estimation**: Estimate production function output elasticities (θ) by industry-year using selected method(s)
3. **Markup Calculation**: Compute firm-level markups as `markup = θ_cogs / cost_share`

## Requirements

- Python 3.10+
- pandas, numpy, scipy
- linearmodels (for IV/2SLS estimation)
- statsmodels
- pydantic (for configuration validation)
- typer (for CLI)

## Development

```bash
# Install with development dependencies
pip install -e ".[test]"

# Run tests
pytest

# Run quality checks
ruff check .
ruff format .
```

## TODO

* Decomposition
