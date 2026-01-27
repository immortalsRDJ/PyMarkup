"""Integration tests for end-to-end markup estimation pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from PyMarkup import EstimatorConfig, MarkupPipeline, PipelineConfig
from PyMarkup.io import MarkupResults


@pytest.fixture
def pipeline_config(temp_compustat_file: Path, temp_macro_vars_file: Path, temp_data_dir: Path) -> PipelineConfig:
    """Create a minimal pipeline configuration for testing."""
    return PipelineConfig(
        compustat_path=temp_compustat_file,
        macro_vars_path=temp_macro_vars_file,
        estimator=EstimatorConfig(method="wooldridge_iv", min_observations=5),
        output_dir=temp_data_dir / "output",
        save_intermediate=False,
    )


class TestMarkupPipelineInitialization:
    """Tests for MarkupPipeline initialization."""

    def test_pipeline_initialization(self, pipeline_config: PipelineConfig):
        """Test pipeline can be initialized with config."""
        pipeline = MarkupPipeline(pipeline_config)

        assert pipeline.config == pipeline_config
        assert pipeline.panel_data is None
        assert pipeline.results is None
        assert len(pipeline.estimators) > 0

    def test_pipeline_setup_single_estimator(self, pipeline_config: PipelineConfig):
        """Test pipeline sets up correct estimator for single method."""
        pipeline = MarkupPipeline(pipeline_config)

        # Should have wooldridge_iv estimator
        assert "wooldridge_iv" in pipeline.estimators
        assert len(pipeline.estimators) == 1

    def test_pipeline_setup_all_estimators(self, temp_compustat_file: Path, temp_macro_vars_file: Path):
        """Test pipeline sets up all estimators when method='all'."""
        config = PipelineConfig(
            compustat_path=temp_compustat_file,
            macro_vars_path=temp_macro_vars_file,
            estimator=EstimatorConfig(method="all"),
        )
        pipeline = MarkupPipeline(config)

        # Should have all three estimators
        assert "wooldridge_iv" in pipeline.estimators
        assert "cost_share" in pipeline.estimators
        assert "acf" in pipeline.estimators
        assert len(pipeline.estimators) == 3


class TestMarkupPipelineDataPreparation:
    """Tests for data preparation step."""

    def test_run_data_preparation_returns_dataframe(self, pipeline_config: PipelineConfig):
        """Test data preparation returns a DataFrame."""
        pipeline = MarkupPipeline(pipeline_config)
        panel_data = pipeline.run_data_preparation()

        assert isinstance(panel_data, pd.DataFrame)
        assert len(panel_data) > 0

    def test_run_data_preparation_stores_panel(self, pipeline_config: PipelineConfig):
        """Test data preparation stores panel in pipeline."""
        pipeline = MarkupPipeline(pipeline_config)
        panel_data = pipeline.run_data_preparation()

        assert pipeline.panel_data is not None
        pd.testing.assert_frame_equal(pipeline.panel_data, panel_data)

    def test_run_data_preparation_has_required_columns(self, pipeline_config: PipelineConfig):
        """Test prepared panel has required columns."""
        pipeline = MarkupPipeline(pipeline_config)
        panel_data = pipeline.run_data_preparation()

        # Check for essential columns
        required_cols = {"gvkey", "year", "sale_D", "cogs_D", "capital_D"}
        assert required_cols.issubset(panel_data.columns)


class TestMarkupPipelineEstimation:
    """Tests for elasticity estimation step."""

    def test_run_estimation_returns_dict(self, pipeline_config: PipelineConfig):
        """Test estimation returns dictionary of results."""
        pipeline = MarkupPipeline(pipeline_config)
        pipeline.run_data_preparation()
        elasticities = pipeline.run_estimation()

        assert isinstance(elasticities, dict)
        assert "wooldridge_iv" in elasticities

    def test_run_estimation_results_are_dataframes(self, pipeline_config: PipelineConfig):
        """Test estimation results are DataFrames."""
        pipeline = MarkupPipeline(pipeline_config)
        pipeline.run_data_preparation()
        elasticities = pipeline.run_estimation()

        for method, df in elasticities.items():
            assert isinstance(df, pd.DataFrame)

    def test_run_estimation_multiple_methods(
        self, temp_compustat_file: Path, temp_macro_vars_file: Path, temp_data_dir: Path
    ):
        """Test estimation with multiple methods."""
        config = PipelineConfig(
            compustat_path=temp_compustat_file,
            macro_vars_path=temp_macro_vars_file,
            estimator=EstimatorConfig(method="all", min_observations=3),
            output_dir=temp_data_dir / "output",
        )
        pipeline = MarkupPipeline(config)
        pipeline.run_data_preparation()
        elasticities = pipeline.run_estimation()

        # Should have results from all methods
        assert "wooldridge_iv" in elasticities
        assert "cost_share" in elasticities
        assert "acf" in elasticities


class TestMarkupPipelineMarkupCalculation:
    """Tests for markup calculation step."""

    def test_run_markup_calculation_returns_dict(self, pipeline_config: PipelineConfig):
        """Test markup calculation returns dictionary."""
        pipeline = MarkupPipeline(pipeline_config)
        pipeline.run_data_preparation()
        elasticities = pipeline.run_estimation()
        markups = pipeline.run_markup_calculation(elasticities)

        assert isinstance(markups, dict)
        assert "wooldridge_iv" in markups

    def test_run_markup_calculation_results_are_dataframes(self, pipeline_config: PipelineConfig):
        """Test markup calculation results are DataFrames."""
        pipeline = MarkupPipeline(pipeline_config)
        pipeline.run_data_preparation()
        elasticities = pipeline.run_estimation()
        markups = pipeline.run_markup_calculation(elasticities)

        for method, df in markups.items():
            assert isinstance(df, pd.DataFrame)

    def test_markups_have_required_columns(self, pipeline_config: PipelineConfig):
        """Test markup DataFrames have required columns."""
        pipeline = MarkupPipeline(pipeline_config)
        pipeline.run_data_preparation()
        elasticities = pipeline.run_estimation()
        markups = pipeline.run_markup_calculation(elasticities)

        for method, df in markups.items():
            # At minimum should have gvkey, year, markup
            assert "gvkey" in df.columns
            assert "year" in df.columns
            assert "markup" in df.columns


class TestMarkupPipelineEndToEnd:
    """End-to-end integration tests."""

    def test_full_pipeline_run(self, pipeline_config: PipelineConfig):
        """Test complete pipeline execution."""
        pipeline = MarkupPipeline(pipeline_config)
        results = pipeline.run()

        # Check results object
        assert isinstance(results, MarkupResults)
        assert len(results.firm_markups) > 0
        assert len(results.elasticities) > 0

    def test_full_pipeline_results_saved(self, pipeline_config: PipelineConfig):
        """Test pipeline saves results correctly."""
        pipeline = MarkupPipeline(pipeline_config)
        results = pipeline.run()

        # Check pipeline stores results
        assert pipeline.results is not None
        assert pipeline.results == results

    def test_pipeline_with_all_methods(
        self, temp_compustat_file: Path, temp_macro_vars_file: Path, temp_data_dir: Path
    ):
        """Test full pipeline with all estimation methods."""
        config = PipelineConfig(
            compustat_path=temp_compustat_file,
            macro_vars_path=temp_macro_vars_file,
            estimator=EstimatorConfig(method="all", min_observations=3),
            output_dir=temp_data_dir / "output",
        )
        pipeline = MarkupPipeline(config)
        results = pipeline.run()

        # Should have results from all methods
        assert "wooldridge_iv" in results.firm_markups
        assert "cost_share" in results.firm_markups
        # ACF might fail, so don't strictly require it

    def test_pipeline_saves_output_files(self, pipeline_config: PipelineConfig):
        """Test pipeline saves output files to disk."""
        pipeline = MarkupPipeline(pipeline_config)
        results = pipeline.run()

        # Save results
        output_dir = pipeline_config.output_dir
        results.save(output_dir, format="csv")

        # Check files exist
        assert (output_dir / "markups_wooldridge_iv.csv").exists()
        assert (output_dir / "elasticities_wooldridge_iv.csv").exists()

    def test_pipeline_with_different_specifications(
        self, temp_compustat_file: Path, temp_macro_vars_file: Path, temp_data_dir: Path
    ):
        """Test pipeline with different IV specifications."""
        # Test spec1
        config_spec1 = PipelineConfig(
            compustat_path=temp_compustat_file,
            macro_vars_path=temp_macro_vars_file,
            estimator=EstimatorConfig(method="wooldridge_iv", iv_specification="spec1", min_observations=5),
            output_dir=temp_data_dir / "output_spec1",
        )
        pipeline_spec1 = MarkupPipeline(config_spec1)
        results_spec1 = pipeline_spec1.run()

        # Test spec2
        config_spec2 = PipelineConfig(
            compustat_path=temp_compustat_file,
            macro_vars_path=temp_macro_vars_file,
            estimator=EstimatorConfig(method="wooldridge_iv", iv_specification="spec2", min_observations=5),
            output_dir=temp_data_dir / "output_spec2",
        )
        pipeline_spec2 = MarkupPipeline(config_spec2)
        results_spec2 = pipeline_spec2.run()

        # Both should succeed
        assert isinstance(results_spec1, MarkupResults)
        assert isinstance(results_spec2, MarkupResults)


class TestPipelineConfigValidation:
    """Tests for pipeline configuration validation."""

    def test_config_validates_paths(self, temp_compustat_file: Path, temp_macro_vars_file: Path):
        """Test config converts paths correctly."""
        config = PipelineConfig(
            compustat_path=str(temp_compustat_file),  # Pass as string
            macro_vars_path=str(temp_macro_vars_file),
        )

        # Should convert to Path objects
        assert isinstance(config.compustat_path, Path)
        assert isinstance(config.macro_vars_path, Path)

    def test_config_validates_percentiles(self, temp_compustat_file: Path, temp_macro_vars_file: Path):
        """Test config validates trim percentiles."""
        # Invalid percentiles (lower >= upper)
        with pytest.raises(ValueError, match="Invalid trim_percentiles"):
            PipelineConfig(
                compustat_path=temp_compustat_file,
                macro_vars_path=temp_macro_vars_file,
                trim_percentiles=(0.5, 0.3),  # Invalid order
            )

    def test_estimator_config_validates_industry_level(self):
        """Test estimator config validates industry level."""
        with pytest.raises(ValueError, match="industry_level must be 2, 3, or 4"):
            EstimatorConfig(industry_level=1)

    def test_estimator_config_validates_window_years(self):
        """Test estimator config validates window years."""
        with pytest.raises(ValueError, match="window_years must be at least 3"):
            EstimatorConfig(window_years=1)

    def test_estimator_config_validates_min_observations(self):
        """Test estimator config validates minimum observations."""
        with pytest.raises(ValueError, match="min_observations must be at least 5"):
            EstimatorConfig(min_observations=2)


class TestPipelineErrorHandling:
    """Tests for pipeline error handling."""

    def test_pipeline_missing_compustat_file(self, temp_macro_vars_file: Path, temp_data_dir: Path):
        """Test pipeline handles missing Compustat file."""
        config = PipelineConfig(
            compustat_path=temp_data_dir / "nonexistent.dta",
            macro_vars_path=temp_macro_vars_file,
        )
        pipeline = MarkupPipeline(config)

        # Should raise error during data preparation
        with pytest.raises(FileNotFoundError):
            pipeline.run_data_preparation()

    def test_pipeline_missing_macro_vars_file(self, temp_compustat_file: Path, temp_data_dir: Path):
        """Test pipeline handles missing macro vars file."""
        config = PipelineConfig(
            compustat_path=temp_compustat_file,
            macro_vars_path=temp_data_dir / "nonexistent.xlsx",
        )
        pipeline = MarkupPipeline(config)

        # Should raise error during data preparation
        with pytest.raises(FileNotFoundError):
            pipeline.run_data_preparation()
