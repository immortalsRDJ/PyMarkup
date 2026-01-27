"""Pydantic schemas for input/output validation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, field_validator


class InputData(BaseModel):
    """
    Validated input data container for Compustat panel.

    Attributes
    ----------
    gvkey : pd.Series
        Firm identifier (GVKEY)
    year : pd.Series
        Fiscal year
    sale : pd.Series
        Sales revenue
    cogs : pd.Series
        Cost of goods sold
    ppegt : pd.Series
        Property, plant, and equipment (gross total) - capital stock
    naics : pd.Series
        NAICS industry code
    xsga : pd.Series, optional
        Selling, general, and administrative expenses
    emp : pd.Series, optional
        Number of employees

    Examples
    --------
    >>> data = InputData.from_compustat("data/compustat.dta")
    >>> data = InputData.from_dataframe(df)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Required fields
    gvkey: pd.Series
    year: pd.Series
    sale: pd.Series
    cogs: pd.Series
    ppegt: pd.Series
    naics: pd.Series

    # Optional fields
    xsga: pd.Series | None = None
    emp: pd.Series | None = None

    @field_validator("year")
    @classmethod
    def validate_year_range(cls, v: pd.Series) -> pd.Series:
        """Validate that years are in reasonable range."""
        if v.min() < 1950 or v.max() > 2030:
            raise ValueError(f"Year outside valid range [1950, 2030]: {v.min()}-{v.max()}")
        return v

    @field_validator("sale", "cogs", "ppegt")
    @classmethod
    def validate_positive(cls, v: pd.Series) -> pd.Series:
        """Validate that financial variables are non-negative."""
        if (v < 0).any():
            raise ValueError(f"Found negative values in {v.name}")
        return v

    @classmethod
    def from_compustat(cls, path: Path | str, **kwargs) -> InputData:
        """
        Load and validate from Compustat Stata file.

        Parameters
        ----------
        path : Path or str
            Path to Compustat_annual.dta
        **kwargs
            Additional keyword arguments

        Returns
        -------
        InputData
            Validated input data
        """
        df = pd.read_stata(path)
        return cls.from_dataframe(df)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> InputData:
        """
        Load and validate from pandas DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with required columns

        Returns
        -------
        InputData
            Validated input data
        """
        # Handle year column (might be 'fyear')
        if "year" not in df.columns and "fyear" in df.columns:
            df = df.rename(columns={"fyear": "year"})

        required_cols = {"gvkey", "year", "sale", "cogs", "ppegt", "naics"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        return cls(
            gvkey=df["gvkey"],
            year=df["year"],
            sale=df["sale"],
            cogs=df["cogs"],
            ppegt=df["ppegt"],
            naics=df["naics"],
            xsga=df.get("xsga"),
            emp=df.get("emp"),
        )

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert to pandas DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with all series
        """
        data = {
            "gvkey": self.gvkey,
            "year": self.year,
            "sale": self.sale,
            "cogs": self.cogs,
            "ppegt": self.ppegt,
            "naics": self.naics,
        }

        if self.xsga is not None:
            data["xsga"] = self.xsga
        if self.emp is not None:
            data["emp"] = self.emp

        return pd.DataFrame(data)


class MarkupResults(BaseModel):
    """
    Container for markup estimation results.

    Attributes
    ----------
    firm_markups : dict[str, pd.DataFrame]
        Firm-level markups by estimation method
        Keys: method names ("wooldridge_iv", "cost_share", "acf")
        Values: DataFrames with columns (gvkey, year, markup, theta_c, cost_share)
    elasticities : dict[str, pd.DataFrame]
        Output elasticity estimates by method
        Keys: method names
        Values: DataFrames with columns (ind2d, year, theta_c, theta_k)
    metadata : dict
        Metadata including config, timestamp, method list
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    firm_markups: dict[str, pd.DataFrame]
    elasticities: dict[str, pd.DataFrame]
    metadata: dict[str, Any]

    @classmethod
    def from_pipeline(cls, markups: dict, elasticities: dict, config: Any) -> MarkupResults:
        """
        Create from pipeline outputs.

        Parameters
        ----------
        markups : dict
            Firm-level markups by method
        elasticities : dict
            Elasticity estimates by method
        config : PipelineConfig
            Pipeline configuration

        Returns
        -------
        MarkupResults
            Results container
        """
        metadata = {
            "methods": list(markups.keys()),
            "timestamp": datetime.now().isoformat(),
            "config": config,
        }

        return cls(firm_markups=markups, elasticities=elasticities, metadata=metadata)

    def save(self, output_dir: Path | str, format: str = "csv") -> None:
        """
        Save results to disk.

        Parameters
        ----------
        output_dir : Path or str
            Output directory
        format : str
            Output format ("csv", "parquet", or "stata")
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for method, df in self.firm_markups.items():
            if format == "csv":
                df.to_csv(output_dir / f"markups_{method}.csv", index=False)
            elif format == "parquet":
                df.to_parquet(output_dir / f"markups_{method}.parquet", index=False)
            elif format == "stata":
                df.to_stata(output_dir / f"markups_{method}.dta", write_index=False)
            else:
                raise ValueError(f"Unknown format: {format}")

        for method, df in self.elasticities.items():
            if format == "csv":
                df.to_csv(output_dir / f"elasticities_{method}.csv", index=False)
            elif format == "parquet":
                df.to_parquet(output_dir / f"elasticities_{method}.parquet", index=False)
            elif format == "stata":
                df.to_stata(output_dir / f"elasticities_{method}.dta", write_index=False)

    def compare_methods(self) -> pd.DataFrame:
        """
        Compare summary statistics across estimation methods.

        Returns
        -------
        pd.DataFrame
            Comparison table with rows=methods, columns=stats
        """
        comparison = []
        for method, df in self.firm_markups.items():
            comparison.append(
                {
                    "method": method,
                    "n_firms": df["gvkey"].nunique(),
                    "n_firm_years": len(df),
                    "mean_markup": df["markup"].mean(),
                    "median_markup": df["markup"].median(),
                    "std_markup": df["markup"].std(),
                }
            )
        return pd.DataFrame(comparison)

    def plot_aggregate(self, save_path: Path | str | None = None, method: str | None = None):
        """
        Plot aggregate markup time series.

        Parameters
        ----------
        save_path : Path or str, optional
            Path to save figure
        method : str, optional
            Specific method to plot (if None, plot all methods)

        Returns
        -------
        Figure
            Matplotlib figure
        """
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 6))

        methods_to_plot = [method] if method else list(self.firm_markups.keys())

        for m in methods_to_plot:
            if m not in self.firm_markups:
                continue
            df = self.firm_markups[m]
            agg = df.groupby("year")["markup"].median().reset_index()
            ax.plot(agg["year"], agg["markup"], label=m, marker="o")

        ax.set_xlabel("Year")
        ax.set_ylabel("Median Markup")
        ax.set_title("Aggregate Markup Trends")
        ax.legend()
        ax.grid(True, alpha=0.3)

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")

        return fig
