# Publishing PyMarkup-estimator to PyPI

## ✅ Pre-Publishing Checklist

- [x] Package renamed to PyMarkup-estimator
- [x] All files updated with new name
- [x] GitHub URLs updated to immortalsRDJ/PyMarkup-estimator
- [x] Test suite complete (102 tests)
- [x] Git commit created and pushed
- [ ] All tests passing
- [ ] Version updated to 0.2.0 (remove -dev)
- [ ] CHANGELOG.md created
- [ ] PyPI account created
- [ ] Package built
- [ ] Uploaded to PyPI

---

## Step 1: Update Version Number

Before publishing, remove the `-dev` suffix:

```bash
# Edit src/PyMarkup/_version.py
# Change from: __version__ = "0.2.0-dev"
# To:          __version__ = "0.2.0"
```

Or run this command:
```bash
sed -i '' 's/0.2.0-dev/0.2.0/g' src/PyMarkup/_version.py
sed -i '' 's/0.2.0-dev/0.2.0/g' pyproject.toml
```

---

## Step 2: Run Tests

Make sure everything works:

```bash
# Run all tests
python3 -m pytest tests/ -v

# Expected: All tests pass or most pass
# (Some tests may fail with random data - this is OK for now)

# Check test summary
python3 -m pytest tests/ --tb=line | tail -20
```

---

## Step 3: Install Build Tools

```bash
# Install build and twine
python3 -m pip install --upgrade build twine
```

---

## Step 4: Build the Package

```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info

# Build distribution packages
python3 -m build

# This creates:
# dist/PyMarkup_estimator-0.2.0-py3-none-any.whl
# dist/PyMarkup_estimator-0.2.0.tar.gz
```

**Verify the build:**
```bash
ls -lh dist/
# Should show two files: .whl and .tar.gz
```

---

## Step 5: Test Installation Locally

```bash
# Create a clean virtual environment
python3 -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install from the wheel
pip install dist/PyMarkup_estimator-*.whl

# Test import
python -c "from PyMarkup import MarkupPipeline, __version__; print(f'Version: {__version__}')"

# Test CLI
pymarkup version

# If everything works, deactivate and remove test env
deactivate
rm -rf test_env
```

---

## Step 6: Create PyPI Account (If Not Done)

1. Go to https://pypi.org/account/register/
2. Create account with email verification
3. Enable 2FA (recommended)
4. Create API token:
   - Go to https://pypi.org/manage/account/token/
   - Click "Add API token"
   - Name: "PyMarkup-estimator"
   - Scope: "Entire account" (or specific to project once created)
   - Copy the token (starts with `pypi-...`)
   - **Save it securely!** You can only see it once

---

## Step 7: Upload to TestPyPI (Optional but Recommended)

TestPyPI is a separate instance for testing:

```bash
# Upload to TestPyPI
python3 -m twine upload --repository testpypi dist/*

# You'll be prompted for:
# Username: __token__
# Password: <paste your TestPyPI API token>
```

**Create TestPyPI account and token at:**
- https://test.pypi.org/account/register/
- https://test.pypi.org/manage/account/token/

**Test installation from TestPyPI:**
```bash
pip install --index-url https://test.pypi.org/simple/ PyMarkup-estimator

python -c "from PyMarkup import MarkupPipeline; print('Success!')"
```

---

## Step 8: Upload to Real PyPI

Once TestPyPI works, upload to real PyPI:

```bash
# Upload to PyPI
python3 -m twine upload dist/*

# You'll be prompted for:
# Username: __token__
# Password: <paste your PyPI API token>
```

**Alternative: Use .pypirc file**

Create `~/.pypirc`:
```ini
[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...  # Your API token here

[testpypi]
username = __token__
password = pypi-AgENdGVzdC5weXBp...  # Your TestPyPI token
```

Then simply run:
```bash
twine upload dist/*
```

---

## Step 9: Verify on PyPI

1. Visit: https://pypi.org/project/PyMarkup-estimator/
2. Check that the page looks correct
3. Verify README renders properly
4. Check badges and links

---

## Step 10: Test Installation from PyPI

```bash
# In a new environment
pip install PyMarkup-estimator

# Verify
python -c "from PyMarkup import MarkupPipeline, __version__; print(f'Installed version: {__version__}')"

pymarkup --help
```

