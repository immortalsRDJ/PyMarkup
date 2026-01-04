# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyMarkup is a Python toolkit for estimating firm-level markups using production function-based marginal cost recovery.

## Development Commands

This project uses `just` as a task runner and `uv` for package management.

### Testing
```bash
# Run all tests with Python 3.13
just test

# Run tests with arguments (e.g., specific test file)
just test tests/test_PyMarkup.py

# Run with debugger on failure
just pdb

# Run tests for all supported Python versions (3.10-3.13)
just testall

# Run coverage analysis
just coverage
```

### Code Quality
```bash
# Run all QA checks (format, lint, type check, test)
just qa

# Individual tools (run via uv):
uv run --python=3.13 --extra test ruff format .
uv run --python=3.13 --extra test ruff check . --fix
uv run --python=3.13 --extra test ty check .
```

### Building
```bash
# Build the package
just build

# Clean build artifacts
just clean
```

### Version Management
```bash
# Show current version
just version

# Tag and push version to GitHub
just tag
```

## Architecture

### Directory Structure

The project follows a strict separation between code and data:

- **`src/PyMarkup/`**: Main package with pipeline scripts
- **`src/BMYReplication/`**: Python translations of original Stata code from Bond-Hashemi-Kaplan replication package
- **`Input/`**: Raw data (Compustat, CPI, PPI, macro variables) - **not version controlled**
- **`Intermediate/`**: Generated intermediate datasets (trimmed panels, theta estimates) - **not version controlled**
- **`Output/`**: Final figures and tables - **not version controlled**

All data directories (`Input/`, `Intermediate/`, `Output/`) are excluded from git and contain large proprietary files.

### Path Configuration

All scripts use centralized path configuration from `src/PyMarkup/path_plot_config.py`:
- `proj_dir`: Repository root (auto-detected from file location)
- `code_dir`: `src/PyMarkup/`
- `data_dir`: `Input/`
- `int_dir`: `Intermediate/`
- `out_dir`: `Output/`

Scripts can be run from any directory because paths are computed relative to the source file location.

### Pipeline Architecture

The main pipeline is orchestrated by `src/PyMarkup/run_all.py`, which executes numbered scripts in sequence:

1. **Data Download** (Step 0):
   - `0.0 Download Compustat.py`: Pull Compustat data from WRDS
   - `0.1 Download CPI.py`: Download CPI data from FRED
   - `0.2 PPI Data Preparation.py`: Download and process PPI data from BLS

2. **Coefficient Estimation** (Step 1):
   - `0.3 theta_estimation.py`: Self-contained script that builds trimmed Compustat panel and estimates production function elasticities using IV/GMM rolling windows by industry

3. **Dataset Construction** (Step 2):
   - `0.4 Create Main Datasets.py`: Merge Compustat with PPI and CPI deflators
   - Creates `main_annual.csv` and `main_quarterly.csv` in `Intermediate/`

4. **Analysis & Output** (Steps 3-7):
   - `0.5 Prepare Data for Figures and Tables.py`
   - `1. Generate Figure 1 - Aggregate Markup.py`
   - `2. Generate Figure 2 - CAGR of PPI vs Markup.py`
   - `3. Generate Summary Statistics.py`
   - `4. Generate Table 1.py`

### Key Modules

- **`Create_Data.py`**: Builds trimmed annual Compustat panel, deflates by macro variables, applies percentile trimming
- **`Estimate_Coefficients.py`**: Estimates production function output elasticities using Wooldridge-style IV/GMM approach with rolling 5-year windows by 2-digit industry
- **`0.3 theta_estimation.py`**: Combines Create_Data and Estimate_Coefficients logic inline for the main pipeline

### BMYReplication Package

The `src/BMYReplication/` directory contains Python translations of original Stata `.do` files:
- Mirrors the structure of the Bond-Hashemi-Kaplan replication code
- Uses `linearmodels` for IV/2SLS estimation
- Can be run independently via `main.py`

