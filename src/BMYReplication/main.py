"""
Python orchestration of the BMY replication pipeline (mirrors ``main.do``).
"""

from __future__ import annotations

import logging

from .analyze_missing import main as analyze_missing_main
from .compute_markups import compute_markups
from .create_data import create_data
from .estimate_coefficients import estimate_coefficients
from .markup_figures import main as markup_figures_main
from .utils import ensure_directories

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


def run_pipeline() -> None:
    ensure_directories()

    # Create data with and without interest in COGS
    LOGGER.info("Running Create_Data include_interest_cogs=1 and 0")
    create_data(include_interest_cogs=True)
    create_data(include_interest_cogs=False)

    # Analyze missing SG&A
    LOGGER.info("Running Analyze_Missing")
    analyze_missing_main()

    # Estimate production function coefficients
    LOGGER.info("Running Estimate_Coefficients variants")
    estimate_coefficients(include_interest_cogs=True, drop_missing_sga=False, drop3254=False)
    estimate_coefficients(include_interest_cogs=False, drop_missing_sga=False, drop3254=False)
    estimate_coefficients(include_interest_cogs=False, drop_missing_sga=False, drop3254=True)
    estimate_coefficients(include_interest_cogs=False, drop_missing_sga=True, drop3254=False)

    # Compute markups
    LOGGER.info("Running Compute_Markups variants")
    compute_markups(include_interest_cogs=False, drop_missing_sga=False, drop3254=False)
    compute_markups(include_interest_cogs=False, drop_missing_sga=False, drop3254=True)
    compute_markups(include_interest_cogs=True, drop_missing_sga=False, drop3254=False)
    compute_markups(include_interest_cogs=False, drop_missing_sga=True, drop3254=False)

    # Figures
    LOGGER.info("Running Markup_Figures")
    markup_figures_main()


if __name__ == "__main__":
    run_pipeline()
