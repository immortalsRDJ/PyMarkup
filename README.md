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

## Pipeline Overview

```
Data Download → Data Preparation → Elasticity Estimation (θ) → Markup Calculation → Decomposition
```

### 1. Data Download

Download raw data from external sources:

- **Compustat** (WRDS) — firm-level financials (sales, COGS, PPE, NAICS)
- **CPI** (FRED) — consumer price index
- **PPI** (BLS) — producer price index

### 2. Data Preparation

Loads Compustat and macro variables, then:

- Cleans duplicates, extracts 2/3/4-digit NAICS codes
- Deflates all values by GDP (e.g. `sale_D`, `cogs_D`, `capital_D`)
- Computes market shares by industry-year
- Trims outliers at 1st/99th percentiles

**Output:** cleaned firm-year panel with deflated variables and market shares.

### 3. Elasticity Estimation (Theta)

Estimates **output elasticity w.r.t. COGS (θ_c)** at the industry-year level using one of three methods:

| Method | Approach |
|--------|----------|
| **Wooldridge IV** | IV/2SLS with rolling windows; lagged COGS as instrument to address endogeneity |
| **Cost Share** | Direct accounting: θ_c = COGS / (COGS + capital expense); no estimation needed |
| **ACF** | Two-stage GMM with control function; handles selection and simultaneity bias |

Typical values: θ_c ≈ 0.7–0.8, θ_k ≈ 0.1–0.2.

### 4. Markup Calculation

Merges industry-level elasticities onto the firm-level panel and computes:

```
Markup = θ_c / Cost_Share
where Cost_Share = COGS / (COGS + capital_expense [+ SG&A])
```

- **Markup > 1** — price exceeds marginal cost (market power)
- **Markup ≈ 1** — competitive pricing

### 5. Decomposition (Optional)

Decomposes aggregate markup changes over time:

- **FHK** (Foster-Haltiwanger-Krizan) — within-firm + reallocation + entry/exit
- **Melitz-Polanec** — alternative reallocation methodology

### Output Files

```
Intermediate/
├── elasticities_wooldridge_iv.csv   # θ estimates by industry-year
├── elasticities_cost_share.csv
├── elasticities_acf.csv
├── markups_wooldridge_iv.csv        # Firm-level markups
├── markups_cost_share.csv
└── markups_acf.csv
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
