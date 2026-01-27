# PyMarkup Project Structure - Reorganization Plan

## Current Issues

1. **Mixed paradigms**: Numbered scripts (0.0-4.) alongside proper modules
2. **Duplicate files**: `cli.py` vs `cli/`, `utils.py` vs `utils/`
3. **Old files**: Stata `.do` files mixed with Python code
4. **Unclear organization**: Legacy scripts at top level of package

## Proposed New Structure

```
PyMarkup/
├── README.md
├── SECURITY_SETUP.md
├── DATA_DOWNLOADING_GUIDE.md
├── CLAUDE.md
├── pyproject.toml
├── .env.example
├── config.yaml.example
├── .gitignore
│
├── docs/                              # Documentation (NEW)
│   ├── index.md
│   ├── quickstart.md
│   ├── api_reference.md
│   ├── data_requirements.md
│   ├── methodology.md
│   ├── decomposition_guide.md         # NEW
│   └── examples/
│       ├── basic_usage.ipynb
│       ├── decomposition_example.ipynb
│       └── comparison_methods.ipynb
│
├── src/PyMarkup/
│   ├── __init__.py                    # Public API exports
│   ├── __main__.py                    # Entry point
│   ├── _version.py                    # Version info
│   ├── config_loader.py               # Credential management
│   ├── path_plot_config.py            # Paths and plotting
│   │
│   ├── core/                          # Core logic (INTERNAL)
│   │   ├── __init__.py
│   │   ├── data_preparation.py        # Clean Compustat panel
│   │   └── markup_calculation.py      # Compute markups
│   │
│   ├── data/                          # Data I/O (INTERNAL)
│   │   ├── __init__.py
│   │   ├── loaders.py                 # Load existing files
│   │   └── downloaders.py             # Download from APIs
│   │
│   ├── estimators/                    # Production function estimators (PUBLIC)
│   │   ├── __init__.py
│   │   ├── base.py                    # Abstract base class
│   │   ├── wooldridge_iv.py           # IV/GMM estimator
│   │   ├── cost_share.py              # Cost share estimator
│   │   └── acf.py                     # ACF estimator
│   │
│   ├── decomposition/                 # ⭐ NEW MODULE
│   │   ├── __init__.py
│   │   ├── base.py                    # Base decomposition class
│   │   ├── aggregate.py               # Aggregate markup decomposition
│   │   ├── fhk.py                     # Foster-Haltiwanger-Krizan decomposition
│   │   ├── melitz.py                  # Melitz-Polanec decomposition
│   │   └── visualization.py           # Decomposition plots
│   │
│   ├── pipeline/                      # End-to-end pipelines (PUBLIC)
│   │   ├── __init__.py
│   │   ├── config.py                  # PipelineConfig, EstimatorConfig
│   │   └── markup_pipeline.py         # MarkupPipeline orchestrator
│   │
│   ├── io/                            # Input/output schemas (PUBLIC)
│   │   ├── __init__.py
│   │   └── schemas.py                 # InputData, MarkupResults
│   │
│   ├── cli/                           # Command-line interface
│   │   ├── __init__.py
│   │   ├── main.py                    # Main CLI app
│   │   ├── estimate.py                # Estimation commands
│   │   ├── download.py                # Download commands
│   │   └── decompose.py               # NEW: Decomposition commands
│   │
│   ├── utils/                         # Utilities (INTERNAL)
│   │   ├── __init__.py
│   │   ├── transformations.py         # Log, lags, deflation
│   │   └── constants.py               # Industry codes, constants
│   │
│   └── scripts/                       # Legacy/standalone scripts (RENAMED from _legacy)
│       ├── README.md                  # Explains legacy scripts
│       ├── 0.0_download_compustat.py  # Cleaned up names
│       ├── 0.1_download_cpi.py
│       ├── 0.2_download_ppi.py
│       ├── 0.3_theta_estimation.py
│       ├── 0.4_create_main_datasets.py
│       ├── 0.5_prepare_data.py
│       ├── 1_generate_figure1.py
│       ├── 2_generate_figure2.py
│       ├── 3_generate_summary_stats.py
│       ├── 4_generate_table1.py
│       ├── run_all.py                 # Run full pipeline
│       └── stata/                     # Original Stata code
│           ├── 0.3_theta_estimation.do
│           └── 0.4_create_datasets.do
│
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   ├── unit/
│   │   ├── test_data_loaders.py
│   │   ├── test_data_downloaders.py
│   │   ├── test_wooldridge_estimator.py
│   │   ├── test_cost_share_estimator.py
│   │   ├── test_acf_estimator.py
│   │   ├── test_decomposition_fhk.py       # NEW
│   │   ├── test_decomposition_melitz.py    # NEW
│   │   └── test_io_schemas.py
│   ├── integration/
│   │   ├── test_pipeline_end_to_end.py
│   │   └── test_decomposition_pipeline.py  # NEW
│   └── regression/
│       └── test_against_stata.py
│
└── examples/                          # Example scripts
    ├── README.md
    ├── basic_estimation.py
    ├── compare_methods.py
    ├── decomposition_analysis.py      # NEW
    └── custom_pipeline.py
```

