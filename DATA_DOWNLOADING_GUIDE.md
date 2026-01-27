# Data Downloading Process - Complete Guide

## Overview

PyMarkup estimates firm-level markups using production function-based methods. To do this, it requires **three types of data**:

1. **Compustat** - Firm-level financial data (revenues, costs, capital)
2. **CPI** - Consumer Price Index for deflating to real values
3. **PPI** - Producer Price Index for industry-specific deflators

This guide explains how each dataset is downloaded, processed, and prepared for markup estimation.

---

## Quick Summary

| Data Source | Provider | Purpose | Output Files | Update Frequency |
|------------|----------|---------|--------------|------------------|
| **Compustat** | WRDS | Firm financials (sales, COGS, capital) | `Compustat_annual.dta`<br>`Compustat_quarterly.dta` | Annual/Quarterly |
| **CPI** | FRED | Economy-wide price deflator | `CPI_annual.csv`<br>`CPI_quarterly.csv` | Monthly |
| **PPI** | BLS | Industry-specific price deflators | `PPI_annual.csv`<br>`PPI_quarterly.csv` | Monthly |

---

## 1. Compustat: Firm Financial Data

### What is Compustat?

Compustat is a comprehensive database of financial statement data for publicly traded companies in North America. It's provided by S&P Global through the **Wharton Research Data Services (WRDS)** platform.

### What Data Do We Download?

**Annual Data (`comp.funda`):**
- **Identifiers**: `gvkey` (firm ID), `naics` (industry code)
- **Revenue & Costs**: `sale` (sales), `cogs` (cost of goods sold), `xsga` (selling, general & admin expenses)
- **Capital**: `ppegt` (gross PP&E), `ppent` (net PP&E)
- **Other**: `xlr` (labor expenses), `xrd` (R&D), `emp` (employment), `mkvalt` (market value)

**Quarterly Data (`comp.fundq`):**
- Similar variables with quarterly frequency (e.g., `saleq`, `cogsq`, `ppegtq`)

### How the Download Works

```python
from PyMarkup.data import download_compustat

# Download requires WRDS credentials
download_compustat(
    output_dir="Input/DLEU/",
    wrds_username="your_username"  # Optional if configured
)
```

**Step-by-step process:**

1. **Connect to WRDS**: Establishes secure connection using your WRDS credentials
   ```python
   db = wrds.Connection(wrds_username=username)
   ```

2. **Download NAICS codes**: Gets industry classification for each firm
   ```sql
   SELECT gvkey, naics FROM comp.company
   ```

3. **Download Annual Data**: Pulls financial statements with filters
   ```sql
   SELECT gvkey, fyear, sale, cogs, ppegt, ...
   FROM comp.funda
   WHERE consol = 'C'      -- Consolidated statements only
     AND popsrc = 'D'      -- Domestic companies
     AND datafmt = 'STD'   -- Standardized format
   ```

4. **Download Quarterly Data**: Same filters, quarterly frequency
   ```sql
   SELECT gvkey, fyearq, fqtr, saleq, cogsq, ppegtq, ...
   FROM comp.fundq
   WHERE consol = 'C' AND popsrc = 'D' AND datafmt = 'STD'
   ```

5. **Merge NAICS codes**: Adds industry classification to financial data
   ```python
   df = pd.merge(df_fund, naics, on=['gvkey'], how='left')
   ```

6. **Save as Stata files**: Outputs to `.dta` format
   - `Input/DLEU/Compustat_annual.dta` (~500MB, 300k+ firm-years)
   - `Input/DLEU/Compustat_quarterly.dta` (~1GB, 1M+ firm-quarters)

### Data Filters Applied

- **Consolidated (C)**: Only consolidated financial statements (no subsidiaries separately)
- **Domestic (D)**: Primary data source is domestic filings
- **Standard (STD)**: Standardized accounting format (not restated)

These filters ensure consistency and avoid double-counting.

### Requirements

