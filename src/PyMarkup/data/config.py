"""Configuration management for data downloading."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class DataConfig:
    """Configuration for data downloading and paths."""

    # API Keys
    fred_api_key: str = ""
    wrds_username: str = ""

    # Paths
    data_dir: Path = field(default_factory=lambda: Path("Input"))
    intermediate_dir: Path = field(default_factory=lambda: Path("Intermediate"))

    # URLs
    ppi_url: str = "https://download.bls.gov/pub/time.series/pc/pc.data.0.Current"

    @classmethod
    def from_yaml(cls, path: Path | str) -> DataConfig:
        """Load configuration from YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls(
            fred_api_key=data.get("fred_api_key", os.getenv("FRED_API_KEY", "")),
            wrds_username=data.get("wrds_username", os.getenv("WRDS_USERNAME", "")),
            data_dir=Path(data.get("data_dir", "Input")),
            intermediate_dir=Path(data.get("intermediate_dir", "Intermediate")),
            ppi_url=data.get("ppi_url", cls.ppi_url),
        )

    @classmethod
    def from_env(cls) -> DataConfig:
        """Load configuration from environment variables."""
        return cls(
            fred_api_key=os.getenv("FRED_API_KEY", ""),
            wrds_username=os.getenv("WRDS_USERNAME", ""),
        )

    def validate(self, require_wrds: bool = False, require_fred: bool = False) -> None:
        """Validate configuration."""
        if require_wrds and not self.wrds_username:
            raise ValueError("WRDS username required. Set wrds_username in config or WRDS_USERNAME env var.")
        if require_fred and not self.fred_api_key:
            raise ValueError("FRED API key required. Set fred_api_key in config or FRED_API_KEY env var.")


def get_default_config_path() -> Path:
    """Get default config path (project root / config.yaml)."""
    return Path(__file__).resolve().parents[3] / "config.yaml"


def load_config(path: Path | str | None = None) -> DataConfig:
    """Load config from file or environment."""
    if path:
        return DataConfig.from_yaml(path)

    default_path = get_default_config_path()
    if default_path.exists():
        return DataConfig.from_yaml(default_path)

    return DataConfig.from_env()