## Key Changes

### 1. New Decomposition Module

**Purpose**: Decompose aggregate markup trends into components

**Features**:
- **Foster-Haltiwanger-Krizan (FHK)**: Decompose into within-firm, between-firm, entry/exit
- **Melitz-Polanec**: Alternative decomposition for trade/entry analysis
- **Aggregate trends**: Time series decomposition of markup changes
- **Visualization**: Publication-ready decomposition charts

### 2. Reorganization

**Move to `scripts/` (legacy)**:
- All numbered scripts (0.0-4.)
- `run_all.py`
- Stata `.do` files → `scripts/stata/`
- Old `Create_Data.py`, `Estimate_Coefficients.py`

**Clean up**:
- Remove duplicate `cli.py` (keep `cli/`)
- Remove duplicate `utils.py` (keep `utils/`)
- Remove empty `PyMarkup.py`
- Move macro calculations to `utils/`

**New directories**:
- `docs/` - Comprehensive documentation
- `examples/` - Example usage scripts
- `decomposition/` - New module

### 3. Documentation Structure

**Root level**:
- `README.md` - Overview and quick start
- `SECURITY_SETUP.md` - API key setup
- `DATA_DOWNLOADING_GUIDE.md` - Data download details
- `CLAUDE.md` - Development guide

**docs/ directory**:
- `index.md` - Documentation home
- `quickstart.md` - Getting started
- `api_reference.md` - Full API docs
- `data_requirements.md` - Data specs
- `methodology.md` - Estimation theory
- `decomposition_guide.md` - Decomposition methods
- `examples/` - Jupyter notebooks

## Migration Steps

1. ✅ Create decomposition module structure
2. ✅ Move legacy scripts to `scripts/`
3. ✅ Create documentation directory
4. ✅ Update imports and paths
5. ✅ Create example scripts
6. ✅ Update tests
7. ✅ Update README

## Public API (what users import)

```python
# Main pipeline
from PyMarkup import MarkupPipeline, PipelineConfig, EstimatorConfig

# Estimators
from PyMarkup.estimators import (
    WooldridgeIVEstimator,
    CostShareEstimator,
    ACFEstimator
)

# Decomposition (NEW)
from PyMarkup.decomposition import (
    FHKDecomposition,
    MelitzDecomposition,
    plot_decomposition
)

# I/O
from PyMarkup.io import InputData, MarkupResults

# Data
from PyMarkup.data import (
    load_compustat,
    load_cpi,
    load_ppi,
    download_compustat,
    download_cpi,
    download_ppi
)

# Config
from PyMarkup.config_loader import get_fred_api_key, get_config
```

## Backward Compatibility

### Keep working:
- Old numbered scripts in `scripts/` (with deprecation warnings)
- `run_all.py` still works
- All existing imports still work (via `__init__.py` exports)

### Deprecation path:
1. Version 0.3.0: Add deprecation warnings to old scripts
2. Version 0.4.0: Move scripts to `scripts/` but keep working
3. Version 1.0.0: Remove backward compatibility, clean API only

## Next Actions

1. Implement decomposition module
2. Create migration script to reorganize files
3. Update all imports
4. Create comprehensive docs
5. Add examples
6. Update tests