- **WRDS Account**: Requires institutional access (typically through university)
- **Python Package**: `pip install wrds`
- **First-time Setup**: Run `import wrds; wrds.Connection()` to configure credentials

### Example Output Structure

**Compustat_annual.dta:**
```
   gvkey  fyear  naics    sale      cogs    ppegt   xsga
0  001000  2020  334111  50000.0  30000.0  20000.0  5000.0
1  001000  2021  334111  55000.0  32000.0  22000.0  5500.0
2  001004  2020  311111  10000.0   6000.0   8000.0  1000.0
...
```

---

## 2. CPI: Consumer Price Index

### What is CPI?

The Consumer Price Index measures the average change in prices paid by urban consumers for a market basket of consumer goods and services. It's published by the **U.S. Bureau of Labor Statistics (BLS)** and available through the **Federal Reserve Economic Data (FRED)** API.

### Why Do We Need CPI?

Financial data in Compustat is in **nominal dollars** (current prices). To compare across time, we need to convert to **real dollars** (constant prices). CPI provides the economy-wide deflator.

### How the Download Works

```python
from PyMarkup.data import download_cpi

download_cpi(
    output_dir="Input/CPI/",
    fred_api_key="your_fred_api_key"
)
```

**Step-by-step process:**

1. **Connect to FRED API**: Uses your API key
   ```python
   from fredapi import Fred
   fred = Fred(api_key=fred_api_key)
   ```

2. **Download CPI Series**: Fetches monthly CPI data (series ID: `CPIAUCSL`)
   ```python
   cpi_data = fred.get_series('CPIAUCSL')
   ```
   - `CPIAUCSL` = "Consumer Price Index for All Urban Consumers"
   - Monthly frequency from 1947 to present
   - Base period: 1982-84 = 100

3. **Create Annual File**: **January values only** (to match fiscal year convention)
   ```python
   df_annual = df[df.month == 1][['year', 'CPI']]
   ```
   - Saved as `Input/CPI/CPI_annual.csv`

4. **Create Quarterly File**: Quarter-start months (Jan, Apr, Jul, Oct)
   ```python
   # Q1 = January, Q2 = April, Q3 = July, Q4 = October
   df['quarter'] = df['year'].astype(str) + 'Q' + df['quarter'].astype(str)
   ```
   - Saved as `Input/CPI/CPI_quarterly.csv`

### Requirements

- **FRED API Key**: Free, obtain at https://fred.stlouisfed.org/docs/api/api_key.html
- **Python Package**: `pip install fredapi`
- **Internet Connection**: Downloads ~50KB of data

### Example Output

**CPI_annual.csv:**
```csv
year,CPI
2018,251.107
2019,255.657
2020,258.811
2021,271.696
2022,292.655
```

**CPI_quarterly.csv:**
```csv
quarter,CPI
2020Q1,258.811
2020Q2,256.394
2020Q3,260.388
2020Q4,261.582
2021Q1,263.014
```

### Usage in Pipeline

```python
# Deflate sales to real values
df['sale_real'] = df['sale'] / (df['CPI'] / 100)

# Deflate to 2012 dollars
cpi_2012 = cpi_df[cpi_df['year'] == 2012]['CPI'].iloc[0]
df['sale_2012'] = df['sale'] * (cpi_2012 / df['CPI'])
```

---

## 3. PPI: Producer Price Index

### What is PPI?

The Producer Price Index measures the average change in prices received by domestic producers for their output. Unlike CPI (consumer prices), PPI tracks **wholesale/producer prices** at the industry level.

### Why Do We Need PPI?

While CPI is an economy-wide deflator, different industries experience different price changes. For example:
- Tech industry (semiconductors): Prices **decline** over time
- Healthcare: Prices **increase** faster than CPI
- Energy: Volatile price swings

PPI provides **industry-specific deflators** (by NAICS code) for more accurate real value calculations.

### How the Download Works

```python
from PyMarkup.data import download_ppi

download_ppi(
    output_dir="Input/PPI/",
    use_browser=True  # Use browser automation to download
)
```

