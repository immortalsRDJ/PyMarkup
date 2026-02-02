"""Main markup estimation pipeline orchestrator."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from PyMarkup.core.data_preparation import create_compustat_panel
from PyMarkup.core.figures import plot_aggregate_markup, plot_markup_vs_ppi, prepare_scatter_data
from PyMarkup.core.markup_calculation import compute_markups
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
            self.estimators["wooldridge_iv"] = WooldridgeIVEstimator(
                specification=self.config.estimator.iv_specification,
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

        self.panel_data = create_compustat_panel(
            compustat_path=self.config.compustat_path,
            macro_path=self.config.macro_vars_path,
            include_interest_cogs=self.config.include_interest_cogs,
            trim_percentiles=self.config.trim_percentiles,
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
                markups = compute_markups(
                    elasticities=elast,
                    panel_data=self.panel_data,
                    cost_share_type="cogs_only",  # TODO: Make configurable
                )
                all_markups[name] = markups
                logger.info(f"✓ {name}: computed markups for {len(markups)} firm-years")

                if self.config.save_intermediate:
                    output_path = self.config.output_dir / "intermediate" / f"markups_{name}.csv"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    markups.to_csv(output_path, index=False)

            except Exception as exc:
                logger.error(f"✗ {name} failed: {exc}")

        return all_markups

    def run_figures(
        self,
        all_markups: dict[str, pd.DataFrame],
        ppi_data: pd.DataFrame | None = None,
        cpi_data: pd.DataFrame | None = None,
    ) -> None:
        """
        Generate figures from markup results.

        Step 4: Produces Figure 1 (aggregate markup time series) and optionally
        Figure 2 (CAGR of PPI vs markup scatter, if PPI/CPI data provided).

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

        for name, markups in all_markups.items():
            # Figure 1: Aggregate markup time series
            logger.info(f"\nFigure 1 ({name}): Aggregate markup time series")
            try:
                fig1 = plot_aggregate_markup(
                    markups,
                    title=f"Aggregate Markup ({name})",
                    save_path=fig_dir / f"aggregate_markup_{name}.pdf",
                )
                plt.close(fig1)
                logger.info(f"  Saved aggregate_markup_{name}.pdf")
            except Exception as exc:
                logger.error(f"  Figure 1 ({name}) failed: {exc}")

            # Figure 2: PPI vs markup scatter (needs PPI + CPI)
            if ppi_data is not None and cpi_data is not None and self.panel_data is not None:
                logger.info(f"\nFigure 2 ({name}): PPI vs markup scatter")
                try:
                    scatter = prepare_scatter_data(
                        markups, self.panel_data, ppi_data, cpi_data,
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
