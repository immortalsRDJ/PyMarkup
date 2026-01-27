# PyMarkup Test Suite

Comprehensive test suite for PyMarkup package using pytest.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures (sample data)
├── unit/                    # Fast unit tests (~100ms)
│   ├── test_data_loaders.py          # Data loading functions
│   ├── test_io_schemas.py            # InputData and MarkupResults schemas
│   ├── test_wooldridge_estimator.py  # Wooldridge IV estimator
│   ├── test_cost_share_estimator.py  # Cost share estimator
│   └── test_acf_estimator.py         # ACF estimator
│
└── integration/             # Integration tests (~1-5s)
    └── test_pipeline_end_to_end.py   # Full pipeline tests
```

## Running Tests

### Run all tests
```bash
just test
```

### Run specific test file
```bash
just test tests/unit/test_wooldridge_estimator.py
```

### Run specific test class or function
```bash
pytest tests/unit/test_io_schemas.py::TestInputData::test_from_dataframe_success -v
```

### Run with coverage
```bash
just coverage
```

### Run with debugger on failure
```bash
just pdb
```

## Test Categories

### Unit Tests

**Data Loaders** (`test_data_loaders.py`)
- Test loading Compustat data from Stata files
- Test loading macro variables from Excel
- Test error handling for missing files and invalid data
- Test data type validation

**IO Schemas** (`test_io_schemas.py`)
- Test `InputData` schema validation and conversion
- Test `MarkupResults` creation and export
- Test saving results in multiple formats (CSV, Parquet, Stata)
- Test result comparison and plotting methods

**Estimators** (`test_*_estimator.py`)
- Test estimator initialization and parameter validation
- Test data preprocessing steps
- Test elasticity estimation with various configurations
- Test edge cases (empty data, insufficient observations, etc.)
- Test output format and value ranges

### Integration Tests

**Pipeline End-to-End** (`test_pipeline_end_to_end.py`)
- Test full pipeline execution from raw data to final results
- Test pipeline with different estimator methods
- Test configuration validation
- Test error handling for missing files
- Test output file generation

## Fixtures

Key fixtures defined in `conftest.py`:

- `sample_compustat_data`: Synthetic Compustat panel (50 firms, 10 years)
- `sample_macro_vars`: Synthetic macro variables
- `sample_prepared_panel`: Panel data after preprocessing
- `sample_elasticities`: Sample elasticity estimates
- `sample_firm_markups`: Sample markup results
- `temp_compustat_file`: Temporary Stata file with test data
- `temp_macro_vars_file`: Temporary Excel file with test data

## Testing Data Downloads

The data download scripts (`0.0 Download Compustat.py`, etc.) interact with external APIs:
- WRDS for Compustat data
- FRED for CPI data
- BLS for PPI data

**Testing approach:**

1. **Unit tests**: Use mocked API responses to test download logic
2. **Manual tests**: Run download scripts with real credentials (not automated)
3. **Integration tests**: Use pre-downloaded sample data files

Example manual test:
```python
# tests/manual/test_download_compustat.py
import pytest
from PyMarkup.data.downloaders import download_compustat

@pytest.mark.manual
@pytest.mark.requires_wrds
def test_download_compustat_real():
    """Manual test requiring WRDS credentials."""
    download_compustat(output_path="test_output.dta")
    # Verify file exists and has correct structure
```

Run manual tests:
```bash
pytest -m manual  # Only run manual tests
pytest -m "not manual"  # Skip manual tests (default)
```

## Writing New Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test classes: `Test<ClassName>` or `Test<Feature>`
- Test functions: `test_<what_it_tests>`

### Example Test
```python
def test_estimator_validates_input():
    """Test that estimator validates input parameters."""
    with pytest.raises(ValueError, match="industry_level must be"):
        WooldridgeIVEstimator(industry_level=5)
```

### Using Fixtures
```python
def test_load_compustat(temp_compustat_file: Path):
    """Test loading Compustat from fixture file."""
    df = load_compustat(temp_compustat_file)
    assert len(df) > 0
```

## Coverage Requirements

- **Unit tests**: >90% coverage of core logic
- **Integration tests**: All public API methods must be tested
- **Critical paths**: 100% coverage of estimators and pipeline

Check coverage:
```bash
just coverage
# Open htmlcov/index.html in browser
```

## Continuous Integration

Tests run automatically on:
- Every push to main branch
- Every pull request
- Using GitHub Actions with Python 3.10, 3.11, 3.12, 3.13

## Troubleshooting

### Tests fail with "Missing required columns"
- Check that fixtures in `conftest.py` have all required columns
- Verify column names match those expected by the code

### Tests timeout or run slowly
- Use `min_observations=5` in estimator configs for faster tests
- Use smaller sample sizes in fixtures for slow tests

### Import errors
- Ensure package is installed in editable mode: `uv pip install -e .`
- Check that `src/` is in Python path

## Best Practices

1. **Fast tests**: Unit tests should complete in <1 second each
2. **Isolation**: Tests should not depend on each other or external state
3. **Clear assertions**: Use descriptive assertion messages
4. **Fixtures over setup**: Use pytest fixtures instead of setUp/tearDown
5. **Parametrize**: Use `@pytest.mark.parametrize` for similar tests with different inputs
6. **Mock external calls**: Mock API calls, file I/O when testing business logic
7. **Test edge cases**: Empty data, missing values, boundary conditions

## Future Test Additions

Tests to add in future iterations:

- [ ] Regression tests comparing with Stata outputs
- [ ] Property-based tests using Hypothesis
- [ ] Performance benchmarks
- [ ] Tests for CLI commands
- [ ] Tests for data downloaders with mocked APIs
- [ ] Tests for plotting functions
- [ ] Parallel execution tests
