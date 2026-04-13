"""Tests for dynamic Olley-Pakes decomposition.

Run with:
    uv run python tests/test_decomposition.py
    just test tests/test_decomposition.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

MARKUPS_PATH = Path("Output/intermediate/markups_cost_share.csv")
PANEL_PATH = Path("Intermediate/main_annual.csv")


# --------------------------------------------------------------------------- #
# Synthetic data tests
# --------------------------------------------------------------------------- #


def test_additivity() -> None:
    """within + reallocation + net_entry should approximate aggregate_change."""
    from PyMarkup.decomposition import OlleyPakesDecomposition

    print("\n  Additivity: within + reallocation + net_entry ≈ aggregate_change")

    rng = np.random.default_rng(42)
    rows = []
    for year in range(2000, 2010):
        n_firms = rng.integers(150, 250)
        for i in range(n_firms):
            rows.append({
                "gvkey": i, "year": year,
                "markup": rng.lognormal(0, 0.4),
                "sale": rng.uniform(100, 5000),
            })
    df = pd.DataFrame(rows)

    op = OlleyPakesDecomposition()
    result = op.decompose(df)

    residual = (
        result["aggregate_change"]
        - result["within"]
        - result["reallocation"]
        - result["net_entry"]
    ).abs()
    assert residual.max() < 1e-10, f"Additivity violated: max residual = {residual.max()}"
    print(f"    Max residual: {residual.max():.2e} (OK)")


def test_no_entry_exit() -> None:
    """When all firms continue, net_entry should be zero."""
    from PyMarkup.decomposition import OlleyPakesDecomposition

    print("\n  No entry/exit -> zero net_entry")

    rng = np.random.default_rng(42)
    rows = []
    for year in [2000, 2001]:
        for i in range(50):
            rows.append({
                "gvkey": i, "year": year,
                "markup": 1.0 + i * 0.01 + (year - 2000) * 0.05,
                "sale": 1000.0 + rng.uniform(-100, 100),
            })
    df = pd.DataFrame(rows)

    op = OlleyPakesDecomposition()
    result = op.decompose(df)

    assert (result["net_entry"].abs() < 1e-12).all(), (
        f"Net entry should be zero: {result['net_entry'].tolist()}"
    )
    assert (result["n_entrants"] == 0).all()
    assert (result["n_exiters"] == 0).all()
    print("    Net entry is zero, n_entrants=0, n_exiters=0 (OK)")


def test_within_only() -> None:
    """When shares don't change and no entry/exit, only within component matters."""
    from PyMarkup.decomposition import OlleyPakesDecomposition

    print("\n  Fixed shares, no entry/exit -> only within component")

    rows = []
    for year in [2000, 2001]:
        for i in range(50):
            rows.append({
                "gvkey": i, "year": year,
                "markup": 1.0 + i * 0.01 + (year - 2000) * 0.1,
                "sale": 100.0 * (i + 1),  # same shares both periods
            })
    df = pd.DataFrame(rows)

    op = OlleyPakesDecomposition()
    result = op.decompose(df)

    # With identical shares, reallocation should be zero
    assert (result["reallocation"].abs() < 1e-12).all(), (
        f"Reallocation should be zero: {result['reallocation'].tolist()}"
    )
    # Within should equal aggregate change
    residual = (result["aggregate_change"] - result["within"]).abs()
    assert residual.max() < 1e-12, f"Within != aggregate: {residual.max()}"
    print("    Reallocation is zero, within == aggregate_change (OK)")


def test_positive_reallocation() -> None:
    """When high-markup firms gain share, reallocation should be positive."""
    from PyMarkup.decomposition import OlleyPakesDecomposition

    print("\n  Positive reallocation")

    rows = []
    for i in range(100):
        markup_base = 1.0 + i * 0.01
        sale_base = 100 + i * 10
        # Period 1: base
        rows.append({"gvkey": i, "year": 2000, "markup": markup_base, "sale": sale_base})
        # Period 2: high-markup firms gain sales, low-markup firms lose
        sale_change = (i - 50) * 20  # positive for high-markup, negative for low
        rows.append({
            "gvkey": i, "year": 2001,
            "markup": markup_base,  # same markups
            "sale": max(sale_base + sale_change, 10),
        })
    df = pd.DataFrame(rows)

    op = OlleyPakesDecomposition()
    result = op.decompose(df)

    assert result.loc[2001, "reallocation"] > 0, (
        f"Expected positive reallocation, got {result.loc[2001, 'reallocation']:.6f}"
    )
    print(f"    Reallocation: {result.loc[2001, 'reallocation']:.6f} > 0 (OK)")


