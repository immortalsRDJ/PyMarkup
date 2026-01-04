"""Base class for all production function estimators."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


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
