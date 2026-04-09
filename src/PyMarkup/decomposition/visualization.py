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
    start_year: int | None = None,
    title: str = "Decomposition of Markup Growth at the Firm Level",
    figsize: tuple[int, int] = (15, 10),
    save_path: Path | str | None = None,
) -> plt.Figure:
    """
    Plot decomposition results as a 4-line chart replicating DLEU Figure IV.

    Replicates Figure IV from De Loecker, Eeckhout & Unger (2020, QJE):
    "Decomposition of Markup Growth at the Firm Level". All four lines
    start at the same base_markup level (e.g., 1.21 in 1980) and diverge
    as each component accumulates over time.

    When start_year and base_markup are provided, the plot:
    - Filters decomposition data to periods >= start_year
    - Prepends a base-year anchor row so all lines visibly start at base_markup
    - Accumulates each component from the base year forward

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
    start_year : int, optional
        First year to display (e.g., 1980 for DLEU Figure IV).
        When used with base_markup, a zero-change anchor row is prepended at
        this year so all four lines visibly converge at the baseline.
        Decomposition rows before start_year are excluded.
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

    # Filter to start_year onward (decomposition index holds the "to" period,
    # so rows with index >= start_year+1 represent changes *after* start_year)
    if start_year is not None:
        plot_data = plot_data[plot_data.index > start_year]

    if cumulative:
        plot_data = plot_data.cumsum()
        if base_markup is not None:
            # Prepend base-year anchor row so all lines start at base_markup
            if start_year is not None:
                anchor = pd.DataFrame(
                    {col: [0.0] for col in components}, index=[start_year]
                )
                anchor.index.name = plot_data.index.name
                plot_data = pd.concat([anchor, plot_data])
            # Shift all lines to start at base_markup
            for col in components:
                plot_data[col] = plot_data[col] + base_markup

    fig, ax = plt.subplots(figsize=figsize)

    # Style matching DLEU Figure IV exactly
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