## Data Requirements

Before running the pipeline, ensure these directories and files exist:

### Input Data
- `Input/DLEU/Compustat_annual.dta`: Downloaded from WRDS (see `0.0 Download Compustat.py`)
- `Input/DLEU/macro_vars_new.xlsx`: Macro variables (USGDP, usercost)
- `Input/CPI/`: CPI data from FRED
- `Input/PPI/`: PPI data from BLS
- `Input/Other/NAICS_2D_Description.xlsx`: Industry code lookup

### API Keys
- WRDS credentials required for Compustat download
- FRED API key in `path_plot_config.py` (for CPI download)

See `DATA_MANIFEST.md` for complete data documentation.

## Running the Full Pipeline

```bash
# Ensure you're in the repository root
cd /path/to/PyMarkup

# Run the entire pipeline (downloads data, estimates parameters, generates outputs)
python src/PyMarkup/run_all.py
```

Individual scripts can be run standalone from anywhere:
```bash
python src/PyMarkup/0.3\ theta_estimation.py
```

## Dependencies

Core dependencies:
- `typer`: CLI framework
- `pandas`: Data manipulation
- `numpy`: Numerical computing
- `linearmodels`: IV/2SLS estimation
- `scipy`: Optimization
- `statsmodels`: Statistical models
- `matplotlib`, `seaborn`: Plotting

Development dependencies (install with `--extra test`):
- `pytest`: Testing
- `ruff`: Linting and formatting
- `ty`: Type checking
- `coverage`: Test coverage
- `ipdb`: Debugging

## Notes for Development

- Python 3.10+ required (specified in `pyproject.toml`)
- Use `uv` for dependency management
- Scripts use `runpy.run_path()` or `subprocess.run()` to execute other Python files
- Plot styling is centralized in `path_plot_config.py` via `setplotstyle()` and `setplotstyle_agg()`
- The CLI (`PyMarkup.cli`) is currently a placeholder - main functionality is in numbered scripts

---

## Package Refactoring Plan (v0.2.0+)

### Goal
Transform PyMarkup from a collection of numbered scripts into a professional Python package with:
- Clean public API for programmatic use
- Multiple estimation methods (IV, Cost Share, ACF)
- Unified pipeline interface
- Comprehensive testing
- Full documentation

### New Package Structure

```
src/PyMarkup/
├── __init__.py              # Public API exports
├── _version.py              # Single source of truth for version
│
├── core/                    # Core estimation logic (INTERNAL)
│   ├── __init__.py
│   ├── data_preparation.py  # Clean Compustat panel creation
│   ├── estimation.py        # IV/GMM/ACF estimators
│   ├── markup_calculation.py # Compute markups from elasticities
│   └── aggregation.py       # Industry/time aggregations
│
├── data/                    # Data loading/downloading (INTERNAL)
│   ├── __init__.py
│   ├── loaders.py           # Load Compustat, macro vars, PPI, CPI
│   ├── downloaders.py       # WRDS, FRED, BLS API clients
│   └── validators.py        # Data quality checks
│
├── estimators/              # PUBLIC API - main estimator classes
│   ├── __init__.py
│   ├── base.py              # ProductionFunctionEstimator abstract class
│   ├── wooldridge_iv.py     # WooldridgeIVEstimator (2 specs)
│   ├── cost_share.py        # CostShareEstimator (accounting approach)
│   └── acf.py               # ACFEstimator (Ackerberg-Caves-Frazer)
│
├── pipeline/                # PUBLIC API - end-to-end pipelines
│   ├── __init__.py
│   ├── markup_pipeline.py   # MarkupPipeline orchestrator
│   └── config.py            # PipelineConfig, EstimatorConfig dataclasses
│
├── io/                      # Input/output interfaces (PUBLIC)
│   ├── __init__.py
│   ├── schemas.py           # Pydantic models for I/O validation
│   ├── readers.py           # Read various formats (CSV, Stata, Parquet)
│   └── writers.py           # Write outputs
│
├── utils/                   # Utilities (INTERNAL)
│   ├── __init__.py
│   ├── transformations.py   # Log, lags, deflation helpers
│   └── constants.py         # Industry codes, deflator types
│
├── cli/                     # Command-line interface
│   ├── __init__.py
│   ├── main.py              # Main CLI app
│   ├── estimate.py          # `pymarkup estimate` commands
│   ├── download.py          # `pymarkup download` commands
│   └── validate.py          # `pymarkup validate` commands
│
└── _legacy/                 # Backward compatibility (old numbered scripts)
    ├── run_all.py
    └── ...
```

