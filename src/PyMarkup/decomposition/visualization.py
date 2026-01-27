"""Visualization tools for markup decompositions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def plot_decomposition(
    decomposition: pd.DataFrame,
    decomp_type: str = "fhk",
    title: str | None = None,
    figsize: tuple[int, int] = (12, 6),
    save_path: Path | str | None = None,
    **kwargs,
) -> plt.Figure:
    """
    Plot decomposition results as stacked bar chart.

    Parameters
    ----------
    decomposition : pd.DataFrame
        Output from FHKDecomposition or MelitzDecomposition
    decomp_type : str, default "fhk"
        Type of decomposition: "fhk" or "melitz"
    title : str, optional
        Plot title. If None, auto-generates based on decomp_type.
    figsize : tuple, default (12, 6)
        Figure size in inches
    save_path : Path or str, optional
        If provided, saves figure to this path
    **kwargs
        Additional arguments passed to plt.bar()

    Returns
    -------
    matplotlib.figure.Figure
        The figure object

    Examples
    --------
    >>> from PyMarkup.decomposition import FHKDecomposition, plot_decomposition
    >>> fhk = FHKDecomposition()
    >>> results = fhk.decompose(data)
    >>> fig = plot_decomposition(results, save_path="decomp.png")
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Select components to plot
    if decomp_type.lower() == "fhk":
        components = ["within", "between", "cross", "entry", "exit"]
        if title is None:
            title = "Foster-Haltiwanger-Krizan Decomposition of Markup Changes"
    elif decomp_type.lower() == "melitz":
        components = ["surviving", "entry", "exit"]
        if title is None:
            title = "Melitz-Polanec Decomposition of Markup Changes"
    else:
        # Auto-detect components (exclude metadata columns)
        exclude = [
            "aggregate_change",
            "n_continuing",
            "n_entrants",
            "n_exiters",
            "n_surviving",
        ]
        components = [c for c in decomposition.columns if c not in exclude]
        if title is None:
            title = "Markup Decomposition"

    # Prepare data for stacking
    decomp_plot = decomposition[components].copy()

    # Create colors - exit is negative, so use different color
    colors = plt.cm.Set3(range(len(components)))
    if "exit" in components:
        exit_idx = components.index("exit")
        decomp_plot["exit"] = -decomp_plot["exit"]  # Flip sign for visualization

    # Create stacked bar chart
    decomp_plot.plot(
        kind="bar", stacked=True, ax=ax, color=colors, edgecolor="black", **kwargs
    )

    # Add aggregate change line
    if "aggregate_change" in decomposition.columns:
        ax.plot(
            range(len(decomposition)),
            decomposition["aggregate_change"],
            color="red",
            marker="o",
            linewidth=2,
            markersize=6,
            label="Total Change",
        )

    # Formatting
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Period", fontsize=12)
    ax.set_ylabel("Markup Change", fontsize=12)
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.legend(loc="best", frameon=True)
    ax.grid(True, alpha=0.3)

    # Rotate x-axis labels
    ax.set_xticklabels(decomposition.index, rotation=45, ha="right")

    plt.tight_layout()

    # Save if requested
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    return fig


def plot_component_contributions(
    decomposition: pd.DataFrame,
    components: list[str] | None = None,
    title: str = "Component Contributions to Markup Change",
    figsize: tuple[int, int] = (10, 6),
    save_path: Path | str | None = None,
) -> plt.Figure:
    """
    Plot each component's contribution over time as line chart.

    Parameters
    ----------
    decomposition : pd.DataFrame
        Decomposition results
    components : list of str, optional
        Components to plot. If None, plots all numeric columns.
    title : str
        Plot title
    figsize : tuple, default (10, 6)
        Figure size
    save_path : Path or str, optional
        Path to save figure

    Returns
    -------
    matplotlib.figure.Figure
        The figure object
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Auto-detect components if not provided
    if components is None:
        exclude = [
            "aggregate_change",
            "n_continuing",
            "n_entrants",
            "n_exiters",
            "n_surviving",
        ]
        components = [c for c in decomposition.columns if c not in exclude]

    # Plot each component
    for comp in components:
        if comp in decomposition.columns:
            ax.plot(
                decomposition.index,
                decomposition[comp],
                marker="o",
                label=comp.replace("_", " ").title(),
                linewidth=2,
                markersize=6,
            )

    # Formatting
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Period", fontsize=12)
    ax.set_ylabel("Contribution", fontsize=12)
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.legend(loc="best", frameon=True)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    return fig


def plot_aggregate_with_decomposition(
    trends: pd.DataFrame,
    decomposition: pd.DataFrame,
    decomp_type: str = "fhk",
    figsize: tuple[int, int] = (14, 10),
    save_path: Path | str | None = None,
) -> plt.Figure:
    """
    Create comprehensive plot with aggregate trends and decomposition.

    Parameters
    ----------
    trends : pd.DataFrame
        Output from aggregate_markup_trends()
    decomposition : pd.DataFrame
        Output from decomposition
    decomp_type : str, default "fhk"
        Decomposition type
    figsize : tuple, default (14, 10)
        Figure size
    save_path : Path or str, optional
        Path to save figure

    Returns
    -------
    matplotlib.figure.Figure
        The figure object
    """
    fig, axes = plt.subplots(2, 1, figsize=figsize)

    # Top panel: Aggregate markup trend
    ax1 = axes[0]
    ax1.plot(
        trends.index if trends.index.name else range(len(trends)),
        trends["aggregate_markup"] if "aggregate_markup" in trends.columns else trends.iloc[:, 0],
        marker="o",
        linewidth=2,
        markersize=6,
        color="darkblue",
        label="Aggregate Markup",
    )
    ax1.set_title("Aggregate Markup Over Time", fontsize=14, fontweight="bold")
    ax1.set_ylabel("Markup", fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="best")

    # Bottom panel: Decomposition
    ax2 = axes[1]

    if decomp_type.lower() == "fhk":
        components = ["within", "between", "cross", "entry", "exit"]
    else:
        components = ["surviving", "entry", "exit"]

    decomp_plot = decomposition[components].copy()
    if "exit" in components:
        decomp_plot["exit"] = -decomp_plot["exit"]

    colors = plt.cm.Set3(range(len(components)))
    decomp_plot.plot(kind="bar", stacked=True, ax=ax2, color=colors, edgecolor="black")

    if "aggregate_change" in decomposition.columns:
        ax2.plot(
            range(len(decomposition)),
            decomposition["aggregate_change"],
            color="red",
            marker="o",
            linewidth=2,
            markersize=6,
            label="Total Change",
        )

    ax2.set_title("Decomposition of Markup Changes", fontsize=14, fontweight="bold")
    ax2.set_xlabel("Period", fontsize=12)
    ax2.set_ylabel("Contribution to Change", fontsize=12)
    ax2.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax2.legend(loc="best")
    ax2.grid(True, alpha=0.3)
    ax2.set_xticklabels(decomposition.index, rotation=45, ha="right")

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    return fig
