"""Configuration loader for API keys and credentials."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def load_env_file(env_path: Path | None = None) -> dict[str, str]:
    """
    Load environment variables from .env file.

    Parameters
    ----------
    env_path : Path, optional
        Path to .env file. If None, looks for .env in project root.

    Returns
    -------
    dict[str, str]
        Dictionary of environment variables
    """
    if env_path is None:
        # Look for .env in project root (2 levels up from this file)
        project_root = Path(__file__).resolve().parents[2]
        env_path = project_root / ".env"

    if not env_path.exists():
        return {}

    env_vars = {}
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse KEY=VALUE format
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    return env_vars


def load_yaml_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    Load configuration from YAML file.

    Parameters
    ----------
    config_path : Path, optional
        Path to config.yaml. If None, looks for config.yaml in project root.

    Returns
    -------
    dict[str, Any]
        Configuration dictionary
    """
    if config_path is None:
        # Look for config.yaml in project root
        project_root = Path(__file__).resolve().parents[2]
        config_path = project_root / "config.yaml"

    if not config_path.exists():
        return {}

    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


def get_fred_api_key() -> str | None:
    """
    Get FRED API key from environment or config files.

    Checks in order:
    1. Environment variable FRED_API_KEY
    2. .env file
    3. config.yaml

    Returns
    -------
    str or None
        FRED API key if found, None otherwise
    """
    # Check environment variable first
    api_key = os.environ.get("FRED_API_KEY")
    if api_key:
        return api_key

    # Check .env file
    env_vars = load_env_file()
    api_key = env_vars.get("FRED_API_KEY")
    if api_key:
        return api_key

    # Check config.yaml
    config = load_yaml_config()
    api_key = config.get("credentials", {}).get("fred_api_key")
    if api_key and api_key != "your_fred_api_key_here":
        return api_key

    return None


def get_wrds_username() -> str | None:
    """
    Get WRDS username from environment or config files.

    Checks in order:
    1. Environment variable WRDS_USERNAME
    2. .env file
    3. config.yaml

    Returns
    -------
    str or None
        WRDS username if found, None otherwise (will use default WRDS auth)
    """
    # Check environment variable first
    username = os.environ.get("WRDS_USERNAME")
    if username:
        return username

    # Check .env file
    env_vars = load_env_file()
    username = env_vars.get("WRDS_USERNAME")
    if username:
        return username

    # Check config.yaml
    config = load_yaml_config()
    username = config.get("credentials", {}).get("wrds_username")
    if username and username != "your_wrds_username":
        return username

    return None


def get_config() -> dict[str, Any]:
    """
    Get full configuration from environment and config files.

    Returns
    -------
    dict[str, Any]
        Complete configuration dictionary
    """
    config = {
        "credentials": {
            "fred_api_key": get_fred_api_key(),
            "wrds_username": get_wrds_username(),
        }
    }

    # Load additional config from yaml
    yaml_config = load_yaml_config()
    if yaml_config:
        config.update(yaml_config)

    return config