**Step-by-step process:**

1. **Download Raw Data from BLS**: Uses Playwright browser automation
   ```python
   # Downloads from: https://download.bls.gov/pub/time.series/pc/
   # File: pc.data.0.Current.txt (~100MB text file)
   ```
   - Contains PPI for **all industries** and **all months** (1980s-present)
   - Format: Tab-separated text file

2. **Parse Raw Data**: Read as DataFrame
   ```python
   df = pd.read_csv(input_path, sep=r"\s+", dtype=str)
   # Columns: series_id, year, period, value
   ```

3. **Extract NAICS Codes**: Parse from series_id
   ```python
   # series_id format: PCU123456--123456--
   #                      ^^^^^^ = NAICS code (with dashes)
   df['naics_code'] = df['series_id'].str.slice(3, 9).str.replace('-', '')
   ```

4. **Filter Valid Industries**: Keep 2-6 digit NAICS codes only
   ```python
   df = df[df['naics_code'].str.match(r'^\d{2,6}$')]
   ```
   - Removes aggregate series and invalid codes

5. **Filter Quarter-End Months**: Keep M03, M06, M09, M12 only
   ```python
   valid_months = ['M03', 'M06', 'M09', 'M12']
   df = df[df['period'].isin(valid_months)]
   ```
   - Matches quarterly Compustat data frequency

6. **Map to Quarters**:
   ```python
   month_to_q = {'M03': 1, 'M06': 2, 'M09': 3, 'M12': 4}
   df['quarter'] = df['period'].map(month_to_q)
   df['date'] = df['year'] + 'Q' + df['quarter'].astype(str)
   ```

7. **Create Annual Dataset**: December (M12) values only
   ```python
   df_annual = df[df['period'] == 'M12'][['year', 'naics_code', 'PPI']]
   ```

8. **Merge with Old Data**: Combine with historical PPI (pre-1980s)
   ```python
   # If PPI_annual_old.csv exists, merge to extend coverage back to 1980s
   df_a = pd.concat([old_a, df_a]).drop_duplicates(['naics_code', 'year'])
   ```

9. **Save Processed Files**:
   - `Input/PPI/PPI_annual.csv` (~5MB, 50k+ industry-years)
   - `Input/PPI/PPI_quarterly.csv` (~20MB, 200k+ industry-quarters)

### Requirements

- **Python Package**: `pip install playwright`
- **Browser Setup**: `playwright install chromium`
- **Disk Space**: ~150MB for raw + processed files
- **Alternative**: Set `use_browser=False` and manually download `pc.data.0.Current.txt`

### Example Output

**PPI_annual.csv:**
```csv
year,naics_code,PPI
2018,11,102.3
2018,21,89.5
2018,22,104.7
2018,23,108.1
2019,11,98.7
2019,21,95.2
```

**PPI_quarterly.csv:**
```csv
year,quarter,naics_code,PPI,date
2020,1,11,100.0,2020Q1
2020,2,11,101.5,2020Q2
2020,3,11,103.2,2020Q3
2020,4,11,105.0,2020Q4
```

### NAICS Code Hierarchy

PPI provides deflators at multiple industry aggregation levels:
- **2-digit**: Major sectors (e.g., `11` = Agriculture, `31-33` = Manufacturing)
- **3-digit**: Subsectors (e.g., `311` = Food Manufacturing)
- **4-digit**: Industry groups (e.g., `3111` = Animal Food Manufacturing)
- **5-6 digit**: Specific industries (e.g., `311111` = Dog and Cat Food Manufacturing)

### Usage in Pipeline

```python
# Merge PPI with Compustat on industry code
df = pd.merge(
    compustat_df,
    ppi_df,
    left_on=['naics', 'year'],
    right_on=['naics_code', 'year'],
    how='left'
)

# Deflate industry-specific values
df['sale_D'] = df['sale'] / (df['PPI'] / 100)
df['cogs_D'] = df['cogs'] / (df['PPI'] / 100)
```

