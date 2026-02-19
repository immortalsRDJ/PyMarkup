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
    title: str = "Dynamic Olley-Pakes Decomposition of Markup Changes",
    figsize: tuple[int, int] = (15, 10),
    save_path: Path | str | None = None,
) -> plt.Figure:
    """
    Plot decomposition results as a 4-line chart.

    Shows aggregate markup change and its three components:
    within, reallocation, and net entry.

    Parameters
    ----------
    decomposition : pd.DataFrame
        Output from OlleyPakesDecomposition.decompose().
        Must have columns: aggregate_change, within, reallocation, net_entry.
        Index is the time period.
    cumulative : bool, default False
        If True, plot cumulative sums (shows level changes from base period).
        If False, plot period-to-period changes.
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

    fig, ax = plt.subplots(figsize=figsize)

    ax.plot(plot_data.index, plot_data["aggregate_change"],
            color="black", linestyle="-", linewidth=3, label="Markup (Total)")
    ax.plot(plot_data.index, plot_data["within"],
            color="darkgreen", linestyle="-", linewidth=3, label="Within")
    ax.plot(plot_data.index, plot_data["reallocation"],
            color="orange", linestyle="--", linewidth=3, label="Reallocation")
    ax.plot(plot_data.index, plot_data["net_entry"],
            color="steelblue", linestyle=":", linewidth=3, label="Net Entry")

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_ylabel("Cumulative Change" if cumulative else "Period Change")
    ax.set_title(title)
    ax.legend()
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
