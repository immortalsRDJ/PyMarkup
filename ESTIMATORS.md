# PyMarkup Estimators Documentation

This document provides detailed information about the three production function estimators available in PyMarkup.

## Overview

PyMarkup implements three methods for estimating output elasticities, which are then used to compute firm-level markups:

1. **Wooldridge IV** - Instrumental variables / GMM approach
2. **Cost Share** - Direct accounting approach
3. **ACF** - Ackerberg-Caves-Frazer two-stage GMM

All estimators inherit from the `ProductionFunctionEstimator` abstract base class and implement:
- `estimate_elasticities(data)`: Main estimation method
- `get_method_name()`: Returns human-readable method name

## 1. Wooldridge IV Estimator

### Description

The `WooldridgeIVEstimator` implements a Wooldridge-style instrumental variables approach with GMM estimation. It addresses simultaneity bias in production function estimation by instrumenting current COGS with lagged COGS.

### Method

- **Dependent variable**: log(sales)
- **Endogenous variable**: log(COGS)
- **Instrument**: lagged log(COGS)
- **Controls**: log(capital), investment, capital polynomials, SG&A (optional)

Two specifications are available:
- **Spec 1**: Output = f(COGS, Capital)
- **Spec 2**: Output = f(COGS, Capital, SG&A)

### Implementation

```python
from PyMarkup.estimators import WooldridgeIVEstimator

estimator = WooldridgeIVEstimator(
    specification="spec2",      # "spec1", "spec2", or "both"
    window_years=5,             # Rolling window size (±2 years)
    industry_level=2,           # 2, 3, or 4-digit NAICS
    min_observations=15,        # Min obs per window
)

elasticities = estimator.estimate_elasticities(panel_data)
```

### Parameters

- `specification` (str): Which specification to use
  - `"spec1"`: COGS + capital only
  - `"spec2"`: COGS + capital + SG&A
  - `"both"`: Estimate both, return spec2
- `window_years` (int): Rolling window size in years (default: 5)
- `industry_level` (int): NAICS digit level (2, 3, or 4)
- `min_observations` (int): Minimum observations per window (default: 15)

### Output

Returns DataFrame with columns:
- `ind2d`: Industry code
- `year`: Fiscal year
- `theta_c`: COGS elasticity
- `theta_k`: Capital elasticity

### Pros/Cons

**Pros:**
- Addresses simultaneity bias (COGS choice correlated with productivity)
- Robust to endogeneity issues
- Widely used in empirical IO literature
- Two specifications allow robustness checks

**Cons:**
- Requires valid instruments (assumes lagged COGS exogenous)
- Computationally intensive (many IV regressions)
- May have weak instruments in small samples
- Requires panel data with time variation

### When to Use

- **Research papers**: Preferred method for academic work
- **Endogeneity concerns**: When input choices are correlated with unobservables
- **Panel data available**: Requires firm-level time series
- **Robustness checks**: Compare spec1 vs spec2

---

## 2. Cost Share Estimator

### Description

The `CostShareEstimator` uses a direct accounting approach, computing output elasticities from observed cost shares. Under assumptions of constant returns to scale and perfect competition in input markets, the cost share equals the output elasticity.

### Method

Output elasticity = Cost share = COGS / Total Costs

Where Total Costs = COGS + Capital Expense (+ SG&A optionally)

### Implementation

```python
from PyMarkup.estimators import CostShareEstimator

estimator = CostShareEstimator(
    include_sga=False,          # Include SG&A in total costs?
    aggregation="median",       # "median", "mean", or "weighted_mean"
    industry_level=2,           # 2, 3, or 4-digit NAICS
)

elasticities = estimator.estimate_elasticities(panel_data)
```

### Parameters

- `include_sga` (bool): Whether to include SG&A in total costs (default: False)
- `aggregation` (str): How to aggregate firm-level cost shares
  - `"median"`: Industry-year median (robust to outliers)
  - `"mean"`: Industry-year mean
  - `"weighted_mean"`: Sales-weighted mean
- `industry_level` (int): NAICS digit level (2, 3, or 4)

### Output

Returns DataFrame with columns:
- `ind2d`: Industry code
- `year`: Fiscal year
- `theta_c`: Cost share (COGS elasticity)

Note: No capital elasticity (`theta_k`) since this is a direct calculation.

### Pros/Cons

**Pros:**
- Simple and fast (no estimation, just aggregation)
- No endogeneity concerns (accounting identity)
- Interpretable (direct from financial statements)
- Works with cross-sectional data
- Good for benchmarking other methods

**Cons:**
- Assumes constant returns to scale
- Assumes perfect competition in input markets
- Assumes no adjustment costs
- May not capture dynamic effects
- Sensitive to measurement error in COGS/capital

### When to Use

- **Quick estimates**: Need fast results for many firms/years
- **Benchmarking**: Compare with IV/ACF estimates
- **Cross-sectional analysis**: Don't have panel data
- **Teaching/exploration**: Simple method to understand concepts
- **Data quality check**: Sanity check for other methods

---

## 3. ACF Estimator (Ackerberg-Caves-Frazer)

### Description

