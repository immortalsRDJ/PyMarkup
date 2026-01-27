# Markup Decomposition Guide

## Overview

The decomposition module allows you to analyze **how** aggregate markup changes over time by breaking down the total change into interpretable components. This is crucial for understanding whether markup increases are driven by:
- Firms raising their own markups (within-firm changes)
- Market share shifting to high-markup firms (reallocation)
- New high-markup firms entering the market
- Low-markup firms exiting

## Available Decomposition Methods

PyMarkup provides two well-established decomposition methods from the productivity literature:

### 1. Foster-Haltiwanger-Krizan (FHK) Decomposition

**Best for**: Detailed analysis of markup dynamics with rich firm entry/exit data

The FHK decomposition breaks aggregate markup changes into **5 components**:

```
Δ Aggregate Markup = Within + Between + Cross + Entry - Exit
```

- **Within**: Markup changes within continuing firms (holding market shares constant)
- **Between**: Reallocation effects (market share shifting among continuing firms based on initial markup levels)
- **Cross**: Covariance term (correlation between markup changes and share changes)
- **Entry**: Contribution of new entrants
- **Exit**: Contribution of exiting firms

**Reference**: Foster, Haltiwanger, and Krizan (2001)

### 2. Melitz-Polanec Decomposition

**Best for**: Simpler analysis focusing on surviving vs. new/exiting firms

The Melitz-Polanec decomposition is a cleaner alternative with **3 components**:

```
Δ Aggregate Markup = Surviving + Entry - Exit
```

- **Surviving**: All changes among firms that survive from period t to t+1
- **Entry**: Contribution of new entrants
- **Exit**: Contribution of exiting firms

**Reference**: Melitz and Polanec (2015)

## Quick Start

### Basic FHK Decomposition

```python
import pandas as pd
from PyMarkup.decomposition import FHKDecomposition, plot_decomposition

# Load your firm-level markup data
# Required columns: gvkey (firm), year, markup, sale (weight)
firm_markups = pd.read_csv("firm_markups.csv")

# Run decomposition
fhk = FHKDecomposition()
results = fhk.decompose(firm_markups)

print(results)
#         within  between  cross  entry  exit  aggregate_change
# year
# 2020     0.05     0.02   0.01   0.03  0.02             0.09
# 2021     0.04     0.03   0.01   0.02  0.01             0.09

# Visualize
fig = plot_decomposition(results, decomp_type="fhk", save_path="decomp_fhk.png")
```

### Basic Melitz Decomposition

```python
from PyMarkup.decomposition import MelitzDecomposition

melitz = MelitzDecomposition()
results = melitz.decompose(firm_markups)

print(results)
#         surviving  entry  exit  aggregate_change
# year
# 2020        0.06   0.03  0.02             0.07
# 2021        0.07   0.02  0.01             0.08

fig = plot_decomposition(results, decomp_type="melitz")
```

## Detailed Usage

### 1. Preparing Your Data

Decomposition requires **firm-level panel data** with these columns:

| Column | Description | Example |
|--------|-------------|---------|
| **gvkey** | Firm identifier | "001076" |
| **year** | Time period | 2020 |
| **markup** | Firm markup | 1.25 |
| **sale** | Weight (typically sales) | 1000000 |

**Important**:
- Data must be a **balanced or unbalanced panel** (firms can enter/exit)
- Missing values will raise an error
- Weights should be positive (typically sales or revenue)

```python
# Example: Load from MarkupResults
from PyMarkup import MarkupPipeline, PipelineConfig

pipeline = MarkupPipeline(config)
results = pipeline.run()

# Get firm-level markups
firm_markups = results.firm_markups["wooldridge_iv"]

# Ensure required columns
assert all(col in firm_markups.columns for col in ["gvkey", "year", "markup"])

# Add weight column if needed
if "sale" not in firm_markups.columns:
    # Merge with original Compustat data
    firm_markups = firm_markups.merge(compustat[["gvkey", "year", "sale"]], on=["gvkey", "year"])
```

