"""Main markup estimation pipeline orchestrator."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from PyMarkup.core.data_preparation import create_compustat_panel
from PyMarkup.core.figures import (
    compute_aggregate_markup,
    plot_aggregate_markup,
    plot_aggregate_markup_comparison,
    plot_aggregate_markup_single_method,
    plot_markup_vs_ppi,
    prepare_scatter_data,
)
from PyMarkup.core.markup_calculation import compute_markups
from PyMarkup.decomposition import OlleyPakesDecomposition, plot_decomposition
from PyMarkup.estimators import ACFEstimator, CostShareEstimator, WooldridgeIVEstimator
from PyMarkup.io.schemas import MarkupResults
from PyMarkup.pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


class MarkupPipeline:
    """
    End-to-end markup estimation pipeline.

    This class orchestrates the full workflow:
    1. Load and prepare Compustat data
    2. Estimate production function elasticities (using selected method(s))
    3. Compute firm-level markups
    4. Aggregate and save results

    Parameters
    ----------
    config : PipelineConfig
        Pipeline configuration

    Attributes
    ----------
    config : PipelineConfig
        Configuration object
    panel_data : pd.DataFrame
        Prepared Compustat panel (after run_data_preparation)
    estimators : dict
        Dictionary of initialized estimators
    results : MarkupResults
        Estimation results (after run)

    Examples
    --------
    >>> config = PipelineConfig(
    ...     compustat_path="data/compustat.dta",
    ...     macro_vars_path="data/macro_vars.xlsx",
    ... )
    >>> pipeline = MarkupPipeline(config)
    >>> results = pipeline.run()
    >>> results.save("output/")
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.panel_data = None
        self.estimators = {}
        self.results = None
        self._setup_estimators()

    def _setup_estimators(self) -> None:
        """Initialize estimator(s) based on configuration."""
        method = self.config.estimator.method

        if method in ["wooldridge_iv", "all"]:
            iv_spec = self.config.estimator.iv_specification
            if iv_spec == "both":
                # Register one estimator per spec so each produces its own
                # markups_*.csv file (downstream builders / dashboard read both).
                for spec in ("spec1", "spec2"):
                    self.estimators[f"wooldridge_iv_{spec}"] = WooldridgeIVEstimator(
                        specification=spec,
                        window_years=self.config.estimator.window_years,
                        industry_level=self.config.estimator.industry_level,
                        min_observations=self.config.estimator.min_observations,
                    )
            else:
                self.estimators["wooldridge_iv"] = WooldridgeIVEstimator(
                    specification=iv_spec,
                    window_years=self.config.estimator.window_years,
                    industry_level=self.config.estimator.industry_level,
                    min_observations=self.config.estimator.min_observations,
                )

        if method in ["cost_share", "all"]:
            self.estimators["cost_share"] = CostShareEstimator(
                include_sga=self.config.estimator.cs_include_sga,
                aggregation=self.config.estimator.cs_aggregation,
                industry_level=self.config.estimator.industry_level,
            )

        if method in ["acf", "all"]:
            self.estimators["acf"] = ACFEstimator(
                window_years=self.config.estimator.window_years,
                include_market_share=self.config.estimator.acf_include_market_share,
                include_sga=self.config.estimator.acf_include_sga,
                industry_level=self.config.estimator.industry_level,
                min_observations=self.config.estimator.min_observations,
            )

        logger.info(f"Initialized {len(self.estimators)} estimator(s): {list(self.estimators.keys())}")

    def run_data_preparation(self) -> pd.DataFrame:
        """
        Load and prepare Compustat panel data.

        Returns
        -------
        pd.DataFrame
            Cleaned and trimmed panel data
        """
        logger.info("=" * 80)
        logger.info("STEP 1: Data Preparation")
        logger.info("=" * 80)

        # Determine DEU path if using DEU sample
        deu_path = None
        if self.config.use_deu_sample:
            deu_path = self.config.deu_observations_path
            logger.info(f"Using DEU sample filter: {deu_path}")

        self.panel_data = create_compustat_panel(
            compustat_path=self.config.compustat_path,
            macro_path=self.config.macro_vars_path,
            include_interest_cogs=self.config.include_interest_cogs,
            trim_percentiles=self.config.trim_percentiles,
            deu_observations_path=deu_path,
        )

        if self.config.save_intermediate:
            output_path = self.config.output_dir / "intermediate" / "panel_data.csv"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self.panel_data.to_csv(output_path, index=False)
            logger.info(f"Saved intermediate panel data to {output_path}")

        return self.panel_data

    def run_estimation(self) -> dict[str, pd.DataFrame]:
        """
        Run elasticity estimation using configured method(s).

        Returns
        -------
        dict
            Dictionary mapping method name to elasticity DataFrame
        """
        if self.panel_data is None:
            raise RuntimeError("Must call run_data_preparation() first")

        logger.info("=" * 80)
        logger.info("STEP 2: Elasticity Estimation")
        logger.info("=" * 80)

        all_elasticities = {}
        for name, estimator in self.estimators.items():
            logger.info(f"\nRunning {estimator.get_method_name()}...")
            try:
                elasticities = estimator.estimate_elasticities(self.panel_data)
                all_elasticities[name] = elasticities
                logger.info(f"✓ {name}: estimated {len(elasticities)} industry-years")

                if self.config.save_intermediate:
                    output_path = self.config.output_dir / "intermediate" / f"elasticities_{name}.csv"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    elasticities.to_csv(output_path, index=False)

            except Exception as exc:
                logger.error(f"✗ {name} failed: {exc}")

        return all_elasticities

    def run_markup_calculation(self, elasticities: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """
        Compute firm-level markups from elasticities.

        For cost_share method, uses direct firm-level computation under CRS:
            markup = Revenue / (COGS + K)

        For other methods (IV, ACF), merges industry-year elasticities and computes:
            markup = theta / cost_share

        Parameters
        ----------
        elasticities : dict
            Dictionary mapping method name to elasticity DataFrame

        Returns
        -------
        dict
            Dictionary mapping method name to firm-level markup DataFrame
        """
        logger.info("=" * 80)
        logger.info("STEP 3: Markup Calculation")
        logger.info("=" * 80)

        all_markups = {}
        for name, elast in elasticities.items():
            logger.info(f"\nComputing markups for {name}...")
            try:
                # Cost share: use direct firm-level computation under CRS
                if name == "cost_share" and "cost_share" in self.estimators:
                    markups = self.estimators["cost_share"].compute_firm_markups(
                        data=self.panel_data,
                        apply_trim=True,
                    )
                    logger.info(f"✓ {name}: computed direct firm-level markups for {len(markups)} firm-years")
                else:
                    # IV and ACF: merge industry-year theta and compute markup
                    markups = compute_markups(
                        elasticities=elast,
                        panel_data=self.panel_data,
                    )
                    logger.info(f"✓ {name}: computed markups for {len(markups)} firm-years")

                all_markups[name] = markups

                if self.config.save_intermediate:
                    output_path = self.config.output_dir / "intermediate" / f"markups_{name}.csv"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    markups.to_csv(output_path, index=False)

            except Exception as exc:
                logger.error(f"✗ {name} failed: {exc}")

        # If both IV specs were estimated, expose spec2 under the "wooldridge_iv"
        # key as well so figure/decomposition steps (which hardcode that name)
        # still work without code changes.
        if "wooldridge_iv_spec2" in all_markups and "wooldridge_iv" not in all_markups:
            all_markups["wooldridge_iv"] = all_markups["wooldridge_iv_spec2"]

        return all_markups

    def run_figures(
        self,
        all_markups: dict[str, pd.DataFrame],
        ppi_data: pd.DataFrame | None = None,
        cpi_data: pd.DataFrame | None = None,
    ) -> None:
        """
        Generate figures from markup results.

        Step 4: Produces Figure 1 (aggregate markup time series comparing all methods)
        and optionally Figure 2 (CAGR of PPI vs markup scatter, if PPI/CPI data provided).

        Parameters
        ----------
        all_markups : dict
            Dictionary mapping method name to firm-level markup DataFrame.
        ppi_data : pd.DataFrame, optional
            PPI data with columns: ind2d, year, ppi.
        cpi_data : pd.DataFrame, optional
            CPI data with columns: year, CPI.
        """
        logger.info("=" * 80)
        logger.info("STEP 4: Figure Generation")
        logger.info("=" * 80)

        fig_dir = self.config.output_dir / "figures"
        fig_dir.mkdir(parents=True, exist_ok=True)
        intermediate_dir = self.config.output_dir / "intermediate"
        intermediate_dir.mkdir(parents=True, exist_ok=True)

        # Load DLEU benchmark (external reference data)
        dleu_path = Path("Intermediate/For Figure 1") / "Aggregate Markups by DLEU.csv"
        agg_markup_dleu = None

        if dleu_path.exists():
            try:
                agg_markup_dleu = pd.read_csv(dleu_path)
                logger.info(f"Loaded DLEU benchmark from {dleu_path}")
            except Exception as e:
                logger.warning(f"Could not load DLEU benchmark: {e}")

        # Compute and save aggregate markups for each method
        logger.info("\nComputing aggregate markups for each method...")
        for name, markups in all_markups.items():
            try:
                # All firms
                agg_all = compute_aggregate_markup(
                    markups, self.panel_data,
                    weight_type=self.config.aggregation_weight,
                    ppi_matched_only=False,
                )
                agg_all.to_csv(intermediate_dir / f"agg_markup_annual_{name}.csv", index=False)
                logger.info(f"  Saved agg_markup_annual_{name}.csv")

                # PPI-matched firms only
                if ppi_data is not None:
                    agg_ppi = compute_aggregate_markup(
                        markups, self.panel_data,
                        weight_type=self.config.aggregation_weight,
                        ppi_matched_only=True,
                        ppi_data=ppi_data,
                    )
                    agg_ppi.to_csv(intermediate_dir / f"agg_markup_ppi_matched_{name}.csv", index=False)
                    logger.info(f"  Saved agg_markup_ppi_matched_{name}.csv")
            except Exception as exc:
                logger.error(f"  Aggregate computation for {name} failed: {exc}")

        # Figure 1: Separate plot for each method (IV and Cost Share only)
        # Each plot has 3 lines: DLEU, Replication, Firms Matched to PPI
        methods_to_plot = ["wooldridge_iv", "cost_share"]
        method_labels = {
            "wooldridge_iv": "Wooldridge IV",
            "cost_share": "Cost Share",
        }

        for method_name in methods_to_plot:
            if method_name not in all_markups:
                continue

            markups = all_markups[method_name]
            label = method_labels.get(method_name, method_name)
            logger.info(f"\nFigure 1 ({label}): Aggregate markup time series")

            try:
                year_min = int(markups["year"].min())
                year_max = int(markups["year"].max())
                filename = f"Aggregate Markup Comparison - {label} ({year_min}-{year_max}, Annual).pdf"

                fig = plot_aggregate_markup_single_method(
                    firm_markups=markups,
                    panel_data=self.panel_data,
                    method_name=label,
                    agg_markup_dleu=agg_markup_dleu,
                    ppi_data=ppi_data,
                    weight_type=self.config.aggregation_weight,
                    year_range=(year_min, year_max),
                    save_path=fig_dir / filename,
                )
                plt.close(fig)
                logger.info(f"  Saved {filename}")
            except Exception as exc:
                logger.error(f"  Figure 1 ({label}) failed: {exc}")

        # Figure 2: PPI vs markup scatter (for each method)
        if ppi_data is not None and cpi_data is not None and self.panel_data is not None:
            for name, markups in all_markups.items():
                logger.info(f"\nFigure 2 ({name}): PPI vs markup scatter")
                try:
                    scatter = prepare_scatter_data(
                        markups,
                        self.panel_data,
                        ppi_data,
                        cpi_data,
                    )
                    if len(scatter) > 0:
                        fig2 = plot_markup_vs_ppi(
                            scatter,
                            title=f"Growth of PPI and Markup ({name})",
                            save_path=fig_dir / f"ppi_vs_markup_{name}.pdf",
                        )
                        plt.close(fig2)
                        logger.info(f"  Saved ppi_vs_markup_{name}.pdf")
                    else:
                        logger.warning(f"  No scatter data for {name}")
                except Exception as exc:
                    logger.error(f"  Figure 2 ({name}) failed: {exc}")

    def run_download(
        self,
        skip_compustat: bool = False,
        skip_cpi: bool = False,
        skip_ppi: bool = False,
    ) -> dict:
        """
        Download data from WRDS, FRED, and BLS.

        Parameters
        ----------
        skip_compustat : bool
            Skip Compustat download (requires WRDS credentials)
        skip_cpi : bool
            Skip CPI download (requires FRED API key)
        skip_ppi : bool
            Skip PPI download (no credentials needed)

        Returns
        -------
        dict
            Dictionary mapping source name to (annual_path, quarterly_path)
        """
        from PyMarkup.data import download_all

        logger.info("=" * 80)
        logger.info("STEP 0: Data Download")
        logger.info("=" * 80)

        data_config = self.config.to_data_config()
        return download_all(
            config=data_config,
            skip_compustat=skip_compustat,
            skip_cpi=skip_cpi,
            skip_ppi=skip_ppi,
        )

    def _load_price_indices(self) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
        """
        Load PPI and CPI data if available.

        Returns
        -------
        tuple
            (ppi_data, cpi_data) - either may be None if file not found
        """
        from PyMarkup.data.loaders import load_cpi, load_ppi

        ppi_path = self.config.data_dir / "PPI" / "PPI_annual.csv"
        cpi_path = self.config.data_dir / "CPI" / "CPI_annual.csv"

        ppi_data = None
        cpi_data = None

        if ppi_path.exists():
            try:
                ppi_data = load_ppi(ppi_path)
                logger.info(f"Loaded PPI data from {ppi_path}")
            except Exception as e:
                logger.warning(f"Could not load PPI data: {e}")

        if cpi_path.exists():
            try:
                cpi_data = load_cpi(cpi_path)
                logger.info(f"Loaded CPI data from {cpi_path}")
            except Exception as e:
                logger.warning(f"Could not load CPI data: {e}")

        return ppi_data, cpi_data

    def run_decomposition(
        self,
        all_markups: dict[str, pd.DataFrame],
    ) -> dict[str, pd.DataFrame]:
        """
        Run Olley-Pakes decomposition on firm-level markups.

        Decomposes aggregate markup changes into:
        - Within: Changes within continuing firms
        - Reallocation: Market share shifts
        - Net Entry: Entry/exit effects

        Parameters
        ----------
        all_markups : dict
            Dictionary mapping method name to firm-level markup DataFrame.

        Returns
        -------
        dict
            Dictionary mapping method name to decomposition results DataFrame.
        """
        logger.info("=" * 80)
        logger.info("STEP 5: Olley-Pakes Decomposition")
        logger.info("=" * 80)

        fig_dir = self.config.output_dir / "figures"
        fig_dir.mkdir(parents=True, exist_ok=True)
        intermediate_dir = self.config.output_dir / "intermediate"
        intermediate_dir.mkdir(parents=True, exist_ok=True)

        # Run decomposition for IV and Cost Share only
        methods_to_decompose = ["wooldridge_iv", "cost_share"]
        method_labels = {
            "wooldridge_iv": "Wooldridge IV",
            "cost_share": "Cost Share",
        }

        all_decompositions = {}

        for method_name in methods_to_decompose:
            if method_name not in all_markups:
                continue

            markups = all_markups[method_name]
            label = method_labels.get(method_name, method_name)
            logger.info(f"\nDecomposition ({label})...")

            try:
                # Prepare data for decomposition
                # Need: gvkey, year, markup, sale (for weights)
                decomp_data = markups.merge(
                    self.panel_data[["gvkey", "year", "sale_D"]],
                    on=["gvkey", "year"],
                    how="left",
                )

                # Remove rows with missing values
                decomp_data = decomp_data.dropna(subset=["markup", "sale_D"])
                decomp_data = decomp_data[decomp_data["markup"] > 0]
                decomp_data = decomp_data[decomp_data["markup"] < 50]  # Remove extreme outliers

                # Compute base period aggregate markup (revenue-weighted)
                # Use decomposition_start_year (default 1980) as in DLEU Figure IV
                start_year = self.config.decomposition_start_year
                base_data = decomp_data[decomp_data["year"] == start_year]
                if base_data.empty:
                    # Fall back to earliest available year
                    start_year = int(decomp_data["year"].min())
                    base_data = decomp_data[decomp_data["year"] == start_year]
                    logger.warning(
                        f"  Start year {self.config.decomposition_start_year} not in data, "
                        f"falling back to {start_year}"
                    )
                base_total_sales = base_data["sale_D"].sum()
                base_markup = (base_data["markup"] * base_data["sale_D"]).sum() / base_total_sales
                logger.info(f"  Base year {start_year} aggregate markup: {base_markup:.4f}")

                # Run decomposition
                op = OlleyPakesDecomposition(
                    firm_var="gvkey",
                    time_var="year",
                    markup_var="markup",
                    weight_var="sale_D",
                )
                decomp_results = op.decompose(decomp_data)
                all_decompositions[method_name] = decomp_results

                # Save results
                decomp_results.to_csv(intermediate_dir / f"decomposition_{method_name}.csv")
                logger.info(f"  Saved decomposition_{method_name}.csv")

                # Generate plot (cumulative values with base markup level)
                # Use start_year to match DLEU Figure IV (all lines begin at
                # base_markup in 1980)
                year_max = int(decomp_results.index.max())
                filename = f"Decomposition - {label} ({start_year}-{year_max}).pdf"

                fig = plot_decomposition(
                    decomp_results,
                    cumulative=True,
                    base_markup=base_markup,
                    start_year=start_year,
                    title=f"Decomposition of Markup Growth - {label}",
                    save_path=fig_dir / filename,
                )
                plt.close(fig)
                logger.info(f"  Saved {filename}")

            except Exception as exc:
                logger.error(f"  Decomposition ({label}) failed: {exc}")

        return all_decompositions

    def run(self) -> MarkupResults:
        """
        Execute the full pipeline.

        Returns
        -------
        MarkupResults
            Results object containing markups, elasticities, and metadata
        """
        logger.info("\n" + "=" * 80)
        logger.info("PyMarkup Pipeline")
        logger.info("=" * 80)

        # Step 1: Data preparation
        self.run_data_preparation()

        # Step 2: Estimation
        all_elasticities = self.run_estimation()

        # Step 3: Markup calculation
        all_markups = self.run_markup_calculation(all_elasticities)

        # Create and store MarkupResults object
        logger.info("\n" + "=" * 80)
        logger.info("Pipeline completed successfully!")
        logger.info("=" * 80)

        self.results = MarkupResults.from_pipeline(
            markups=all_markups,
            elasticities=all_elasticities,
            config=self.config,
        )

        return self.results

    def run_all(
        self,
        download: bool = True,
        skip_compustat: bool = False,
        skip_cpi: bool = False,
        skip_ppi: bool = False,
        generate_figures: bool = True,
    ) -> MarkupResults:
        """
        Execute the complete end-to-end pipeline.

        This method runs all steps in sequence:
        1. Download data (optional)
        2. Data preparation
        3. Elasticity estimation
        4. Markup calculation
        5. Figure generation (optional)
        6. Olley-Pakes decomposition (optional)

        Parameters
        ----------
        download : bool
            Whether to run data download step (default True)
        skip_compustat : bool
            Skip Compustat download (use existing data)
        skip_cpi : bool
            Skip CPI download (use existing data)
        skip_ppi : bool
            Skip PPI download (use existing data)
        generate_figures : bool
            Whether to generate output figures (default True)

        Returns
        -------
        MarkupResults
            Results object containing markups, elasticities, and metadata

        Examples
        --------
        >>> config = PipelineConfig(
        ...     compustat_path="Input/DLEU/Compustat_annual.dta",
        ...     macro_vars_path="Input/DLEU/macro_vars_new.xlsx",
        ...     fred_api_key="your-key",
        ... )
        >>> pipeline = MarkupPipeline(config)
        >>> results = pipeline.run_all(download=True, generate_figures=True)
        """
        logger.info("\n" + "=" * 80)
        logger.info("PyMarkup Full Pipeline")
        logger.info("=" * 80)

        # Step 0: Download (optional)
        if download:
            self.run_download(
                skip_compustat=skip_compustat,
                skip_cpi=skip_cpi,
                skip_ppi=skip_ppi,
            )

        # Steps 1-3: Core pipeline
        results = self.run()

        # Step 4: Figures (optional)
        if generate_figures:
            ppi_data, cpi_data = self._load_price_indices()
            self.run_figures(results.firm_markups, ppi_data, cpi_data)

        # Step 5: Decomposition
        if generate_figures:
            self.run_decomposition(results.firm_markups)

        return results
