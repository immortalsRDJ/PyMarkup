# PyMarkup v0.2.0 - New Package Structure

This document describes the new package structure created for PyMarkup v0.2.0.

## What's New

PyMarkup has been refactored from a collection of numbered scripts into a professional Python package with:
- **Clean public API** for programmatic use
- **Multiple estimation methods** (Wooldridge IV, Cost Share, ACF)
- **Unified pipeline interface** with configuration management
- **Type-safe I/O** with Pydantic validation
- **CLI interface** with rich output
- **Modular architecture** for extensibility

## New Directory Structure

```
src/PyMarkup/
├── __init__.py              # Public API exports
├── _version.py              # Version (0.2.0-dev)
│
├── core/                    # Core estimation logic (INTERNAL)
│   ├── data_preparation.py  # Compustat panel creation
│   ├── markup_calculation.py # Compute markups from elasticities
│
├── data/                    # Data loading (INTERNAL)
│   └── loaders.py           # Compustat, macro vars loaders
│
├── estimators/              # PUBLIC API - Estimator classes
│   ├── base.py              # ProductionFunctionEstimator ABC
│   ├── wooldridge_iv.py     # WooldridgeIVEstimator
│   ├── cost_share.py        # CostShareEstimator
│   └── acf.py               # ACFEstimator
│
├── pipeline/                # PUBLIC API - Pipeline
│   ├── config.py            # PipelineConfig, EstimatorConfig
│   └── markup_pipeline.py   # MarkupPipeline orchestrator
│
├── io/                      # PUBLIC API - I/O
│   └── schemas.py           # InputData, MarkupResults (Pydantic)
│
├── cli/                     # CLI
│   └── main.py              # pymarkup command
│
└── _legacy/                 # Old numbered scripts (TBD)
```

## Quick Start

### Installation

```bash
# Install with new dependencies
uv sync

# Or using pip
pip install -e .
```

### Usage

#### High-level Pipeline API (Recommended)

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

#### Low-level Estimator API

```python
from PyMarkup.estimators import WooldridgeIVEstimator
from PyMarkup.core.data_preparation import create_compustat_panel

# Prepare data
panel = create_compustat_panel(
    compustat_path="Input/DLEU/Compustat_annual.dta",
    macro_path="Input/DLEU/macro_vars_new.xlsx",
)

# Estimate elasticities
estimator = WooldridgeIVEstimator(specification="spec2")
elasticities = estimator.estimate_elasticities(panel)
```

#### CLI Usage

```bash
# Using config file
pymarkup estimate --config config.yaml

# Using command-line args
pymarkup estimate \
    --method wooldridge_iv \
    --compustat Input/DLEU/Compustat_annual.dta \
    --macro-vars Input/DLEU/macro_vars_new.xlsx \
    --output output/

# Validate data
pymarkup validate Input/DLEU/Compustat_annual.dta
```

#### YAML Configuration

```yaml
# config.yaml
compustat_path: Input/DLEU/Compustat_annual.dta
macro_vars_path: Input/DLEU/macro_vars_new.xlsx

estimator:
  method: wooldridge_iv
  iv_specification: spec2
  window_years: 5
  industry_level: 2

output_dir: output/
```

## Public API Reference

### Pipeline Classes

- `MarkupPipeline`: Main pipeline orchestrator
- `PipelineConfig`: Pipeline configuration
- `EstimatorConfig`: Estimator configuration

### Estimators

All inherit from `ProductionFunctionEstimator`:

- `WooldridgeIVEstimator`: IV/GMM with lagged COGS instrument
- `CostShareEstimator`: Direct cost share (accounting approach)
- `ACFEstimator`: Ackerberg-Caves-Frazer two-stage GMM

### I/O

- `InputData`: Validated input data container (Pydantic)
- `MarkupResults`: Results with comparison tools

## Estimation Methods

| Method | Class | Description | Best For |
|--------|-------|-------------|----------|
| **Wooldridge IV** | `WooldridgeIVEstimator` | IV/GMM, two specs (±SG&A) | Research, addresses endogeneity |
| **Cost Share** | `CostShareEstimator` | Direct accounting θ = COGS/(COGS+K) | Quick estimates, benchmarking |
| **ACF** | `ACFEstimator` | Two-stage GMM with productivity proxy | Robustness checks, selection bias |

## Examples

See `examples/` directory:
- `quickstart.py`: Basic usage examples
- `config_example.yaml`: Example configuration file

## Migration from Old Scripts

Old numbered scripts (e.g., `0.3 theta_estimation.py`) still exist but will be moved to `_legacy/`.

To replicate old behavior:

```python
config = PipelineConfig.from_legacy_settings()
pipeline = MarkupPipeline(config)
results = pipeline.run()
```

## Next Steps

### Immediate (Week 1)

1. **Extract full IV logic** from `0.3 theta_estimation.py` into `WooldridgeIVEstimator`
2. **Test basic pipeline** with sample data
3. **Create test fixtures** for unit tests

### Short-term (Weeks 2-3)

4. Move old scripts to `_legacy/`
5. Implement `MarkupResults.save()` fully
6. Add logging throughout
7. Write comprehensive docstrings

### Medium-term (Week 4+)

8. Unit tests for all estimators
9. Integration tests with real data
10. Regression tests against Stata
11. Documentation and examples
12. CI/CD setup

## Development

```bash
# Install dev dependencies
uv sync --extra test --extra dev

# Run tests
just test

# Format and lint
just qa

# Type check
uv run ty check .
```

## Notes

- Old scripts remain functional during migration
- New dependencies added: `pydantic`, `pyyaml`, `rich`
- CLI command changed from `PyMarkup` to `pymarkup`
- Version bumped to `0.2.0-dev`

## Questions?

See `CLAUDE.md` for full package construction plan and design rationale.
