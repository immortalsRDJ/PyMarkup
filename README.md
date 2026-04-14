# PyMarkup

[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://pymarkup.streamlit.app/)
[![PyPI](https://img.shields.io/pypi/v/Pymkp)](https://pypi.org/project/Pymkp/)

A Python toolkit for estimating firm-level markups using production function-based marginal cost recovery.

**[Live Dashboard](https://pymarkup.streamlit.app/)** | **[PyPI](https://pypi.org/project/Pymkp/)**

## Installation

```bash
pip install Pymkp
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

## License

MIT License
