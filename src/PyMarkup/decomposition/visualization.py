"""Visualization for dynamic Olley-Pakes decomposition."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)


def _apply_decomp_style() -> None:
    """Apply plot style matching legacy setplotstyle_agg()."""
    from cycler import cycler

    import matplotlib
    matplotlib.style.use("seaborn-v0_8-whitegrid")
    matplotlib.rcParams.update({"font.size": 26})
    plt.rcParams["figure.figsize"] = (15, 10)
    plt.rc("font", size=26)
    plt.rc("axes", titlesize=26, labelsize=26)
    plt.rc("xtick", labelsize=26)
    plt.rc("ytick", labelsize=26)
    plt.rc("legend", fontsize=20)
    plt.rc("figure", titlesize=26)
    plt.rc(
        "axes",
        prop_cycle=(
            cycler(color=["#252525", "#636363", "#969696", "#bdbdbd"])
            * cycler(linestyle=["-", ":", "--", "-."])
        ),
    )
    plt.rc("lines", linewidth=3)


def plot_decomposition(
    decomposition: pd.DataFrame,
    cumulative: bool = False,
    base_markup: float | None = None,
    title: str = "Dynamic Olley-Pakes Decomposition of Markup Changes",
    figsize: tuple[int, int] = (15, 10),
    save_path: Path | str | None = None,
) -> plt.Figure:
    """
    Plot decomposition results as a 4-line chart (DLEU Figure IV style).

    Shows aggregate markup and three counterfactual paths based on the
    decomposition, all starting from the same baseline year.

    When base_markup is provided with cumulative=True, plots counterfactual
    markup levels where ALL lines start at the same baseline:
    - Markup (benchmark) = base_markup + cumsum(aggregate_change)
    - Within-only = base_markup + cumsum(within)
    - Reallocation-only = base_markup + cumsum(reallocation)
    - Net Entry-only = base_markup + cumsum(net_entry)

    Each counterfactual line shows "what the markup would have been if only
    this component operated" starting from the common baseline (DLEU 2020).

    Parameters
    ----------
    decomposition : pd.DataFrame
        Output from OlleyPakesDecomposition.decompose().
        Must have columns: aggregate_change, within, reallocation, net_entry.
        Index is the time period.
    cumulative : bool, default False
        If True, plot cumulative sums (shows level changes from base period).
        If False, plot period-to-period changes.
    base_markup : float, optional
        Base period aggregate markup level (e.g., 1.21 for 1980 in DLEU).
        If provided with cumulative=True, plots counterfactual markup levels
        where all lines start at this common baseline.
    title : str
        Plot title.
    figsize : tuple
        Figure size in inches.
    save_path : Path or str, optional
        If provided, saves figure to this path.

    Returns
    -------
    matplotlib.figure.Figure
    """
    _apply_decomp_style()

    components = ["aggregate_change", "within", "reallocation", "net_entry"]
    for col in components:
        if col not in decomposition.columns:
            raise ValueError(f"Missing column: {col}")

    plot_data = decomposition[components].copy()
    if cumulative:
        plot_data = plot_data.cumsum()
        # If base_markup provided, all lines start at the same baseline
        # This creates counterfactual paths: "what if only this component operated?"
        if base_markup is not None:
            plot_data["aggregate_change"] = plot_data["aggregate_change"] + base_markup
            plot_data["within"] = plot_data["within"] + base_markup
            plot_data["reallocation"] = plot_data["reallocation"] + base_markup
            plot_data["net_entry"] = plot_data["net_entry"] + base_markup

    fig, ax = plt.subplots(figsize=figsize)

    # Style matching DLEU Figure IV
    ax.plot(plot_data.index, plot_data["aggregate_change"],
            color="red", linestyle="-", linewidth=3, label="Markup (benchmark)")
    ax.plot(plot_data.index, plot_data["within"],
            color="blue", linestyle="--", linewidth=3, label="Within")
    ax.plot(plot_data.index, plot_data["reallocation"],
            color="black", linestyle=":", linewidth=3, label="Reallocation")
    ax.plot(plot_data.index, plot_data["net_entry"],
            color="green", linestyle="-.", linewidth=3, label="Net Entry")

    if not (cumulative and base_markup is not None):
        ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)

    if cumulative and base_markup is not None:
        ax.set_ylabel("Aggregate Markup")
    else:
        ax.set_ylabel("Cumulative Change" if cumulative else "Period Change")
    ax.set_title(title)
    ax.legend(loc="upper left")
    fig.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        logger.info(f"Saved decomposition plot to {save_path}")

    return fig


def plot_component_contributions(
    decomposition: pd.DataFrame,
    title: str = "Period-to-Period Decomposition of Markup Changes",
    figsize: tuple[int, int] = (15, 10),
    save_path: Path | str | None = None,
) -> plt.Figure:
    """
    Plot period-to-period component contributions as a stacked bar chart.

    Parameters
    ----------
    decomposition : pd.DataFrame
        Output from OlleyPakesDecomposition.decompose().
    title : str
        Plot title.
    figsize : tuple
        Figure size in inches.
    save_path : Path or str, optional
        If provided, saves figure to this path.

    Returns
    -------
    matplotlib.figure.Figure
    """
    _apply_decomp_style()

    components = ["within", "reallocation", "net_entry"]
    plot_data = decomposition[components].copy()

    fig, ax = plt.subplots(figsize=figsize)

    colors = {"within": "darkgreen", "reallocation": "orange", "net_entry": "steelblue"}
    plot_data.plot(
        kind="bar", stacked=True, ax=ax,
        color=[colors[c] for c in components],
        edgecolor="black", alpha=0.8,
    )

    # Overlay aggregate change as line
    if "aggregate_change" in decomposition.columns:
        ax.plot(
            range(len(decomposition)),
            decomposition["aggregate_change"].values,
            color="black", marker="o", linewidth=2, markersize=4,
            label="Total Change",
        )

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_ylabel("Markup Change")
    ax.set_title(title)
    ax.legend(["Within", "Reallocation", "Net Entry", "Total Change"])
    ax.grid(True, alpha=0.3)

    # Thin out x-axis labels for readability
    tick_labels = [str(int(x)) if i % 5 == 0 else "" for i, x in enumerate(decomposition.index)]
    ax.set_xticklabels(tick_labels, rotation=45, ha="right")

    fig.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        logger.info(f"Saved component contributions plot to {save_path}")

    return fig
