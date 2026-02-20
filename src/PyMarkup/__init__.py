"""
PyMarkup: Production function-based markup estimation toolkit.

This package provides tools for estimating firm-level markups using
production function approaches including Wooldridge IV, Cost Share,
and Ackerberg-Caves-Frazer (ACF) methods, plus markup decomposition tools.

Public API
----------
Pipeline (recommended for most users):
    MarkupPipeline : Main pipeline orchestrator
    PipelineConfig : Pipeline configuration
    EstimatorConfig : Estimator configuration

Estimators (for researchers who want control):
    WooldridgeIVEstimator : Wooldridge IV/GMM estimator
    CostShareEstimator : Direct cost share estimator
    ACFEstimator : Ackerberg-Caves-Frazer GMM estimator
    ProductionFunctionEstimator : Base class for all estimators

Decomposition (analyze markup trends):
    OlleyPakesDecomposition : Olley-Pakes decomposition (DLEU 2020)
    aggregate_markup_trends : Calculate aggregate trends
    plot_decomposition : Visualize decomposition results

Input/Output:
    InputData : Validated input data container
    MarkupResults : Results container with comparison tools

Example Usage
-------------
High-level pipeline API:

>>> from PyMarkup import MarkupPipeline, PipelineConfig, EstimatorConfig
>>> config = PipelineConfig(
...     compustat_path="data/compustat.dta",
...     macro_vars_path="data/macro_vars.xlsx",
...     estimator=EstimatorConfig(method="wooldridge_iv"),
... )
>>> pipeline = MarkupPipeline(config)
>>> results = pipeline.run()
>>> results.save("output/")

Decomposition analysis:

>>> from PyMarkup.decomposition import OlleyPakesDecomposition
>>> op = OlleyPakesDecomposition()
>>> decomp_results = op.decompose(firm_markups)
>>> print(decomp_results[["unweighted_mean", "op_covariance"]])

Low-level estimator API:

>>> from PyMarkup.estimators import WooldridgeIVEstimator
>>> from PyMarkup.io import InputData
>>> data = InputData.from_compustat("data/compustat.dta")
>>> estimator = WooldridgeIVEstimator(specification="spec2")
>>> elasticities = estimator.estimate_elasticities(data)
"""

from PyMarkup._version import __version__
from PyMarkup.decomposition import (
    OlleyPakesDecomposition,
    aggregate_markup_trends,
    plot_component_contributions,
    plot_decomposition,
)
from PyMarkup.estimators import (
    ACFEstimator,
    CostShareEstimator,
    ProductionFunctionEstimator,
    WooldridgeIVEstimator,
)
from PyMarkup.core.figures import (
    compute_aggregate_markup,
    plot_aggregate_markup,
    plot_aggregate_markup_comparison,
    plot_aggregate_markup_single_method,
    plot_markup_vs_ppi,
    prepare_scatter_data,
)
from PyMarkup.io import InputData, MarkupResults
from PyMarkup.pipeline import EstimatorConfig, MarkupPipeline, PipelineConfig

__author__ = """Yangyang (Claire) Meng"""
__email__ = "ym3593@nyu.edu"

__all__ = [
    "__version__",
    # Pipeline
    "MarkupPipeline",
    "PipelineConfig",
    "EstimatorConfig",
    # Estimators
    "ProductionFunctionEstimator",
    "WooldridgeIVEstimator",
    "CostShareEstimator",
    "ACFEstimator",
    # Decomposition
    "OlleyPakesDecomposition",
    "aggregate_markup_trends",
    "plot_decomposition",
    "plot_component_contributions",
    # Figures
    "compute_aggregate_markup",
    "plot_aggregate_markup",
    "plot_aggregate_markup_comparison",
    "plot_aggregate_markup_single_method",
    "plot_markup_vs_ppi",
    "prepare_scatter_data",
    # I/O
    "InputData",
    "MarkupResults",
]
