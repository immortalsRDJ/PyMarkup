"""Base class for all production function estimators."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ProductionFunctionEstimator(ABC):
    """
    Abstract base class for production function estimators.

    All estimators must implement:
    - estimate_elasticities(): Estimate output elasticities (theta)
    - get_method_name(): Return human-readable method name
    """

    @abstractmethod
    def estimate_elasticities(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Estimate output elasticities from panel data.

        Parameters
        ----------
        data : pd.DataFrame
            Prepared panel data with required variables

        Returns
        -------
        pd.DataFrame
            Elasticity estimates with at minimum columns:
            - ind2d: 2-digit industry code
            - year: fiscal year
            - theta_c: output elasticity w.r.t. COGS
            - theta_k: output elasticity w.r.t. capital (optional)
        """
        pass

    @abstractmethod
    def get_method_name(self) -> str:
        """
        Return human-readable method name.

        Returns
        -------
        str
            Method name (e.g., "Wooldridge IV", "Cost Share", "ACF")
        """
        pass

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(method='{self.get_method_name()}')"

    def save(
        self,
        output_dir: Path | str,
        suffix: str = "",
        format: str = "dta",
    ) -> Path:
        """
        Save estimation results to file.

        Parameters
        ----------
        output_dir : Path or str
            Directory to save results (typically Intermediate/)
        suffix : str
            Suffix for filename (e.g., "DEUSample", "fullSample_intExp")
        format : str
            Output format: "dta" (Stata), "csv", or "parquet"

        Returns
        -------
        Path
            Path to saved file

        Raises
        ------
        ValueError
            If no results to save (estimate_elasticities not called)
        """
        if self.results_ is None:
            raise ValueError("No results to save. Call estimate_elasticities() first.")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get filename from subclass
        filename = self._get_output_filename(suffix, format)
        output_path = output_dir / filename

        # Save based on format
        if format == "dta":
            self.results_.to_stata(output_path, write_index=False)
        elif format == "csv":
            self.results_.to_csv(output_path, index=False)
        elif format == "parquet":
            self.results_.to_parquet(output_path, index=False)
        else:
            raise ValueError(f"Unknown format: {format}. Use 'dta', 'csv', or 'parquet'.")

        logger.info(f"Saved {self.get_method_name()} results to {output_path}")
        return output_path

    def _get_output_filename(self, suffix: str, format: str) -> str:
        """
        Get output filename. Override in subclasses for custom naming.

        Parameters
        ----------
        suffix : str
            Suffix for filename
        format : str
            File format extension

        Returns
        -------
        str
            Filename
        """
        # Default naming - subclasses can override
        method_short = self.get_method_name().split()[0].lower()
        suffix_part = f"_{suffix}" if suffix else ""
        return f"theta_{method_short}{suffix_part}.{format}"
