"""Main markup estimation pipeline orchestrator."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from PyMarkup.core.data_preparation import create_compustat_panel
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