### 2. Customizing Variable Names

If your data uses different column names:

```python
fhk = FHKDecomposition(
    firm_var="company_id",      # Instead of "gvkey"
    time_var="fiscal_year",     # Instead of "year"
    markup_var="price_cost_margin",  # Instead of "markup"
    weight_var="revenue"        # Instead of "sale"
)
```

### 3. Aggregate Markup Trends

Calculate aggregate (weighted average) markups before decomposition:

```python
from PyMarkup.decomposition import aggregate_markup_trends

# Overall aggregate
trends = aggregate_markup_trends(firm_markups)
print(trends)
#      year  aggregate_markup  total_weight  n_firms  min_markup  max_markup
# 0    2015            1.15     5.2e+09       1532      0.85        3.21
# 1    2016            1.18     5.5e+09       1589      0.82        3.45

# By industry
industry_trends = aggregate_markup_trends(
    firm_markups,
    group_var="industry"
)
```

### 4. Growth Rate Analysis

```python
from PyMarkup.decomposition.aggregate import calculate_growth_rates

# Calculate various growth metrics
trends_growth = calculate_growth_rates(trends)
print(trends_growth[["year", "aggregate_markup", "growth_rate", "cumulative_growth", "cagr"]])
#      year  aggregate_markup  growth_rate  cumulative_growth  cagr
# 0    2015            1.15         NaN                0.00   0.00
# 1    2016            1.18        2.61                2.61   2.61
# 2    2017            1.22        3.39                6.09   3.00
```

### 5. Advanced Visualization

```python
from PyMarkup.decomposition import (
    plot_decomposition,
    plot_component_contributions,
    plot_aggregate_with_decomposition
)

# Stacked bar chart (default)
fig1 = plot_decomposition(
    results,
    decomp_type="fhk",
    title="Markup Decomposition: Manufacturing Sector",
    figsize=(14, 7),
    save_path="figures/decomp_manufacturing.png"
)

# Component contributions as lines
fig2 = plot_component_contributions(
    results,
    components=["within", "between", "entry", "exit"],
    title="Component Evolution Over Time",
    save_path="figures/components_lines.png"
)

# Combined aggregate + decomposition
fig3 = plot_aggregate_with_decomposition(
    trends,
    results,
    decomp_type="fhk",
    save_path="figures/full_decomposition.png"
)
```

## Interpreting Results

### What Do the Components Mean?

#### FHK Decomposition

1. **Within Component (Δμ effect)**
   - Measures markup changes **within** continuing firms
   - Positive → Firms are increasing their markups
   - **Formula**: Σ s_it · Δμ_it (where s_it = base period share, Δμ_it = markup change)

2. **Between Component (reallocation effect)**
   - Measures market share reallocation based on **initial** markup levels
   - Positive → High-markup firms are gaining market share
   - **Formula**: Σ (μ_it - μ̄) · Δs_it (where μ̄ = mean markup, Δs_it = share change)

3. **Cross Component (covariance)**
   - Captures correlation between markup changes and share changes
   - Positive → Firms that increase markups are also gaining market share
   - **Formula**: Σ Δμ_it · Δs_it

4. **Entry Component**
   - Contribution of new firms entering the market
   - Positive if entrants have above-average markups
   - **Formula**: Σ (μ_it+1 - μ̄_t) · s_it+1 for entrants

5. **Exit Component**
   - Contribution of firms exiting the market
   - Positive (increases aggregate) if low-markup firms exit
   - **Formula**: -Σ (μ_it - μ̄_t) · s_it for exiters

#### Melitz Decomposition

1. **Surviving Component**
   - **All** changes among continuing firms (combines Within + Between + Cross from FHK)
   - Cleaner but less detailed than FHK

2. **Entry/Exit**
   - Same interpretation as FHK

### Example Interpretations

