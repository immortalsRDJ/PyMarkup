# Security Setup - API Keys and Credentials

## Overview

PyMarkup requires API credentials to download data from external sources. To keep your credentials secure, we use configuration files that are **NOT** tracked in version control.

## Quick Setup

### Option 1: Using .env File (Recommended)

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and add your credentials:**
   ```bash
   # FRED API Key (required for CPI download)
   FRED_API_KEY=your_actual_fred_api_key

   # WRDS Username (optional for Compustat download)
   WRDS_USERNAME=your_wrds_username
   ```

3. **Get your API keys:**
   - **FRED API Key**: Free at https://fred.stlouisfed.org/docs/api/api_key.html
   - **WRDS Access**: Requires institutional subscription (typically through university)

### Option 2: Using config.yaml

1. **Copy the example file:**
   ```bash
   cp config.yaml.example config.yaml
   ```

2. **Edit `config.yaml` and add your credentials:**
   ```yaml
   credentials:
     fred_api_key: "your_actual_fred_api_key"
     wrds_username: "your_wrds_username"  # optional
   ```

### Option 3: Environment Variables

Set environment variables in your shell:

```bash
# Bash/Zsh
export FRED_API_KEY="your_fred_api_key"
export WRDS_USERNAME="your_wrds_username"

# Add to ~/.bashrc or ~/.zshrc to make permanent
```

## Priority Order

The configuration system checks for credentials in this order:

1. **Environment variables** (highest priority)
2. **.env file**
3. **config.yaml file**
4. **Default WRDS authentication** (~/.pgpass for WRDS only)

## Files That Are Ignored by Git

These files contain your credentials and are **automatically ignored**:

- `.env` - Your actual environment variables
- `config.yaml` - Your actual configuration
- `config.yml` - Alternative YAML filename
- `.secrets.yaml` - Alternative secrets file

## Files Tracked in Git

These are safe to commit (contain no real credentials):

- `.env.example` - Template with placeholder values
- `config.yaml.example` - Template configuration
- `SECURITY_SETUP.md` - This file

## Verification

Test that your credentials are loaded correctly:

```python
from PyMarkup.config_loader import get_fred_api_key, get_wrds_username

fred_key = get_fred_api_key()
wrds_user = get_wrds_username()

print(f"FRED API Key: {'✓ Found' if fred_key else '✗ Not found'}")
print(f"WRDS Username: {'✓ Found' if wrds_user else '✗ Not found (will use default)'}")
```

## Security Best Practices

### ✅ DO:
- Keep `.env` and `config.yaml` files **private** and **local only**
- Use different API keys for development and production
- Rotate API keys periodically
- Store credentials in password managers
- Use environment variables on servers/CI systems

### ❌ DON'T:
- **Never** commit `.env` or `config.yaml` to version control
- **Never** share API keys in issues, pull requests, or chat
- **Never** hardcode credentials in source code
- **Never** email or message credentials as plain text

## Troubleshooting

### "FRED API key not found" Warning

This means the system couldn't find your API key. Check:

1. **File exists?**
   ```bash
   ls -la .env  # Should show .env file
   ```

2. **File has content?**
   ```bash
   cat .env  # Should show FRED_API_KEY=...
   ```

3. **No typos?**
   - Variable name must be exactly `FRED_API_KEY` (case-sensitive)
   - No spaces around the `=` sign
   - No quotes needed (but ok to use them)

4. **File in correct location?**
   - Should be in project root (same directory as README.md)

### WRDS Connection Fails

For Compustat download, WRDS uses multiple authentication methods:

1. **Username in config** (if provided in .env or config.yaml)
2. **~/.pgpass file** (WRDS default authentication)
3. **Interactive prompt** (will ask for username/password)

On first use, WRDS will help you set up ~/.pgpass:
```python
import wrds
db = wrds.Connection()  # Follow the prompts
```

## Migration from Old Setup

If you had credentials hardcoded in `path_plot_config.py`:

1. **Copy your API key** from the old file
2. **Create `.env` file** and paste it there:
   ```bash
   FRED_API_KEY=your_old_api_key
   ```
3. **Delete the old hardcoded key** (already done in latest version)

The code will automatically use the new config system.

## CI/CD Setup

For GitHub Actions or other CI systems:

1. **Add secrets to your repository:**
   - GitHub: Settings → Secrets → Actions → New repository secret
   - Add `FRED_API_KEY` with your key

2. **Reference in workflow:**
   ```yaml
   - name: Run tests
     env:
       FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
     run: pytest
   ```

## Getting API Keys

### FRED API Key (Free)

1. Visit https://fred.stlouisfed.org/
2. Create a free account
3. Go to https://fred.stlouisfed.org/docs/api/api_key.html
4. Click "Request API Key"
5. Copy the key to your .env file

### WRDS Access (Institutional)

1. Check if your institution subscribes: https://wrds-www.wharton.upenn.edu/
2. Register with your institutional email
3. Request access through your institution's library
4. Follow WRDS setup guide: https://wrds-www.wharton.upenn.edu/pages/support/

## Support

If you have issues with:
- **API key setup**: Check this guide and .env.example
- **FRED access**: Contact FRED support at https://fred.stlouisfed.org/
- **WRDS access**: Contact WRDS support at wrds@wharton.upenn.edu
- **PyMarkup bugs**: Open an issue at https://github.com/immortalsRDJ/PyMarkup/issues

## Example: Complete Setup

Here's a full example of setting up PyMarkup from scratch:

```bash
# 1. Clone the repository
git clone https://github.com/immortalsRDJ/PyMarkup.git
cd PyMarkup

# 2. Install dependencies
pip install -e ".[test]"

# 3. Set up credentials
cp .env.example .env
nano .env  # Edit and add your FRED_API_KEY

# 4. Test the setup
python -c "from PyMarkup.config_loader import get_fred_api_key; print('✓ Setup complete!' if get_fred_api_key() else '✗ API key not found')"

# 5. Download data
python -c "
from pathlib import Path
from PyMarkup.data import download_cpi
from PyMarkup.config_loader import get_fred_api_key

download_cpi(Path('Input/CPI/'), fred_api_key=get_fred_api_key())
print('✓ CPI data downloaded!')
"
```

---

**Remember**: Your `.env` and `config.yaml` files are **automatically ignored by git**. They will never be accidentally committed!