def test_output_columns() -> None:
    """Output should have exactly the expected columns."""
    from PyMarkup.decomposition import OlleyPakesDecomposition

    print("\n  Output columns")

    rows = [
        {"gvkey": i, "year": y, "markup": 1.1, "sale": 100}
        for y in [2000, 2001, 2002] for i in range(10)
    ]
    df = pd.DataFrame(rows)

    op = OlleyPakesDecomposition()
    result = op.decompose(df)

    expected = {
        "within", "reallocation", "net_entry", "aggregate_change",
        "n_continuing", "n_entrants", "n_exiters",
    }
    assert set(result.columns) == expected, f"Got columns: {set(result.columns)}"
    assert result.index.name == "period"
    assert len(result) == 2  # 2 transitions for 3 periods
    print(f"    Columns: {sorted(result.columns)} (OK)")


def test_custom_column_names() -> None:
    """Should work with non-default column names."""
    from PyMarkup.decomposition import OlleyPakesDecomposition

    print("\n  Custom column names")

    rows = [
        {"firm_id": i, "t": y, "mu": 1.2 + i * 0.01, "revenue": 500 + i * 10}
        for y in [2010, 2011, 2012] for i in range(20)
    ]
    df = pd.DataFrame(rows)

    op = OlleyPakesDecomposition(
        firm_var="firm_id", time_var="t", markup_var="mu", weight_var="revenue"
    )
    result = op.decompose(df)

    assert len(result) == 2  # 2 transitions
    assert result.index.name == "period"
    print("    Custom columns accepted (OK)")


def test_missing_column_raises() -> None:
    """Should raise ValueError for missing columns."""
    from PyMarkup.decomposition import OlleyPakesDecomposition

    print("\n  Missing column validation")

    df = pd.DataFrame({"gvkey": [1], "year": [2000], "markup": [1.0]})
    op = OlleyPakesDecomposition()
    try:
        op.decompose(df)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "sale" in str(e)
        print(f"    Raised ValueError: {e} (OK)")


def test_nan_raises() -> None:
    """Should raise ValueError for NaN values."""
    from PyMarkup.decomposition import OlleyPakesDecomposition

    print("\n  NaN validation")

    df = pd.DataFrame({
        "gvkey": [1, 2, 1, 2], "year": [2000, 2000, 2001, 2001],
        "markup": [1.0, np.nan, 1.1, 1.2], "sale": [100, 200, 100, 200],
    })
    op = OlleyPakesDecomposition()
    try:
        op.decompose(df)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "missing" in str(e).lower()
        print(f"    Raised ValueError: {e} (OK)")


def test_single_period_raises() -> None:
    """Should raise ValueError with only one period."""
    from PyMarkup.decomposition import OlleyPakesDecomposition

    print("\n  Single period validation")

    df = pd.DataFrame({
        "gvkey": [1, 2], "year": [2000, 2000],
        "markup": [1.0, 1.1], "sale": [100, 200],
    })
    op = OlleyPakesDecomposition()
    try:
        op.decompose(df)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "2 time periods" in str(e)
        print(f"    Raised ValueError: {e} (OK)")


def test_entry_exit_counts() -> None:
    """Entry/exit counts should be correct."""
    from PyMarkup.decomposition import OlleyPakesDecomposition

    print("\n  Entry/exit counts")

    rows = []
    # Period 1: firms 0-9
    for i in range(10):
        rows.append({"gvkey": i, "year": 2000, "markup": 1.1, "sale": 100})
    # Period 2: firms 5-14 (5 exiters: 0-4, 5 entrants: 10-14, 5 continuing: 5-9)
    for i in range(5, 15):
        rows.append({"gvkey": i, "year": 2001, "markup": 1.2, "sale": 100})
    df = pd.DataFrame(rows)

    op = OlleyPakesDecomposition()
    result = op.decompose(df)

    assert result.loc[2001, "n_continuing"] == 5
    assert result.loc[2001, "n_entrants"] == 5
    assert result.loc[2001, "n_exiters"] == 5
    print("    n_continuing=5, n_entrants=5, n_exiters=5 (OK)")


# --------------------------------------------------------------------------- #
# Visualization test
# --------------------------------------------------------------------------- #


def test_plot_decomposition() -> None:
    """Test that plot_decomposition renders without errors."""
    from PyMarkup.decomposition import OlleyPakesDecomposition, plot_decomposition

    print("\n  Plot decomposition (4-line chart)")

    rng = np.random.default_rng(42)
    rows = []
    for year in range(2000, 2010):
        for i in range(100):
            rows.append({
                "gvkey": i, "year": year,
                "markup": rng.lognormal(0, 0.3),
                "sale": rng.uniform(100, 5000),
            })
    df = pd.DataFrame(rows)

    op = OlleyPakesDecomposition()
    result = op.decompose(df)

    # Test cumulative plot
    fig = plot_decomposition(result, cumulative=True)
    axes = fig.get_axes()
    assert len(axes) == 1
    lines = axes[0].get_lines()
    # 4 data lines + 1 horizontal zero line
    assert len(lines) >= 4, f"Expected at least 4 lines, got {len(lines)}"
    print(f"    Cumulative plot: {len(lines)} lines (OK)")

    import matplotlib.pyplot as plt
    plt.close(fig)

    # Test period-to-period plot
    fig2 = plot_decomposition(result, cumulative=False)
    print("    Period-to-period plot: OK")
    plt.close(fig2)


