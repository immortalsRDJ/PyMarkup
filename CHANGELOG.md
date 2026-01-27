# Changelog

All notable changes to PyMarkup-estimator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive test suite with 102 tests
  - Unit tests for all three estimators (Wooldridge IV, Cost Share, ACF)
  - Integration tests for full pipeline
  - IO schema validation tests
  - Test fixtures with synthetic data
- Complete documentation in tests/README.md
- Pydantic-based IO schemas (InputData, MarkupResults) with validation
- Multiple output format support (CSV, Parquet, Stata)
- Result comparison and plotting methods
- Rich CLI output with typer and rich

### Changed
- Package renamed from PyMarkup to PyMarkup-estimator for PyPI publication
- Import name remains 'PyMarkup' for backward compatibility
- Updated GitHub repository URLs to immortalsRDJ/PyMarkup-estimator
- Improved README with badges and clearer installation instructions
- Enhanced documentation structure

### Fixed
- Fixed fyear to year column renaming in InputData schema

## [0.2.0-dev] - 2026-01-04

### Added
- Complete refactored package with modular architecture
- Three production function estimators:
  - Wooldridge IV/GMM with lagged COGS instrument (spec1 and spec2)
  - Cost Share estimator (accounting approach)
  - ACF (Ackerberg-Caves-Frazer) GMM estimator
- MarkupPipeline orchestrator for end-to-end workflow
- PipelineConfig and EstimatorConfig with YAML support
- Command-line interface with estimate and validate commands
- Type hints throughout codebase
- Pydantic validation for inputs and outputs

### Changed
- Migrated from numbered scripts to professional package structure
- Separated core logic, estimators, pipeline, and I/O modules
- Improved error handling and logging

## [0.1.0] - 2025-12-08

### Added
- Initial numbered script implementation
- Basic Wooldridge IV estimation
- Data preparation pipeline
- Compustat data loading
- Macro variable integration

[Unreleased]: https://github.com/immortalsRDJ/PyMarkup-estimator/compare/v0.2.0-dev...HEAD
[0.2.0-dev]: https://github.com/immortalsRDJ/PyMarkup-estimator/releases/tag/v0.2.0-dev
[0.1.0]: https://github.com/immortalsRDJ/PyMarkup-estimator/releases/tag/v0.1.0
