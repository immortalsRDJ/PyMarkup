"""
PyMarkup: Production function-based markup estimation toolkit.

This package provides tools for estimating firm-level markups using
production function approaches including Wooldridge IV, Cost Share,
and Ackerberg-Caves-Frazer (ACF) methods.

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

Low-level estimator API:

>>> from PyMarkup.estimators import WooldridgeIVEstimator
>>> from PyMarkup.io import InputData
>>> data = InputData.from_compustat("data/compustat.dta")
>>> estimator = WooldridgeIVEstimator(specification="spec2")
>>> elasticities = estimator.estimate_elasticities(data)
"""

from PyMarkup._version import __version__
from PyMarkup.estimators import (
    ACFEstimator,
    CostShareEstimator,
    ProductionFunctionEstimator,
    WooldridgeIVEstimator,
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
    # I/O
    "InputData",
    "MarkupResults",
]
