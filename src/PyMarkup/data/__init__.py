"""Data loading and downloading utilities (internal)."""

from .downloaders import download_compustat, download_cpi, download_ppi
from .loaders import load_compustat, load_cpi, load_macro_vars, load_ppi

__all__ = [
    # Loaders (read existing files)
    "load_compustat",
    "load_macro_vars",
    "load_ppi",
    "load_cpi",
    # Downloaders (fetch from external sources)
    "download_compustat",
    "download_cpi",
    "download_ppi",
]