def test_plot_component_contributions() -> None:
    """Test that plot_component_contributions renders without errors."""
    from PyMarkup.decomposition import OlleyPakesDecomposition, plot_component_contributions

    print("\n  Plot component contributions (stacked bar)")

    rng = np.random.default_rng(42)
    rows = []
    for year in range(2000, 2006):
        for i in range(80):
            rows.append({
                "gvkey": i, "year": year,
                "markup": rng.lognormal(0, 0.3),
                "sale": rng.uniform(100, 5000),
            })
    df = pd.DataFrame(rows)

    op = OlleyPakesDecomposition()
    result = op.decompose(df)

    fig = plot_component_contributions(result)
    assert fig is not None
    print("    Stacked bar plot: OK")

    import matplotlib.pyplot as plt
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Real data test
# --------------------------------------------------------------------------- #


def test_real_data() -> None:
    """Run dynamic OP decomposition on pipeline-generated markups."""
    from PyMarkup.decomposition import OlleyPakesDecomposition, plot_decomposition

    print("\n" + "=" * 60)
    print("Dynamic OP Decomposition with Real Data")
    print("=" * 60)

    if not MARKUPS_PATH.exists():
        print(f"  SKIP: {MARKUPS_PATH} not found")
        return

    markups = pd.read_csv(MARKUPS_PATH)
    print(f"  Loaded markups: {len(markups):,} firm-years")

    # Need a sales column — merge from panel if available
    if "sale" not in markups.columns and PANEL_PATH.exists():
        panel = pd.read_csv(PANEL_PATH, usecols=["gvkey", "year", "sale"])
        markups = markups.merge(panel, on=["gvkey", "year"], how="left")
        markups = markups.dropna(subset=["sale", "markup"])
        print(f"  After merging sales: {len(markups):,} firm-years")
    elif "sale" not in markups.columns:
        print("  SKIP: No sale column and panel not available")
        return

    # Filter valid markups
    markups = markups[(markups["markup"] > 0) & (markups["markup"] < 50)]
    markups = markups[markups["sale"] > 0]
    print(f"  After filtering: {len(markups):,} firm-years")

    op = OlleyPakesDecomposition()
    result = op.decompose(markups)

    print(f"\n  Decomposition ({len(result)} transitions):")
    print(f"  {'Period':<8} {'ΔTotal':>10} {'Within':>10} {'Realloc':>10} {'NetEntry':>10} {'Cont':>6} {'Enter':>6} {'Exit':>6}")
    print(f"  {'-'*68}")
    for period, row in result.iterrows():
        print(
            f"  {period:<8} {row['aggregate_change']:>10.4f} "
            f"{row['within']:>10.4f} "
            f"{row['reallocation']:>10.4f} "
            f"{row['net_entry']:>10.4f} "
            f"{row['n_continuing']:>6.0f} "
            f"{row['n_entrants']:>6.0f} "
            f"{row['n_exiters']:>6.0f}"
        )

    # Verify additivity
    residual = (
        result["aggregate_change"]
        - result["within"]
        - result["reallocation"]
        - result["net_entry"]
    ).abs().max()
    assert residual < 1e-10, f"Additivity violated: {residual}"
    print(f"\n  Additivity check: max residual = {residual:.2e} (OK)")

    # Plot and save
    save_dir = Path("Output/figures")
    save_dir.mkdir(parents=True, exist_ok=True)

    fig = plot_decomposition(
        result, cumulative=True,
        save_path=save_dir / "decomposition_cumulative.pdf",
    )
    print(f"  Saved cumulative plot to {save_dir / 'decomposition_cumulative.pdf'}")

    import matplotlib.pyplot as plt
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main() -> int:
    print("=" * 60)
    print("Dynamic Olley-Pakes Decomposition Tests")
    print("=" * 60)

    # Synthetic data tests
    print("\n--- Synthetic Data Tests ---")
    test_additivity()
    test_no_entry_exit()
    test_within_only()
    test_positive_reallocation()
    test_output_columns()
    test_custom_column_names()
    test_missing_column_raises()
    test_nan_raises()
    test_single_period_raises()
    test_entry_exit_counts()

    # Visualization tests
    print("\n--- Visualization Tests ---")
    test_plot_decomposition()
    test_plot_component_contributions()

    # Real data test
    test_real_data()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