**Case 1: Rising markups driven by within-firm increases**
```
        within  between  cross  entry  exit  aggregate_change
2020     0.08    -0.01   0.00   0.01  0.01             0.09
```
→ Most of the 0.09 increase comes from firms raising their own markups (0.08)
→ Slight negative reallocation (-0.01) toward low-markup firms
→ Entry/exit have small effects

**Case 2: Rising markups driven by reallocation**
```
        within  between  cross  entry  exit  aggregate_change
2020     0.02     0.05   0.02   0.01  0.00             0.10
```
→ Market share is shifting to high-markup firms (0.05)
→ Positive cross term (0.02) suggests growing high-markup firms are also increasing markups
→ Limited within-firm markup growth (0.02)

**Case 3: Rising markups driven by entry**
```
        within  between  cross  entry  exit  aggregate_change
2020    -0.01     0.00   0.00   0.08  0.02             0.09
```
→ New entrants have markups far above incumbents (0.08)
→ Low-markup firms are exiting (0.02)
→ Incumbent firms are actually lowering markups (-0.01)

## Integration with MarkupPipeline

### End-to-End Example

```python
from pathlib import Path
from PyMarkup import MarkupPipeline, PipelineConfig, EstimatorConfig
from PyMarkup.decomposition import FHKDecomposition, plot_decomposition
import pandas as pd

# Step 1: Estimate markups
config = PipelineConfig(
    compustat_path="data/compustat.dta",
    macro_vars_path="data/macro_vars.xlsx",
    estimator=EstimatorConfig(method="wooldridge_iv"),
    output_dir="output/"
)

pipeline = MarkupPipeline(config)
results = pipeline.run()

# Step 2: Get firm-level markups
firm_markups = results.firm_markups["wooldridge_iv"]

# Step 3: Add weights (sales)
compustat = pd.read_stata("data/compustat.dta")
firm_markups = firm_markups.merge(
    compustat[["gvkey", "fyear", "sale"]],
    left_on=["gvkey", "year"],
    right_on=["gvkey", "fyear"]
)

# Step 4: Run decomposition
fhk = FHKDecomposition()
decomp_results = fhk.decompose(firm_markups)

# Step 5: Save results
decomp_results.to_csv("output/decomposition_results.csv")

# Step 6: Generate plots
plot_decomposition(
    decomp_results,
    decomp_type="fhk",
    save_path="output/decomposition.png"
)

# Step 7: Summary statistics
summary = fhk.summary(decomp_results)
print(f"Total markup change: {summary['total_change']:.3f}")
print("Component contributions:")
for comp, vals in summary["component_contributions"].items():
    print(f"  {comp}: {vals['percentage_contribution']:.1f}%")
```

## Best Practices

### 1. Data Quality

- **Remove outliers** before decomposition (extreme markups can distort results)
- **Use consistent weights** across all periods (typically sales or revenue)
- **Check for data errors**: Negative markups, missing firms, etc.

```python
# Clean data before decomposition
firm_markups = firm_markups[
    (firm_markups["markup"] > 0) &     # Positive markups
    (firm_markups["markup"] < 5) &     # Remove extreme values
    (firm_markups["sale"] > 0)         # Positive sales
]
```

### 2. Time Period Selection

- **Short periods**: Year-to-year changes can be noisy
- **Long periods**: Multi-year averages smooth out fluctuations
- **Consider**: 3-year or 5-year rolling windows

```python
# Example: 3-year averages
firm_markups_3yr = (
    firm_markups
    .sort_values(["gvkey", "year"])
    .groupby("gvkey")
    .rolling(window=3, on="year")
    .mean()
    .reset_index()
)
```

### 3. Industry-Level Analysis

Run decomposition separately by industry for richer insights:

```python
# Decompose each industry separately
industries = firm_markups["naics_2d"].unique()

decomp_by_industry = {}
for ind in industries:
    ind_data = firm_markups[firm_markups["naics_2d"] == ind]
    decomp_by_industry[ind] = fhk.decompose(ind_data)

# Compare across industries
for ind, result in decomp_by_industry.items():
    print(f"\nIndustry {ind}:")
    print(result[["within", "between", "entry", "exit"]].mean())
```

## Troubleshooting

### Error: "Missing required columns"

```python
# Check your data
print(firm_markups.columns)
# Make sure it has: gvkey, year, markup, sale (or your custom names)
```

### Error: "Need at least 2 time periods"

```python
# Check number of periods
print(firm_markups["year"].nunique())
# Must have >= 2 periods for decomposition
```

### Warning: Large "cross" component

- Large cross terms suggest correlated markup and share changes
- This is economically interesting! (e.g., successful firms raising prices)
- Not necessarily an error

### Zero or NaN results

```python
# Check if firms actually change between periods
continuing = set(
    firm_markups[firm_markups["year"] == 2020]["gvkey"]
) & set(
    firm_markups[firm_markups["year"] == 2021]["gvkey"]
)
print(f"Continuing firms: {len(continuing)}")

# If few continuing firms, results may be dominated by entry/exit
```

## References

### Academic Papers

1. **Foster, Lucia, John Haltiwanger, and C. J. Krizan. 2001.**
   "Aggregate Productivity Growth: Lessons from Microeconomic Evidence."
   *New Developments in Productivity Analysis*, University of Chicago Press.

2. **Melitz, Marc J., and Sašo Polanec. 2015.**
   "Dynamic Olley-Pakes Productivity Decomposition with Entry and Exit."
   *RAND Journal of Economics* 46 (2): 362–75.

3. **De Loecker, Jan, Jan Eeckhout, and Gabriel Unger. 2020.**
   "The Rise of Market Power and the Macroeconomic Implications."
   *Quarterly Journal of Economics* 135 (2): 561–644.

### Related PyMarkup Documentation

- [Quickstart Guide](quickstart.md)
- [API Reference](api_reference.md)
- [Methodology](methodology.md)
- [Data Requirements](data_requirements.md)

## Advanced Topics

### Custom Decomposition

You can create your own decomposition by subclassing `BaseDecomposition`:

```python
from PyMarkup.decomposition.base import BaseDecomposition
import pandas as pd

class MyCustomDecomposition(BaseDecomposition):
    def decompose(self, data: pd.DataFrame) -> pd.DataFrame:
        self.validate_data(data)
        data = self._calculate_shares(data)

        # Your custom decomposition logic here
        # ...

        return results_df
```

### Weighted Regression Decomposition

For decomposing markup trends using regression-based methods:

```python
import statsmodels.api as sm

# Regression of markup on size quintiles
firm_markups["size_quintile"] = pd.qcut(
    firm_markups["sale"],
    q=5,
    labels=["Q1", "Q2", "Q3", "Q4", "Q5"]
)

model = sm.WLS(
    firm_markups["markup"],
    pd.get_dummies(firm_markups[["year", "size_quintile"]]),
    weights=firm_markups["sale"]
).fit()
```

### Bootstrap Confidence Intervals

For statistical significance of decomposition components:

```python
import numpy as np
from scipy import stats

def bootstrap_decomposition(data, n_bootstrap=1000):
    results = []
    for i in range(n_bootstrap):
        # Resample firms (with replacement)
        firms = data["gvkey"].unique()
        sampled_firms = np.random.choice(firms, size=len(firms), replace=True)
        sample_data = data[data["gvkey"].isin(sampled_firms)]

        # Run decomposition
        fhk = FHKDecomposition()
        decomp = fhk.decompose(sample_data)
        results.append(decomp)

    # Calculate confidence intervals
    results_df = pd.concat(results)
    ci_lower = results_df.groupby(level=0).quantile(0.025)
    ci_upper = results_df.groupby(level=0).quantile(0.975)

    return ci_lower, ci_upper
```