### Public API Design

Users will interact with PyMarkup through:

```python
# High-level pipeline API (recommended for most users)
from PyMarkup import MarkupPipeline, PipelineConfig, EstimatorConfig

config = PipelineConfig(
    compustat_path="data/compustat.dta",
    macro_vars_path="data/macro_vars.xlsx",
    estimator=EstimatorConfig(
        method="wooldridge_iv",  # or "cost_share", "acf", "all"
        iv_specification="spec2",  # spec1 (COGS+K) or spec2 (+SGA)
        window_years=5,
    ),
    output_dir="output/"
)

pipeline = MarkupPipeline(config)
results = pipeline.run()  # Returns MarkupResults object
results.save("output/markups.csv")
results.plot_aggregate("output/fig1.png")
```

```python
# Low-level estimator API (for researchers who want control)
from PyMarkup.estimators import WooldridgeIVEstimator, ACFEstimator
from PyMarkup.io import InputData

data = InputData.from_compustat("data/compustat.dta")

# Wooldridge IV estimation
iv_estimator = WooldridgeIVEstimator(specification="spec2", window_years=5)
elasticities = iv_estimator.estimate_elasticities(data)
markups = iv_estimator.compute_markups(elasticities, data)

# ACF estimation
acf_estimator = ACFEstimator(window_years=5)
elasticities_acf = acf_estimator.estimate_elasticities(data)
```

```python
# CLI usage
# $ pymarkup estimate --config config.yaml
# $ pymarkup estimate --method wooldridge_iv --compustat data.dta --macro-vars macro.xlsx
# $ pymarkup download compustat --wrds-username myuser
# $ pymarkup validate --input data/compustat.dta
```

### Estimation Methods

PyMarkup supports three production function estimation methods:

| Method | Class | Description | Use Case |
|--------|-------|-------------|----------|
| **Wooldridge IV** | `WooldridgeIVEstimator` | IV/GMM with lagged COGS as instrument. Two specs: (1) COGS+Capital, (2) +SG&A | Preferred for research; addresses simultaneity bias |
| **Cost Share** | `CostShareEstimator` | Direct accounting: θ = cost_share = COGS/(COGS+K_expense) | Quick estimates, benchmarking, assumes perfect competition |
| **ACF** | `ACFEstimator` | Ackerberg-Caves-Frazer two-stage GMM with productivity proxy | Robustness check, handles selection bias |

All estimators inherit from `ProductionFunctionEstimator` base class.

### Input/Output Schemas

**Input** (validated with Pydantic):
```python
class InputData(BaseModel):
    gvkey: pd.Series      # Firm identifier
    year: pd.Series       # Fiscal year
    sale: pd.Series       # Sales revenue
    cogs: pd.Series       # Cost of goods sold
    ppegt: pd.Series      # Capital stock (PP&E)
    naics: pd.Series      # Industry code
    xsga: pd.Series | None = None  # SG&A (optional)
    emp: pd.Series | None = None   # Employment (optional)
```

**Output**:
```python
class MarkupResults(BaseModel):
    firm_markups: dict[str, pd.DataFrame]  # {method_name: df with gvkey, year, markup}
    elasticities: dict[str, pd.DataFrame]  # {method_name: df with ind2d, year, theta_c, theta_k}
    config: PipelineConfig
    metadata: dict

    def compare_methods() -> pd.DataFrame  # Compare across methods
    def plot_aggregate_comparison(save_path) -> Figure  # Plot all methods
```