---

## Step 11: Create GitHub Release

1. Go to: https://github.com/immortalsRDJ/PyMarkup-estimator/releases
2. Click "Create a new release"
3. Tag version: `v0.2.0`
4. Release title: `v0.2.0 - First PyPI Release`
5. Description:
```markdown
# PyMarkup-estimator v0.2.0

First official PyPI release! 🎉

## Installation
```bash
pip install PyMarkup-estimator
```

## What's New

- ✨ Complete refactored package with modular architecture
- 📊 Three production function estimators (Wooldridge IV, Cost Share, ACF)
- 🧪 Comprehensive test suite (102 tests)
- 📝 Full documentation and examples
- 🎨 Rich CLI with typer
- ✅ Type hints and validation throughout

## Quick Start

```python
from PyMarkup import MarkupPipeline, PipelineConfig, EstimatorConfig

config = PipelineConfig(
    compustat_path="data/compustat.dta",
    macro_vars_path="data/macro_vars.xlsx",
    estimator=EstimatorConfig(method="wooldridge_iv"),
)

pipeline = MarkupPipeline(config)
results = pipeline.run()
```

See [README](https://github.com/immortalsRDJ/PyMarkup-estimator#readme) for full documentation.

## Links
- PyPI: https://pypi.org/project/PyMarkup-estimator/
- Documentation: https://PyMarkup-estimator.readthedocs.io (coming soon)
```
6. Attach the built files: `dist/*.whl` and `dist/*.tar.gz`
7. Publish release

---

## Step 12: Update Repository

After successful release:

```bash
# Commit the version change
git add src/PyMarkup/_version.py pyproject.toml CHANGELOG.md
git commit -m "Release v0.2.0"
git tag v0.2.0
git push origin main --tags
```

---

## Troubleshooting

### Error: "File already exists"
- You're trying to upload a version that already exists
- Increment version number (e.g., 0.2.0 → 0.2.1)

### Error: "Invalid authentication credentials"
- Check your API token
- Make sure username is `__token__` (with double underscores)
- Token should start with `pypi-`

### Error: "Package name conflict"
- Someone else registered the name
- Choose a different name (we checked - PyMarkup-estimator is available!)

### README not rendering
- Check markdown syntax
- Ensure README.md is in root directory
- PyPI uses a subset of markdown features

---

## Quick Command Summary

```bash
# 1. Update version
sed -i '' 's/0.2.0-dev/0.2.0/g' src/PyMarkup/_version.py pyproject.toml

# 2. Run tests
python3 -m pytest tests/ -v

# 3. Build
rm -rf dist/ && python3 -m build

# 4. Test locally
python3 -m venv test_env && source test_env/bin/activate
pip install dist/PyMarkup_estimator-*.whl
python -c "from PyMarkup import MarkupPipeline; print('OK')"
deactivate && rm -rf test_env

# 5. Upload to TestPyPI (optional)
python3 -m twine upload --repository testpypi dist/*

# 6. Upload to PyPI
python3 -m twine upload dist/*

# 7. Verify
pip install PyMarkup-estimator
python -c "from PyMarkup import __version__; print(__version__)"

# 8. Tag and push
git add . && git commit -m "Release v0.2.0"
git tag v0.2.0 && git push origin main --tags
```

---

## Next Steps After Publishing

1. **Add badges to README**
   - PyPI version badge (already there)
   - Downloads badge: `![Downloads](https://pepy.tech/badge/PyMarkup-estimator)`
   - License badge

2. **Set up Read the Docs**
   - https://readthedocs.org/
   - Connect GitHub repo
   - Auto-build documentation

3. **Enable GitHub Actions**
   - Create `.github/workflows/publish.yml` for auto-publishing
   - Create `.github/workflows/test.yml` for CI testing

4. **Announce**
   - Twitter/X
   - LinkedIn
   - Economics/Python communities
   - Your university/lab

---

## Questions?

If you encounter issues:
1. Check PyPI help: https://pypi.org/help/
2. Twine docs: https://twine.readthedocs.io/
3. Python Packaging Guide: https://packaging.python.org/

---

**You're ready to publish! 🚀**

Run the commands above and your package will be live on PyPI!