The `ACFEstimator` implements the Ackerberg-Caves-Frazer (2015) two-stage GMM estimator. This method addresses both simultaneity bias and selection bias using timing assumptions about input choices.

### Method

**Stage 1**: Estimate productivity proxy via OLS
- φ = output - f(inputs, controls, market share)

**Stage 2**: Recover structural parameters via GMM
- Minimize moment conditions E[ξ · Z] = 0
- Where ξ = innovation in productivity

### Implementation

```python
from PyMarkup.estimators import ACFEstimator

estimator = ACFEstimator(
    window_years=5,                 # Rolling window size
    include_market_share=True,      # Include market share controls?
    industry_level=2,               # 2, 3, or 4-digit NAICS
    min_observations=15,            # Min obs per window
)

elasticities = estimator.estimate_elasticities(panel_data)
```

### Parameters

- `window_years` (int): Rolling window size in years (default: 5)
- `include_market_share` (bool): Include market share controls in first stage (default: True)
- `industry_level` (int): NAICS digit level (2, 3, or 4)
- `min_observations` (int): Minimum observations per window (default: 15)

### Output

Returns DataFrame with columns:
- `ind2d`: Industry code
- `year`: Fiscal year
- `theta_c`: COGS elasticity
- `theta_k`: Capital elasticity

### Pros/Cons

**Pros:**
- Addresses both simultaneity and selection bias
- Uses timing assumptions (more credible than functional form)
- Allows for flexible productivity process
- Well-established in literature (ACF 2015)
- Controls for market structure (market shares)

**Cons:**
- Complex implementation (two-stage GMM)
- Requires numerical optimization (may fail to converge)
- Sensitive to first-stage specification
- Computationally intensive
- Requires market share data

### When to Use

- **Robustness checks**: Verify IV results
- **Selection bias concerns**: When firms exit based on productivity
- **Market structure matters**: When competition affects production
- **Academic research**: Well-cited method in IO
- **Patient estimation**: Have time for optimization

---

## Comparison Table

| Feature | Wooldridge IV | Cost Share | ACF |
|---------|---------------|------------|-----|
| **Speed** | Slow | Very Fast | Slow |
| **Complexity** | Medium | Low | High |
| **Data Requirements** | Panel (lags) | Cross-section OK | Panel (lags) |
| **Endogeneity** | Addresses | Ignores | Addresses |
| **Selection Bias** | No | No | Yes |
| **Assumptions** | Valid instruments | CRTS, perfect comp | Timing, separability |
| **Recommended For** | Research | Benchmarking | Robustness |

## Choosing an Estimator

### Decision Tree

1. **Do you need quick estimates for many firms?**
   - Yes → Use **Cost Share**
   - No → Continue

2. **Is selection bias (firm entry/exit) a concern?**
   - Yes → Use **ACF**
   - No → Continue

3. **Do you have panel data with lagged inputs?**
   - Yes → Use **Wooldridge IV** (preferred)
   - No → Use **Cost Share**

### Best Practices

1. **Start with Cost Share**: Quick sanity check
2. **Main analysis**: Wooldridge IV (spec2 with SG&A)
3. **Robustness**: Compare all three methods
4. **Report all**: Show readers you checked sensitivity

## Common Issues

### Problem: IV estimates are negative or unrealistic

**Solutions:**
- Check data quality (outliers, missing values)
- Increase `min_observations` threshold
- Try spec1 vs spec2
- Verify instrument strength (check first-stage F-stat manually)

### Problem: ACF optimization fails to converge

**Solutions:**
- Increase `min_observations`
- Try without market share controls (`include_market_share=False`)
- Check for numerical issues (very large/small values)
- Verify first-stage regression works

### Problem: Cost shares outside [0,1]

**Solutions:**
- Check for negative COGS or capital expenses
- Verify deflation worked correctly
- Inspect macro variables (USGDP, usercost)

## References

- **Wooldridge (2009)**: "On estimating firm-level production functions using proxy variables to control for unobservables"
- **Ackerberg, Caves, Frazer (2015)**: "Identification properties of recent production function estimators", Econometrica
- **De Loecker & Warzynski (2012)**: "Markups and firm-level export status", American Economic Review

## Example: Running All Three

```python
from PyMarkup.estimators import WooldridgeIVEstimator, CostShareEstimator, ACFEstimator

# Prepare data (from pipeline)
from PyMarkup.core.data_preparation import create_compustat_panel
panel = create_compustat_panel(...)

# Estimate with all three methods
results = {}

# Cost Share (fast baseline)
cs = CostShareEstimator(include_sga=False, aggregation="median")
results["cost_share"] = cs.estimate_elasticities(panel)

# Wooldridge IV (main method)
iv = WooldridgeIVEstimator(specification="spec2", window_years=5)
results["wooldridge_iv"] = iv.estimate_elasticities(panel)

# ACF (robustness)
acf = ACFEstimator(window_years=5, include_market_share=True)
results["acf"] = acf.estimate_elasticities(panel)

# Compare
for method, elast in results.items():
    print(f"{method}: mean theta_c = {elast['theta_c'].mean():.3f}")
```
