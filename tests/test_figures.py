"""Test figure generation with real data.

Run with:
    uv run python tests/test_figures.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

MARKUPS_PATH = Path("Output/intermediate/markups_cost_share.csv")
PANEL_PATH = Path("Intermediate/main_annual.csv")
FIG1_DIR = Path("Intermediate/For Figure 1")
FIG_DIR = Path("Output/figures")


def check_inputs() -> bool:
    """Check at least some input files exist."""
    has_fig1 = FIG1_DIR.exists()
    has_fig2 = MARKUPS_PATH.exists()
    if not has_fig1 and not has_fig2:
        print(f"SKIP: No input files found.")
        print(f"  Figure 1 needs: {FIG1_DIR}")
        print(f"  Figure 2 needs: {MARKUPS_PATH}")
        return False
    return True


def test_figure1() -> None:
    """Test Figure 1: Aggregate Markup Comparison (DLEU, Replication, PPI-matched)."""
    from PyMarkup.core.figures import plot_aggregate_markup

    print("\n" + "=" * 60)
    print("Figure 1: Aggregate Markup Comparison")
    print("=" * 60)

    if not FIG1_DIR.exists():
        print(f"  SKIP: {FIG1_DIR} not found")
        return

    # Load the three input CSVs (same as legacy script 1.)
    agg_markup = pd.read_csv(FIG1_DIR / "agg_markup_annual.csv", low_memory=False)
    print(f"  agg_markup_annual: {len(agg_markup)} years")

    agg_ppi_path = FIG1_DIR / "agg_markup_limited_to_PPI matched_annual.csv"
    agg_markup_ppi = pd.read_csv(agg_ppi_path, low_memory=False) if agg_ppi_path.exists() else None
    if agg_markup_ppi is not None:
        print(f"  agg_markup_ppi_matched: {len(agg_markup_ppi)} years")

    dleu_path = FIG1_DIR / "Aggregate Markups by DLEU.csv"
    agg_dleu = pd.read_csv(dleu_path) if dleu_path.exists() else None
    if agg_dleu is not None:
        print(f"  DLEU benchmark: {len(agg_dleu)} years")

    save_path = FIG_DIR / "Aggregate Markup Comparison (1955-2021, Annual).pdf"
    fig = plot_aggregate_markup(
        agg_markup,
        agg_markup_ppi_matched=agg_markup_ppi,
        agg_markup_dleu=agg_dleu,
        save_path=save_path,
    )

    # Verify figure
    ax = fig.axes[0]
    lines = ax.get_lines()
    expected_lines = 1 + (1 if agg_markup_ppi is not None else 0) + (1 if agg_dleu is not None else 0)
    assert len(lines) == expected_lines, f"Expected {expected_lines} lines, got {len(lines)}"
    print(f"  Lines plotted: {len(lines)} ({ax.get_legend().get_texts()[0].get_text()}, ...)")
    print(f"  Saved to {save_path}")

    plt.close(fig)


def test_figure2(
    markups: pd.DataFrame, panel: pd.DataFrame
) -> None:
    """Test Figure 2: PPI vs Markup Growth scatter."""
    from PyMarkup.core.figures import plot_markup_vs_ppi, prepare_scatter_data

    print("\n" + "=" * 60)
    print("Figure 2: PPI vs Markup Growth")
    print("=" * 60)

    # Extract PPI and CPI from panel
    ppi_data = (
        panel[["ind2d", "year", "ppi"]]
        .dropna(subset=["ppi"])
        .drop_duplicates(subset=["ind2d", "year"])
    )
    cpi_data = (
        panel[["year", "CPI"]]
        .dropna()
        .drop_duplicates(subset=["year"])
    )
    print(f"  PPI: {len(ppi_data):,} industry-years")
    print(f"  CPI: {len(cpi_data):,} years")

    # Prepare scatter data
    scatter = prepare_scatter_data(
        markups, panel, ppi_data, cpi_data,
        min_years=5,
        year_range=(1980, 2018),
    )
    print(f"  Scatter data: {len(scatter):,} firms")

    if len(scatter) == 0:
        print("  SKIP: No scatter data after filtering")
        return

    # Verify scatter data structure
    assert "cagr_markup" in scatter.columns, "Missing cagr_markup"
    assert "cagr_PPI" in scatter.columns, "Missing cagr_PPI"
    assert "cagr_COGS" in scatter.columns, "Missing cagr_COGS"
    assert "sale_CPI" in scatter.columns, "Missing sale_CPI"
    assert scatter["gvkey"].is_unique, "Scatter data should have one row per firm"
    assert (scatter["periods"] > 0).all(), "All periods should be positive"

    print(f"  CAGR markup: mean={scatter['cagr_markup'].mean():.4f}, "
          f"median={scatter['cagr_markup'].median():.4f}")
    print(f"  CAGR PPI:    mean={scatter['cagr_PPI'].mean():.4f}, "
          f"median={scatter['cagr_PPI'].median():.4f}")

    # Generate full-sample scatter plot
    industry_col = (
        "ind2d_definition" if "ind2d_definition" in scatter.columns else "ind2d"
    )
    save_path = FIG_DIR / "ppi_vs_markup_1980_2018.pdf"
    ind_dir = FIG_DIR / "industries"

    fig = plot_markup_vs_ppi(
        scatter,
        title="Growth of PPI and Markup (1980-2018)",
        save_path=save_path,
        by_industry=True,
        industry_col=industry_col,
        industry_dir=ind_dir,
    )

    # Verify figure
    ax = fig.axes[0]
    legend = ax.get_legend()
    assert legend is not None, "Missing R^2 legend"
    legend_text = legend.get_texts()[0].get_text()
    assert "R$^2$" in legend_text, f"Legend should contain R^2, got: {legend_text}"
    print(f"  {legend_text}")

    plt.close(fig)

    print(f"  Saved to {save_path}")

    ind_count = len(list(ind_dir.glob("*.pdf")))
    print(f"  Industry plots: {ind_count} saved to {ind_dir}/")


def main() -> int:
    print("=" * 60)
    print("PyMarkup Figure Generation Test (Real Data)")
    print("=" * 60)

    if not check_inputs():
        return 1

    FIG_DIR.mkdir(parents=True, exist_ok=True)

    # Figure 1
    test_figure1()

    # Figure 2
    if MARKUPS_PATH.exists():
        print("\nLoading data for Figure 2...")
        markups = pd.read_csv(MARKUPS_PATH)
        print(f"  Markups: {len(markups):,} firm-years")

        panel = pd.read_csv(PANEL_PATH) if PANEL_PATH.exists() else None
        if panel is not None:
            print(f"  Panel:   {len(panel):,} firm-years")

        if panel is not None and "ppi" in panel.columns and "CPI" in panel.columns:
            test_figure2(markups, panel)
        else:
            print("\nSKIP Figure 2: main_annual.csv missing or lacks ppi/CPI columns")
    else:
        print(f"\nSKIP Figure 2: {MARKUPS_PATH} not found")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    pdfs = list(FIG_DIR.rglob("*.pdf"))
    print(f"  Total figures generated: {len(pdfs)}")
    for p in sorted(pdfs):
        print(f"    {p.relative_to(FIG_DIR)}")
    print("=" * 60)
    print("DONE")

    return 0


if __name__ == "__main__":
    sys.exit(main())
