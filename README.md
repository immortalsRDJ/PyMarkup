# PyMarkup

A Python toolkit for estimating firm-level markups using production function-based marginal cost recovery.

## Installation

```bash
pip install Pymkp
```

For development:

```bash
git clone https://github.com/immortalsRDJ/PyMarkup
cd PyMarkup
uv sync
```

## Quick Start

### Command Line

```bash
# Set up config
cp config.example.yaml config.yaml
# Edit config.yaml with your API keys

# Run full pipeline (download + estimate + figures)
pymarkup run-all --config config.yaml

# Skip download (use existing data)
pymarkup run-all --config config.yaml --skip-download
```

## Pipeline

```
Download --> Data Preparation --> Elasticity Estimation --> Markup Calculation --> Figures & Decomposition
```

| Step | What it does | Key function |
|------|-------------|--------------|
| 0. Download | Fetch Compustat, CPI, PPI from WRDS/FRED/BLS | `pipeline.run_download()` |
| 1. Data Prep | Dedupe, deflate by GDP, compute market shares, trim outliers | `pipeline.run_data_preparation()` |
| 2. Estimation | Estimate output elasticity (θ) by industry-year | `pipeline.run_estimation()` |
| 3. Markup | `markup = θ / cost_share` | `pipeline.run_markup_calculation()` |
| 4. Figures | Aggregate markup time series, PPI vs markup scatter | `pipeline.run_figures()` |
| 5. Decomposition | Olley-Pakes: Within + Reallocation + Net Entry | `pipeline.run_decomposition()` |

## Estimators

| Method | Class | Use Case |
|--------|-------|----------|
| Wooldridge IV | `WooldridgeIVEstimator` | Main method, addresses endogeneity via IV/2SLS |
| Cost Share | `CostShareEstimator` | Fast baseline, no regression needed |
| ACF | `ACFEstimator` | Robustness, two-stage GMM with control function |

All estimators support SG&A as a third input:

| Estimator | Parameter | Default |
|-----------|-----------|---------|
| Wooldridge IV | `specification="spec1"` / `"spec2"` | `"spec2"` (with SG&A) |
| Cost Share | `include_sga=True/False` | `False` |
| ACF | `include_sga=True/False` | `False` |

## Configuration

### Credentials

Set via `config.yaml` or environment variables:

```yaml
fred_api_key: "your-fred-api-key"
wrds_username: "your-wrds-username"
```

Or: `FRED_API_KEY`, `WRDS_USERNAME`

### Data Requirements

| Source | Credentials | Notes |
|--------|-------------|-------|
| Compustat (WRDS) | WRDS account | [Register](https://wrds-www.wharton.upenn.edu/) |
| CPI (FRED) | FRED API key | [Get key](https://fred.stlouisfed.org/docs/api/api_key.html) |
| PPI (BLS) | None | Public data |

## Project Structure

```
src/PyMarkup/
├── core/              # Data preparation, markup calculation, figures
├── data/              # Data downloaders and loaders
├── estimators/        # WooldridgeIV, CostShare, ACF estimators
├── pipeline/          # MarkupPipeline orchestrator, config
├── decomposition/     # Olley-Pakes decomposition
├── io/                # I/O schemas (Pydantic)
└── cli/               # CLI commands
```

## License

MIT License