### Testing Strategy

```
tests/
├── conftest.py              # Shared fixtures (sample data)
├── fixtures/                # Sample Compustat, macro vars files
│
├── unit/                    # Fast unit tests (~100ms)
│   ├── test_data_preparation.py
│   ├── test_transformations.py
│   ├── test_wooldridge_iv.py
│   ├── test_cost_share.py
│   ├── test_acf.py
│   └── test_io_schemas.py
│
├── integration/             # Integration tests (~1-5s)
│   ├── test_pipeline_end_to_end.py
│   ├── test_estimators.py
│   └── test_cli.py
│
└── regression/              # Regression tests (slow, critical)
    └── test_against_stata.py  # Compare with original Stata outputs
```

**Test Coverage Requirements**:
- Unit tests: >90% coverage
- All public API methods must have tests
- Regression tests ensure numerical accuracy vs. Stata

### Migration Phases

**Phase 1: Core Refactoring** (Weeks 1-2)
- [ ] Create new package structure
- [ ] Extract `WooldridgeIVEstimator` from `0.3 theta_estimation.py`
- [ ] Extract `CostShareEstimator` from cost share logic
- [ ] Extract `ACFEstimator` from ACF logic
- [ ] Create `InputData` and `MarkupResults` schemas
- [ ] Move old scripts to `_legacy/` for backward compatibility

**Phase 2: Pipeline & Configuration** (Week 3)
- [ ] Implement `MarkupPipeline` orchestrator
- [ ] Design `PipelineConfig` and `EstimatorConfig` dataclasses
- [ ] Add YAML config file support
- [ ] Build unified CLI with `typer`

**Phase 3: Testing** (Week 4)
- [ ] Write unit tests for all estimators
- [ ] Create integration tests with sample data
- [ ] Add regression tests against Stata outputs
- [ ] Set up CI/CD with GitHub Actions
- [ ] Add pre-commit hooks (ruff, type checking)

**Phase 4: Documentation** (Week 5)
- [ ] Add comprehensive docstrings (Google style)
- [ ] Create user guide and tutorials
- [ ] Generate API reference docs
- [ ] Add type hints throughout
- [ ] Create example Jupyter notebooks

### Backward Compatibility

Old numbered scripts in `_legacy/` will continue to work:
```python
# src/PyMarkup/_legacy/run_all.py
# Wrapper that calls new API
from PyMarkup import MarkupPipeline, PipelineConfig

# Preserve old behavior
config = PipelineConfig.from_legacy_settings()
pipeline = MarkupPipeline(config)
pipeline.run()
```

### Configuration Example

`config.yaml`:
```yaml
# Data paths
compustat_path: Input/DLEU/Compustat_annual.dta
macro_vars_path: Input/DLEU/macro_vars_new.xlsx

# Estimation method
estimator:
  method: wooldridge_iv  # or cost_share, acf, all
  iv_specification: spec2
  window_years: 5
  industry_level: 2
  min_observations: 15

# Data processing
include_interest_cogs: false
trim_percentiles: [0.01, 0.99]

# Output
output_dir: Output/
save_intermediate: true
```

### Dependencies Update

Core additions to `pyproject.toml`:
```toml
dependencies = [
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "scipy>=1.10.0",
    "statsmodels>=0.14.0",
    "linearmodels>=5.0",
    "pydantic>=2.0",      # Input/output validation
    "typer>=0.9.0",       # CLI framework
    "rich>=13.0",         # CLI pretty printing
    "pyyaml>=6.0",        # Config files
    "matplotlib>=3.7.0",
    "seaborn>=0.12.0",
]

[project.optional-dependencies]
test = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "hypothesis>=6.0",    # Property-based testing
    "coverage[toml]>=7.0",
]
```
