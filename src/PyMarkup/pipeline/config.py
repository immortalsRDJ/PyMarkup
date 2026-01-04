"""Configuration dataclasses for markup estimation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml


@dataclass
class EstimatorConfig:
    """
    Configuration for elasticity estimation method.

    Attributes
    ----------
    method : str
        Estimation method: "wooldridge_iv", "cost_share", "acf", or "all"
    iv_specification : str
        Wooldridge IV specification: "spec1" (COGS+K) or "spec2" (+SG&A)
    cs_include_sga : bool
        Cost share: include SG&A in total costs
    cs_aggregation : str
        Cost share: aggregation method ("median", "mean", "weighted_mean")
    acf_include_market_share : bool
        ACF: include market share controls in first stage
    window_years : int
        Rolling window size in years (for IV and ACF)
    industry_level : int
        NAICS digit level (2, 3, or 4)
    min_observations : int
        Minimum observations per window
    """

    method: Literal["wooldridge_iv", "cost_share", "acf", "all"] = "wooldridge_iv"

    # Wooldridge IV settings
    iv_specification: Literal["spec1", "spec2", "both"] = "spec2"

    # Cost share settings
    cs_include_sga: bool = False
    cs_aggregation: Literal["median", "mean", "weighted_mean"] = "median"

    # ACF settings
    acf_include_market_share: bool = True

    # Common settings
    window_years: int = 5
    industry_level: int = 2
    min_observations: int = 15

    def __post_init__(self):
        """Validate configuration."""
        if self.industry_level not in {2, 3, 4}:
            raise ValueError(f"industry_level must be 2, 3, or 4, got {self.industry_level}")
        if self.window_years < 3:
            raise ValueError(f"window_years must be at least 3, got {self.window_years}")
        if self.min_observations < 5:
            raise ValueError(f"min_observations must be at least 5, got {self.min_observations}")


@dataclass
class PipelineConfig:
    """
    Main configuration for markup estimation pipeline.

    Attributes
    ----------
    compustat_path : Path
        Path to Compustat_annual.dta file
    macro_vars_path : Path
        Path to macro_vars_new.xlsx file
    estimator : EstimatorConfig
        Estimator configuration
    include_interest_cogs : bool
        Whether to include interest expense in COGS
    trim_percentiles : tuple[float, float]
        Lower and upper percentiles for sales/COGS trimming
    output_dir : Path
        Directory for output files
    save_intermediate : bool
        Whether to save intermediate datasets

    Examples
    --------
    >>> config = PipelineConfig(
    ...     compustat_path=Path("data/compustat.dta"),
    ...     macro_vars_path=Path("data/macro_vars.xlsx"),
    ...     estimator=EstimatorConfig(method="wooldridge_iv"),
    ... )
    >>> config.save_yaml("config.yaml")
    """

    # Data paths (required)
    compustat_path: Path
    macro_vars_path: Path

    # Estimator configuration
    estimator: EstimatorConfig = field(default_factory=EstimatorConfig)

    # Data processing
    include_interest_cogs: bool = False
    trim_percentiles: tuple[float, float] = (0.01, 0.99)

    # Output
    output_dir: Path = Path("output/")
    save_intermediate: bool = True

    def __post_init__(self):
        """Convert strings to Path objects and validate."""
        self.compustat_path = Path(self.compustat_path)
        self.macro_vars_path = Path(self.macro_vars_path)
        self.output_dir = Path(self.output_dir)

        # Validate percentiles
        if not (0 <= self.trim_percentiles[0] < self.trim_percentiles[1] <= 1):
            raise ValueError(f"Invalid trim_percentiles: {self.trim_percentiles}")

    @classmethod
    def from_yaml(cls, path: Path | str) -> PipelineConfig:
        """
        Load configuration from YAML file.

        Parameters
        ----------
        path : Path or str
            Path to YAML config file

        Returns
        -------
        PipelineConfig
            Configuration object

        Examples
        --------
        >>> config = PipelineConfig.from_yaml("config.yaml")
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        # Handle nested estimator config
        if "estimator" in data and isinstance(data["estimator"], dict):
            data["estimator"] = EstimatorConfig(**data["estimator"])

        return cls(**data)

    def to_yaml(self, path: Path | str) -> None:
        """
        Save configuration to YAML file.

        Parameters
        ----------
        path : Path or str
            Path to save YAML config file

        Examples
        --------
        >>> config.to_yaml("config.yaml")
        """
        data = {
            "compustat_path": str(self.compustat_path),
            "macro_vars_path": str(self.macro_vars_path),
            "estimator": {
                "method": self.estimator.method,
                "iv_specification": self.estimator.iv_specification,
                "cs_include_sga": self.estimator.cs_include_sga,
                "cs_aggregation": self.estimator.cs_aggregation,
                "acf_include_market_share": self.estimator.acf_include_market_share,
                "window_years": self.estimator.window_years,
                "industry_level": self.estimator.industry_level,
                "min_observations": self.estimator.min_observations,
            },
            "include_interest_cogs": self.include_interest_cogs,
            "trim_percentiles": list(self.trim_percentiles),
            "output_dir": str(self.output_dir),
            "save_intermediate": self.save_intermediate,
        }

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_legacy_settings(cls, data_root: Path | None = None) -> PipelineConfig:
        """
        Create config from legacy numbered script settings.

        This method provides backward compatibility with the old pipeline.

        Parameters
        ----------
        data_root : Path, optional
            Root directory (default: auto-detect from current file)

        Returns
        -------
        PipelineConfig
            Configuration matching legacy behavior
        """
        if data_root is None:
            # Auto-detect root
            data_root = Path(__file__).resolve().parents[3]

        return cls(
            compustat_path=data_root / "Input" / "DLEU" / "Compustat_annual.dta",
            macro_vars_path=data_root / "Input" / "DLEU" / "macro_vars_new.xlsx",
            estimator=EstimatorConfig(
                method="all",  # Run all methods for compatibility
                iv_specification="spec2",
                window_years=5,
                industry_level=2,
            ),
            include_interest_cogs=False,
            trim_percentiles=(0.01, 0.99),
            output_dir=data_root / "Output",
            save_intermediate=True,
        )