---

## Complete Download Workflow

### Option 1: Using Python API

```python
from pathlib import Path
from PyMarkup.data import download_compustat, download_cpi, download_ppi

# Set up directories
data_dir = Path("Input")
data_dir.mkdir(exist_ok=True)

# 1. Download Compustat (requires WRDS credentials)
print("Downloading Compustat...")
download_compustat(
    output_dir=data_dir / "DLEU",
    wrds_username="myuser"
)

# 2. Download CPI (requires FRED API key)
print("Downloading CPI...")
download_cpi(
    output_dir=data_dir / "CPI",
    fred_api_key="YOUR_FRED_API_KEY"
)

# 3. Download PPI (requires internet + browser)
print("Downloading PPI...")
download_ppi(
    output_dir=data_dir / "PPI",
    use_browser=True
)

print("All downloads complete!")
```

### Option 2: Using Original Scripts

```bash
# Run from project root
cd /path/to/PyMarkup

# 1. Compustat
python src/PyMarkup/0.0\ Download\ Compustat.py

# 2. CPI
python src/PyMarkup/0.1\ Download\ CPI.py

# 3. PPI
python src/PyMarkup/0.2\ PPI\ Data\ Preparation.py
```

### Option 3: Future CLI (planned)

```bash
# Download all data sources
pymarkup download all \
    --wrds-username myuser \
    --fred-api-key YOUR_KEY \
    --output Input/

# Or individual sources
pymarkup download compustat --wrds-username myuser
pymarkup download cpi --fred-api-key YOUR_KEY
pymarkup download ppi
```

---

## Directory Structure After Download

```
PyMarkup/
├── Input/
│   ├── DLEU/
│   │   ├── Compustat_annual.dta        # ~500 MB
│   │   ├── Compustat_quarterly.dta     # ~1 GB
│   │   └── macro_vars_new.xlsx         # Manual: GDP, user cost
│   │
│   ├── CPI/
│   │   ├── CPI_annual.csv              # ~10 KB
│   │   └── CPI_quarterly.csv           # ~30 KB
│   │
│   ├── PPI/
│   │   ├── pc.data.0.Current.txt       # ~100 MB (raw BLS data)
│   │   ├── PPI_annual.csv              # ~5 MB
│   │   ├── PPI_quarterly.csv           # ~20 MB
│   │   ├── PPI_annual_old.csv          # Historical data (1980s)
│   │   └── PPI_quarterly_old.csv       # Historical data (1980s)
│   │
│   └── Other/
│       └── NAICS_2D_Description.xlsx   # Manual: Industry names
│
└── src/PyMarkup/
    └── data/
        ├── downloaders.py              # Download functions
        └── loaders.py                  # Load functions
```

**Total disk space required: ~1.7 GB**

---

## How Downloaded Data Flows Through the Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA DOWNLOADING                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Compustat (WRDS)          CPI (FRED)           PPI (BLS)      │
│  ↓                         ↓                    ↓               │
│  Firm financials           Economy deflator     Industry deflat│
│  (nominal $)               (base=100)           (base=100)      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                  DATA PREPARATION (Step 1)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Merge Compustat + CPI + PPI by (firm, industry, year)      │
│  2. Deflate to real values:                                     │
│     - sale_D = sale / (PPI/100)                                 │
│     - cogs_D = cogs / (PPI/100)                                 │
│     - capital_D = ppegt / CPI                                   │
│  3. Create logs: ln(sale_D), ln(cogs_D), ln(capital_D)         │
│  4. Create lags: ln(cogs_D)_lag1, ln(capital_D)_lag1           │
│  5. Filter outliers (trim 1st/99th percentiles)                │
│                                                                 │
│  Output: Prepared panel (Intermediate/compustat_trimmed.csv)   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│               ELASTICITY ESTIMATION (Step 2)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  For each industry-year window (5-year rolling):                │
│                                                                 │
│  Estimate: ln(sale_D) = θ_c·ln(cogs_D) + θ_k·ln(capital_D) + ε │
│                                                                 │
│  Using IV/GMM with instrument = ln(cogs_D)_lag1                 │
│                                                                 │
│  Output: θ_c, θ_k by (industry, year)                           │
│          (Intermediate/theta_estimates.csv)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                 MARKUP CALCULATION (Step 3)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  For each firm-year:                                            │
│                                                                 │
│  1. Get θ_c from industry-year estimate                         │
│  2. Calculate cost_share = cogs_D / (cogs_D + capital_D)        │
│  3. Compute markup = θ_c / cost_share                           │
│                                                                 │
│  Output: Firm-level markups (Output/firm_markups.csv)          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Compustat Download Issues

