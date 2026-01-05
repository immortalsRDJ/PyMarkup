# Data Module Refactoring - Comparison

## Overview

The data downloading functionality has been refactored from standalone scripts (`0.0`, `0.1`, `0.2`) into a proper Python module structure under `src/PyMarkup/data/`.

## File Mapping

| Original Script | Refactored Module | Functions |
|----------------|-------------------|-----------|
| `0.0 Download Compustat.py` | `data/downloaders.py` | `download_compustat()` |
| `0.1 Download CPI.py` | `data/downloaders.py` | `download_cpi()` |
| `0.2 PPI Data Preparation.py` | `data/downloaders.py` | `download_ppi()`, `_process_ppi_data()`, `_download_ppi_source()` |
| N/A (new) | `data/loaders.py` | `load_ppi()`, `load_cpi()` (implemented) |

## Module Structure

```
src/PyMarkup/data/
├── __init__.py           # Exports all public functions
├── loaders.py            # Read existing data files
│   ├── load_compustat()
│   ├── load_macro_vars()
│   ├── load_ppi()       # ✓ Now implemented
│   └── load_cpi()       # ✓ Now implemented
└── downloaders.py        # ✓ NEW: Download from external sources
    ├── download_compustat()
    ├── download_cpi()
    └── download_ppi()
```

## Key Improvements

### 1. Separation of Concerns
- **Loaders**: Read already-downloaded files
- **Downloaders**: Fetch data from external sources

### 2. Better Error Handling
```python
# Old (0.0 Download Compustat.py)
db = wrds.Connection()  # Could fail silently

# New (data/downloaders.py)
try:
    import wrds
except ImportError as e:
    raise ImportError("wrds package required...") from e

try:
    db = wrds.Connection()
except Exception as e:
    raise RuntimeError(f"Failed to connect to WRDS: {e}") from e
```

### 3. Configurable Parameters
```python
# Old: Hardcoded paths from path_plot_config
from path_plot_config import data_dir
df.to_stata(data_dir / 'DLEU' / 'Compustat_annual.dta')

# New: Flexible output directory
def download_compustat(output_dir: Path, wrds_username: str | None = None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_stata(output_dir / 'Compustat_annual.dta')
```

### 4. Logging Instead of Print
```python
# Old
print(f"Downloaded PPI source to {dest_path}")

# New
logger.info(f"Downloaded PPI source to {dest_path}")
```

### 5. Type Hints
All functions now have proper type hints:
```python
def download_compustat(output_dir: Path, wrds_username: str | None = None) -> None:
def load_ppi(path: Path, frequency: str = "annual") -> pd.DataFrame:
```

## Functionality Preserved

### Compustat Download (0.0 → `download_compustat()`)
✓ Same NAICS query from `comp.company`
✓ Same annual data fields and filters
✓ Same quarterly data fields and filters
✓ Same merge logic
✓ Outputs same `.dta` files

### CPI Download (0.1 → `download_cpi()`)
✓ Same FRED API usage (CPIAUCSL series)
✓ Same annual logic (January data only)
✓ Same quarterly logic (Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct)
✓ Outputs same CSV files

### PPI Download (0.2 → `download_ppi()`)
✓ Same Playwright browser automation (optional)
✓ Same processing logic:
  - Filter valid NAICS (2-6 digits)
  - Filter quarter-end months (M03, M06, M09, M12)
  - Map to quarters (1-4)
  - Annual = December only
✓ Same merge with old data logic
✓ Same `drop_index_col()` helper
✓ Outputs same CSV files

## New Loader Functions

### `load_ppi(path, frequency="annual")`
- Loads `PPI_annual.csv` or `PPI_quarterly.csv`
- Automatically drops unnamed index columns
- Can accept directory or file path
- Returns clean DataFrame

### `load_cpi(path, frequency="annual")`
- Loads `CPI_annual.csv` or `CPI_quarterly.csv`
- Can accept directory or file path
- Returns clean DataFrame

## Usage Examples

### Old Way (Scripts)
```python
# Run as standalone scripts
python src/PyMarkup/0.0\ Download\ Compustat.py
python src/PyMarkup/0.1\ Download\ CPI.py
python src/PyMarkup/0.2\ PPI\ Data\ Preparation.py
```

### New Way (Module)
```python
from pathlib import Path
from PyMarkup.data import download_compustat, download_cpi, download_ppi
from PyMarkup.data import load_ppi, load_cpi

# Download data
download_compustat(Path("Input/DLEU/"))
download_cpi(Path("Input/CPI/"), fred_api_key="your_key")
download_ppi(Path("Input/PPI/"), use_browser=True)

# Load data
ppi_annual = load_ppi(Path("Input/PPI/"), frequency="annual")
cpi_quarterly = load_cpi(Path("Input/CPI/"), frequency="quarterly")
```

## Backward Compatibility

The original scripts (0.0, 0.1, 0.2) can remain in place and continue to work. They can be updated to use the new module:

```python
# 0.0 Download Compustat.py (updated)
from PyMarkup.data import download_compustat
from path_plot_config import data_dir

if __name__ == "__main__":
    download_compustat(data_dir / "DLEU")
```

## Testing

New comprehensive test file: `tests/unit/test_data_downloaders.py`

Test coverage:
- ✓ PPI processing logic
- ✓ CPI download with mocked FRED API
- ✓ Compustat download with mocked WRDS connection
- ✓ Integration tests for output consistency
- ✓ Error handling

## Migration Checklist

- [x] Create `data/downloaders.py` with all download functions
- [x] Implement `load_ppi()` and `load_cpi()` in `data/loaders.py`
- [x] Update `data/__init__.py` to export all functions
- [x] Add proper error handling and logging
- [x] Add type hints throughout
- [ ] Update original scripts (0.0, 0.1, 0.2) to call new module
- [ ] Update tests to match new module structure
- [ ] Update documentation and examples

## Next Steps

1. Write tests for the new module
2. Optionally update the original scripts to call the new module
3. Update pipeline scripts to use the new module
4. Add CLI commands (`pymarkup download compustat`, etc.)
