"""
PyMarkup-estimator Quick Start Example

This script demonstrates basic usage of the PyMarkup-estimator package
for estimating firm-level markups from Compustat data.

Installation:
    pip install PyMarkup-estimator

Note: The package is called 'PyMarkup-estimator' but imported as 'PyMarkup'
"""

from pathlib import Path

from PyMarkup import EstimatorConfig, MarkupPipeline, PipelineConfig

# Example 1: Using Wooldridge IV estimator
# ==========================================

config = PipelineConfig(
    compustat_path=Path("Input/DLEU/Compustat_annual.dta"),
    macro_vars_path=Path("Input/DLEU/macro_vars_new.xlsx"),
    estimator=EstimatorConfig(
        method="wooldridge_iv",
        iv_specification="spec2",  # Include SG&A
        window_years=5,
        industry_level=2,
    ),
    output_dir=Path("output/"),
)

# Run the pipeline
pipeline = MarkupPipeline(config)
results = pipeline.run()

# Save results
results["markups"]["wooldridge_iv"].to_csv("output/firm_markups.csv", index=False)


# Example 2: Compare multiple methods
# ====================================

config_all = PipelineConfig(
    compustat_path=Path("Input/DLEU/Compustat_annual.dta"),
    macro_vars_path=Path("Input/DLEU/macro_vars_new.xlsx"),
    estimator=EstimatorConfig(
        method="all",  # Run all three methods
    ),
)

pipeline_all = MarkupPipeline(config_all)
results_all = pipeline_all.run()

# Compare methods
# comparison = results_all.compare_methods()
# print(comparison)


# Example 3: Using low-level API
# ===============================

from PyMarkup.estimators import CostShareEstimator
from PyMarkup.io import InputData

# Load data
data = InputData.from_compustat("Input/DLEU/Compustat_annual.dta")

# Use cost share estimator
estimator = CostShareEstimator(include_sga=False, aggregation="median")
elasticities = estimator.estimate_elasticities(data.to_dataframe())

print(elasticities.head())


# Example 4: Load config from YAML
# =================================

config_yaml = PipelineConfig.from_yaml("config.yaml")
pipeline_yaml = MarkupPipeline(config_yaml)
# results_yaml = pipeline_yaml.run()