**Error: "WRDS connection failed"**
- **Solution**: Check WRDS credentials
  ```python
  import wrds
  db = wrds.Connection()  # Will prompt for username/password
  ```
- First-time users need to set up `.pgpass` file (WRDS will guide you)

**Error: "No data returned"**
- Check your WRDS subscription includes Compustat
- Verify you have access to `comp.funda` and `comp.fundq` tables

### CPI Download Issues

**Error: "FRED API key invalid"**
- Get a free API key: https://fred.stlouisfed.org/docs/api/api_key.html
- Store in `path_plot_config.py`: `fred_apikey = "YOUR_KEY"`

**Error: "Series not found"**
- Ensure series ID is `CPIAUCSL` (case-sensitive)

### PPI Download Issues

**Error: "playwright not installed"**
- Install with: `pip install playwright && playwright install chromium`

**Error: "Download timeout"**
- BLS server may be slow, increase timeout or retry
- Alternative: Manually download from https://download.bls.gov/pub/time.series/pc/

**Error: "Browser launch failed"**
- Try headless mode: `browser = p.chromium.launch(headless=True)`
- Or download manually and use `use_browser=False`

---

## Data Update Schedule

| Dataset | Update Frequency | When to Re-download |
|---------|------------------|---------------------|
| **Compustat** | Quarterly (with lag) | Every 3-6 months for recent data |
| **CPI** | Monthly | Every 1-3 months for recent deflators |
| **PPI** | Monthly | Every 1-3 months for recent deflators |

**Note**: Historical data (pre-2020) rarely changes, so re-downloading is mainly for extending time coverage.

---

## Next Steps

After downloading data:

1. **Verify downloads**:
   ```python
   from PyMarkup.data import load_compustat, load_cpi, load_ppi

   df_comp = load_compustat(Path("Input/DLEU/Compustat_annual.dta"))
   df_cpi = load_cpi(Path("Input/CPI/"), frequency="annual")
   df_ppi = load_ppi(Path("Input/PPI/"), frequency="annual")

   print(f"Compustat: {len(df_comp)} observations")
   print(f"CPI: {df_cpi['year'].min()}-{df_cpi['year'].max()}")
   print(f"PPI: {df_ppi['naics_code'].nunique()} industries")
   ```

2. **Run the pipeline**:
   ```python
   from PyMarkup import MarkupPipeline, PipelineConfig

   config = PipelineConfig(
       compustat_path="Input/DLEU/Compustat_annual.dta",
       macro_vars_path="Input/DLEU/macro_vars_new.xlsx",
       output_dir="Output/"
   )

   pipeline = MarkupPipeline(config)
   results = pipeline.run()
   ```

3. **Review documentation**:
   - `README.md` - Package overview and API
   - `CLAUDE.md` - Development guide
   - `DATA_MANIFEST.md` - Detailed data documentation

---

## References

- **Compustat**: https://wrds-www.wharton.upenn.edu/pages/get-data/compustat-capital-iq-standard-poors/
- **CPI (FRED)**: https://fred.stlouisfed.org/series/CPIAUCSL
- **PPI (BLS)**: https://www.bls.gov/ppi/
- **Markup Estimation Methodology**: Bond et al. (2021), "Misallocation or Mismeasurement?"
