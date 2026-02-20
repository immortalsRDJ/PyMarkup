"""Figure generation for markup analysis.

Based on legacy scripts:
- 0.5 Prepare Data for Figures and Tables.py
- 1. Generate Figure 1 - Aggregate Markup.py
- 2. Generate Figure 2 - CAGR of PPI vs Markup.py

This module provides:
- plot_aggregate_markup: Time series of aggregate markup (Figure 1)
- prepare_scatter_data: CAGR computation for PPI vs markup scatter (from 0.5)
- plot_markup_vs_ppi: Scatter of markup growth vs PPI growth (Figure 2)
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def cagr(first: pd.Series, last: pd.Series, periods: pd.Series) -> pd.Series:
    """Compound Annual Growth Rate: ((last/first)^(1/periods) - 1) * 100."""
    return ((last / first) ** (1 / periods) - 1) * 100


# --------------------------------------------------------------------------- #
# Plot styling (from path_plot_config.py)
# --------------------------------------------------------------------------- #


def _apply_agg_style() -> None:
    """Apply aggregate plot style matching legacy setplotstyle_agg()."""
    from cycler import cycler

    import matplotlib
    matplotlib.style.use("seaborn-v0_8-whitegrid")
    matplotlib.rcParams.update({"font.size": 26})
    plt.rcParams["figure.figsize"] = (15, 10)
    for key in ["font", "axes.title", "axes.label", "xtick", "ytick", "legend", "figure.title"]:
        prop = key if "." in key else key
        if key == "font":
            plt.rc("font", size=26)
        elif key == "axes.title":
            plt.rc("axes", titlesize=26)
        elif key == "axes.label":
            plt.rc("axes", labelsize=26)
        elif key == "xtick":
            plt.rc("xtick", labelsize=26)
        elif key == "ytick":
            plt.rc("ytick", labelsize=26)
        elif key == "legend":
            plt.rc("legend", fontsize=26)
        elif key == "figure.title":
            plt.rc("figure", titlesize=26)
    plt.rc(
        "axes",
        prop_cycle=(
            cycler(color=["#252525", "#636363", "#969696", "#bdbdbd"])
            * cycler(linestyle=["-", ":", "--", "-."])
        ),
    )
    plt.rc("lines", linewidth=3)


# --------------------------------------------------------------------------- #
# Figure 1: Aggregate Markup Comparison
# --------------------------------------------------------------------------- #


def plot_aggregate_markup(
    markups: pd.DataFrame,
    agg_markup_ppi_matched: pd.DataFrame | None = None,
    agg_markup_dleu: pd.DataFrame | None = None,
    year_range: tuple[int, int] | None = None,
    figsize: tuple[int, int] = (15, 10),
    save_path: Path | str | None = None,
    title: str | None = None,
) -> plt.Figure:
    """
    Plot aggregate markup comparison over time (Figure 1).

    Replicates legacy script ``1. Generate Figure 1 - Aggregate Markup.py``.
    Plots up to 3 series: DLEU benchmark, replication (all firms),
    and firms matched to PPI.

    Parameters
    ----------
    markups : pd.DataFrame
        Either firm-level markups with columns: gvkey, year, markup, sale_D (optional)
        OR pre-aggregated with columns: year, MARKUP_spec1
    agg_markup_ppi_matched : pd.DataFrame, optional
        Aggregate markup for PPI-matched firms with columns:
        year, MARKUP10_AGG_limited
        (from ``agg_markup_limited_to_PPI matched_annual.csv``).
    agg_markup_dleu : pd.DataFrame, optional
        DLEU benchmark with columns: year, agg_markup_DLEU
        (from ``Aggregate Markups by DLEU.csv``).
    year_range : tuple of (start, end), optional
        Restrict to this year range (inclusive).
    figsize : tuple
        Figure size in inches.
    save_path : Path or str, optional
        If provided, saves figure to this path.
    title : str, optional
        Plot title. Defaults to "Aggregate Markup".

    Returns
    -------
    matplotlib.figure.Figure
    """
    _apply_agg_style()

    # Check if input is firm-level or pre-aggregated
    if "markup" in markups.columns and "gvkey" in markups.columns:
        # Firm-level: aggregate by year using sales-weighted mean
        df = markups.copy()
        df["TOTSALES"] = df.groupby("year")["sale_D"].transform("sum") if "sale_D" in df.columns else 1
        df["weight"] = df["sale_D"] / df["TOTSALES"] if "sale_D" in df.columns else 1 / df.groupby("year")["markup"].transform("size")
        agg_markup = df.groupby("year").apply(
            lambda g: np.sum(g["weight"] * g["markup"].fillna(0)),
            include_groups=False,
        ).reset_index(name="agg_markup_all_firms")
    else:
        # Pre-aggregated
        agg_markup = markups.rename(
            columns={"MARKUP_spec1": "agg_markup_all_firms"}
        ).copy()

    p = agg_markup.copy()

    if agg_markup_ppi_matched is not None:
        p = p.merge(
            agg_markup_ppi_matched.rename(
                columns={"MARKUP10_AGG_limited": "agg_markup_matched_ppi"}
            ),
            on="year", how="outer",
        )

    if agg_markup_dleu is not None:
        p = p.merge(agg_markup_dleu, on="year", how="outer")

    if year_range is not None:
        p = p[(p["year"] >= year_range[0]) & (p["year"] <= year_range[1])]

    p = p.sort_values("year")

    # Plot
    fig, ax = plt.subplots(figsize=figsize)

    if "agg_markup_DLEU" in p.columns:
        ax.plot(p["year"], p["agg_markup_DLEU"],
                color="black", linestyle=":", linewidth=3)

    ax.plot(p["year"], p["agg_markup_all_firms"],
            color="darkgreen", linestyle="-", linewidth=3)

    if "agg_markup_matched_ppi" in p.columns:
        ax.plot(p["year"], p["agg_markup_matched_ppi"],
                color="orange", linestyle="--", linewidth=3)

    # Legend
    labels = []
    if "agg_markup_DLEU" in p.columns:
        labels.append("DLEU")
    labels.append("Replication")
    if "agg_markup_matched_ppi" in p.columns:
        labels.append("Firms Matched to PPI")
    ax.legend(labels)

    ax.set_ylabel("Aggregate Markup")
    if title:
        ax.set_title(title)
    fig.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight")
        logger.info(f"Saved Figure 1 to {save_path}")

    return fig


# --------------------------------------------------------------------------- #
# Figure 1b: Multi-method Aggregate Markup Comparison
# --------------------------------------------------------------------------- #


def compute_aggregate_markup(
    firm_markups: pd.DataFrame,
    panel_data: pd.DataFrame,
    weight_type: str = "revenue",
    ppi_matched_only: bool = False,
    ppi_data: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Compute aggregate markup from firm-level markups using revenue weights.

    Parameters
    ----------
    firm_markups : pd.DataFrame
        Firm-level markups with columns: gvkey, year, markup
    panel_data : pd.DataFrame
        Panel data with columns: gvkey, year, sale_D, cogs_D, naics
    weight_type : str
        Weight type: "revenue" or "cost"
    ppi_matched_only : bool
        If True, only include firms matched to PPI data
    ppi_data : pd.DataFrame, optional
        PPI data with naics/ind2d and year columns. Required if ppi_matched_only=True.

    Returns
    -------
    pd.DataFrame
        Aggregated markup with columns: year, agg_markup
    """
    # Merge firm markups with panel data
    df = firm_markups.merge(
        panel_data[["gvkey", "year", "sale_D", "cogs_D", "naics"]],
        on=["gvkey", "year"],
        how="left",
    )

    # Filter to PPI-matched firms if requested
    if ppi_matched_only and ppi_data is not None:
        ppi = ppi_data.copy()
        if "naics_code" in ppi.columns:
            ppi = ppi.rename(columns={"naics_code": "naics"})
        if "naics" in ppi.columns:
            ppi["naics"] = ppi["naics"].astype(str).str.strip()
            df["naics"] = df["naics"].astype(str).str.strip()
            # Keep only firms with PPI data
            ppi_keys = ppi[["naics", "year"]].drop_duplicates()
            df = df.merge(ppi_keys, on=["naics", "year"], how="inner")

    # Compute weights
    if weight_type == "revenue":
        weight_col = "sale_D"
    else:
        weight_col = "cogs_D"

    df["_total"] = df.groupby("year")[weight_col].transform("sum")
    df["_weight"] = df[weight_col] / df["_total"]

    # Aggregate
    agg = (
        df.groupby("year")
        .apply(lambda g: np.sum(g["_weight"] * g["markup"].fillna(0)), include_groups=False)
        .reset_index(name="agg_markup")
    )

    return agg


def plot_aggregate_markup_single_method(
    firm_markups: pd.DataFrame,
    panel_data: pd.DataFrame,
    method_name: str,
    agg_markup_dleu: pd.DataFrame | None = None,
    ppi_data: pd.DataFrame | None = None,
    weight_type: str = "revenue",
    year_range: tuple[int, int] | None = None,
    figsize: tuple[int, int] = (15, 10),
    save_path: Path | str | None = None,
) -> plt.Figure:
    """
    Plot aggregate markup for a single method with 3 lines:
    DLEU benchmark, all firms, and PPI-matched firms.

    Matches the template from legacy script ``1. Generate Figure 1 - Aggregate Markup.py``.

    Parameters
    ----------
    firm_markups : pd.DataFrame
        Firm-level markups with columns: gvkey, year, markup
    panel_data : pd.DataFrame
        Panel data with columns: gvkey, year, sale_D, cogs_D, naics
    method_name : str
        Name of the estimation method (for title)
    agg_markup_dleu : pd.DataFrame, optional
        DLEU benchmark with columns: year, agg_markup_DLEU
    ppi_data : pd.DataFrame, optional
        PPI data for filtering to PPI-matched firms
    weight_type : str
        Weight type for aggregation: "revenue" or "cost"
    year_range : tuple of (start, end), optional
        Restrict to this year range (inclusive).
    figsize : tuple
        Figure size in inches.
    save_path : Path or str, optional
        If provided, saves figure to this path.

    Returns
    -------
    matplotlib.figure.Figure
    """
    _apply_agg_style()

    # Compute aggregate for all firms
    agg_all = compute_aggregate_markup(
        firm_markups, panel_data, weight_type=weight_type,
        ppi_matched_only=False,
    )
    agg_all = agg_all.rename(columns={"agg_markup": "agg_markup_all_firms"})

    # Compute aggregate for PPI-matched firms
    agg_ppi = None
    if ppi_data is not None:
        agg_ppi = compute_aggregate_markup(
            firm_markups, panel_data, weight_type=weight_type,
            ppi_matched_only=True, ppi_data=ppi_data,
        )
        agg_ppi = agg_ppi.rename(columns={"agg_markup": "agg_markup_matched_ppi"})

    # Merge data
    p = agg_all.copy()
    if agg_ppi is not None:
        p = p.merge(agg_ppi, on="year", how="outer")
    if agg_markup_dleu is not None:
        p = p.merge(agg_markup_dleu, on="year", how="outer")

    if year_range is not None:
        p = p[(p["year"] >= year_range[0]) & (p["year"] <= year_range[1])]

    p = p.sort_values("year")

    # Determine year range for title
    year_min = int(p["year"].min())
    year_max = int(p["year"].max())

    # Plot (matching legacy template exactly)
    fig, ax = plt.subplots(figsize=figsize)

    # Line 1: DLEU (black, dotted)
    if "agg_markup_DLEU" in p.columns:
        ax.plot(p["year"], p["agg_markup_DLEU"],
                color="black", linestyle=":", linewidth=3)

    # Line 2: Replication / All firms (darkgreen, solid)
    ax.plot(p["year"], p["agg_markup_all_firms"],
            color="darkgreen", linestyle="-", linewidth=3)

    # Line 3: Firms matched to PPI (orange, dashed)
    if "agg_markup_matched_ppi" in p.columns:
        ax.plot(p["year"], p["agg_markup_matched_ppi"],
                color="orange", linestyle="--", linewidth=3)

    # Legend (matching legacy order)
    labels = []
    if "agg_markup_DLEU" in p.columns:
        labels.append("DLEU")
    labels.append("Replication")
    if "agg_markup_matched_ppi" in p.columns:
        labels.append("Firms Matched to PPI")
    ax.legend(labels)

    ax.set_ylabel("Aggregate Markup")
    fig.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight")
        logger.info(f"Saved {method_name} aggregate markup to {save_path}")

    return fig


def plot_aggregate_markup_comparison(
    method_markups: dict[str, pd.DataFrame],
    panel_data: pd.DataFrame,
    agg_markup_dleu: pd.DataFrame | None = None,
    ppi_data: pd.DataFrame | None = None,
    weight_type: str = "revenue",
    year_range: tuple[int, int] | None = None,
    figsize: tuple[int, int] = (15, 10),
    save_path: Path | str | None = None,
    title: str | None = None,
) -> plt.Figure:
    """
    Plot aggregate markup comparison for multiple estimation methods on one plot.

    Parameters
    ----------
    method_markups : dict
        Dictionary mapping method name to firm-level markup DataFrame.
        Each DataFrame should have columns: gvkey, year, markup
    panel_data : pd.DataFrame
        Panel data with columns: gvkey, year, sale_D, cogs_D, naics
    agg_markup_dleu : pd.DataFrame, optional
        DLEU benchmark with columns: year, agg_markup_DLEU
    ppi_data : pd.DataFrame, optional
        PPI data for filtering to PPI-matched firms
    weight_type : str
        Weight type for aggregation: "revenue" or "cost"
    year_range : tuple of (start, end), optional
        Restrict to this year range (inclusive).
    figsize : tuple
        Figure size in inches.
    save_path : Path or str, optional
        If provided, saves figure to this path.
    title : str, optional
        Plot title.

    Returns
    -------
    matplotlib.figure.Figure
    """
    _apply_agg_style()

    # Compute aggregates for each method
    all_agg = {}
    for method_name, markups in method_markups.items():
        agg = compute_aggregate_markup(
            markups, panel_data, weight_type=weight_type,
            ppi_matched_only=False, ppi_data=ppi_data,
        )
        agg = agg.rename(columns={"agg_markup": f"agg_markup_{method_name}"})
        all_agg[method_name] = agg

    # Merge all aggregates
    p = None
    for method_name, agg in all_agg.items():
        if p is None:
            p = agg.copy()
        else:
            p = p.merge(agg, on="year", how="outer")

    # Add DLEU benchmark
    if agg_markup_dleu is not None:
        p = p.merge(agg_markup_dleu, on="year", how="outer")

    if year_range is not None:
        p = p[(p["year"] >= year_range[0]) & (p["year"] <= year_range[1])]

    p = p.sort_values("year")

    # Plot
    fig, ax = plt.subplots(figsize=figsize)

    # Color and style mapping
    method_styles = {
        "wooldridge_iv": {"color": "darkgreen", "linestyle": "-", "label": "Wooldridge IV"},
        "cost_share": {"color": "blue", "linestyle": "--", "label": "Cost Share"},
        "acf": {"color": "red", "linestyle": "-.", "label": "ACF"},
    }

    # Plot DLEU benchmark first (dashed black)
    if "agg_markup_DLEU" in p.columns:
        ax.plot(p["year"], p["agg_markup_DLEU"],
                color="black", linestyle=":", linewidth=3, label="DLEU")

    # Plot each method
    for method_name in method_markups.keys():
        col = f"agg_markup_{method_name}"
        if col in p.columns:
            style = method_styles.get(method_name, {"color": "gray", "linestyle": "-", "label": method_name})
            ax.plot(p["year"], p[col],
                    color=style["color"], linestyle=style["linestyle"],
                    linewidth=3, label=style["label"])

    ax.legend(loc="upper left")
    ax.set_ylabel("Aggregate Markup")
    ax.set_xlabel("Year")
    if title:
        ax.set_title(title)
    fig.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight")
        logger.info(f"Saved multi-method comparison to {save_path}")

    return fig


# --------------------------------------------------------------------------- #
# Data preparation for Figure 2 (from legacy 0.5)
# --------------------------------------------------------------------------- #


def prepare_scatter_data(
    firm_markups: pd.DataFrame,
    panel_data: pd.DataFrame,
    ppi_data: pd.DataFrame,
    cpi_data: pd.DataFrame,
    min_years: int = 5,
    year_range: tuple[int, int] | None = None,
) -> pd.DataFrame:
    """
    Prepare scatter data: per-firm CAGR of markup, PPI, and COGS.

    Based on legacy script ``0.5 Prepare Data for Figures and Tables.py``.

    Parameters
    ----------
    firm_markups : pd.DataFrame
        Firm-level markups with columns: gvkey, year, ind2d, markup.
    panel_data : pd.DataFrame
        Compustat panel with columns: gvkey, year, cogs, sale, naics, conm.
    ppi_data : pd.DataFrame
        PPI data with columns: ind2d (or naics-based key), year, ppi.
    cpi_data : pd.DataFrame
        CPI data with columns: year, CPI.
    min_years : int, default 5
        Minimum number of years a firm must appear.
    year_range : tuple of (start, end), optional
        Restrict to this year range (inclusive).

    Returns
    -------
    pd.DataFrame
        One row per firm with columns: gvkey, cagr_markup, cagr_PPI, cagr_COGS,
        sale_CPI, dot_size, ind2d, ind2d_definition (if available), conm, naics.
    """
    # Merge markups into panel
    merge_cols = ["gvkey", "year"]
    if "ind2d" in firm_markups.columns and "ind2d" not in panel_data.columns:
        merge_cols.append("ind2d")
    df = panel_data.merge(
        firm_markups[["gvkey", "year", "markup"]], on=["gvkey", "year"], how="inner"
    )

    # Merge PPI (skip if panel already has it)
    if "ppi" not in df.columns and "PPI" not in df.columns:
        # Determine merge key based on available columns
        ppi = ppi_data.copy()
        # Standardize column names
        if "PPI" in ppi.columns:
            ppi = ppi.rename(columns={"PPI": "ppi"})
        if "naics_code" in ppi.columns:
            ppi = ppi.rename(columns={"naics_code": "naics"})

        # Try different merge keys
        if "ind2d" in ppi.columns and "ind2d" in df.columns:
            df = df.merge(ppi, on=["ind2d", "year"], how="left")
        elif "naics" in ppi.columns and "naics" in df.columns:
            df = df.merge(ppi, on=["naics", "year"], how="left")
        else:
            # Try to create ind2d from naics in ppi
            if "naics" in ppi.columns:
                ppi["ind2d"] = pd.to_numeric(ppi["naics"].astype(str).str.slice(0, 2), errors="coerce")
                if "ind2d" in df.columns:
                    df = df.merge(ppi[["ind2d", "year", "ppi"]], on=["ind2d", "year"], how="left")
    elif "PPI" in df.columns:
        df = df.rename(columns={"PPI": "ppi"})
    df = df.dropna(subset=["ppi"])

    # Merge CPI (skip if panel already has it)
    if "CPI" not in df.columns:
        cpi = cpi_data.copy()
        # Standardize column name
        if "cpi" in cpi.columns:
            cpi = cpi.rename(columns={"cpi": "CPI"})
        df = df.merge(cpi, on="year", how="left")

    # CPI-adjusted variables
    df["PPI_CPI"] = df["ppi"] / df["CPI"] * 100

    sale_col = "sale" if "sale" in df.columns else "sale_D"
    cogs_col = "cogs" if "cogs" in df.columns else "cogs_D"
    df["sale_CPI"] = df[sale_col] / df["CPI"] * 100
    df["COGS_CPI"] = df[cogs_col] / df["CPI"] * 100

    # Filter year range
    if year_range is not None:
        df = df[(df["year"] >= year_range[0]) & (df["year"] <= year_range[1])]

    # Keep firms with min_years of data
    firm_span = (
        df.sort_values(["gvkey", "year"])
        .groupby("gvkey")["year"]
        .agg(["first", "last"])
        .reset_index()
    )
    firm_span["n"] = firm_span["last"] - firm_span["first"] + 1
    keep = firm_span.loc[firm_span["n"] >= min_years, "gvkey"]
    df = df[df["gvkey"].isin(keep)]

    if len(df) == 0:
        logger.warning("No firms remaining after min_years filter")
        return pd.DataFrame()

    # Sales weight and dot size
    share = df.drop_duplicates(subset="gvkey", keep="last")[["gvkey", "sale_CPI"]].copy()
    share["dot_size"] = np.log(share["sale_CPI"].clip(lower=1))

    # Company info
    char_cols = ["gvkey"]
    if "conm" in df.columns:
        char_cols.append("conm")
    if "naics" in df.columns:
        char_cols.append("naics")
    char = df[char_cols].drop_duplicates(subset="gvkey", keep="last")

    # Industry description
    ind_cols = ["gvkey"]
    if "ind2d_definition" in df.columns:
        ind_cols.append("ind2d_definition")
    elif "ind2d" in df.columns:
        ind_cols.append("ind2d")
    naics_info = df[ind_cols].drop_duplicates(subset="gvkey", keep="last")

    # First/last per firm for CAGR
    agg_df = (
        df.sort_values(["gvkey", "year"])
        .groupby("gvkey")
        .agg(
            first_year=("year", "first"),
            last_year=("year", "last"),
            first_markup=("markup", "first"),
            last_markup=("markup", "last"),
            first_PPI=("PPI_CPI", "first"),
            last_PPI=("PPI_CPI", "last"),
            first_COGS=("COGS_CPI", "first"),
            last_COGS=("COGS_CPI", "last"),
        )
        .reset_index()
    )

    agg_df["periods"] = agg_df["last_year"] - agg_df["first_year"]
    agg_df = agg_df[agg_df["periods"] > 0]

    agg_df["cagr_markup"] = cagr(agg_df["first_markup"], agg_df["last_markup"], agg_df["periods"])
    agg_df["cagr_PPI"] = cagr(agg_df["first_PPI"], agg_df["last_PPI"], agg_df["periods"])
    agg_df["cagr_COGS"] = cagr(agg_df["first_COGS"], agg_df["last_COGS"], agg_df["periods"])

    # Merge everything
    result = agg_df.merge(naics_info, on="gvkey", how="left")
    result = result.merge(share, on="gvkey", how="left")
    result = result.merge(char, on="gvkey", how="left")
    result["markup_closest_end"] = result["last_markup"]

    logger.info(f"Prepared scatter data: {len(result)} firms")
    return result


# --------------------------------------------------------------------------- #
# Figure 2: CAGR of PPI vs Markup scatter
# --------------------------------------------------------------------------- #


def plot_markup_vs_ppi(
    scatter_data: pd.DataFrame,
    weight: str = "sale_CPI",
    outlier_thresholds: dict | None = None,
    title: str = "Growth of PPI and Markup",
    figsize: tuple[int, int] = (15, 10),
    save_path: Path | str | None = None,
    by_industry: bool = False,
    industry_col: str = "ind2d_definition",
    industry_dir: Path | str | None = None,
) -> plt.Figure:
    """
    Scatter plot of markup CAGR vs PPI CAGR with weighted regression.

    Based on legacy script ``2. Generate Figure 2 - CAGR of PPI vs Markup.py``.

    Parameters
    ----------
    scatter_data : pd.DataFrame
        Output from prepare_scatter_data().
    weight : str, default "sale_CPI"
        Column for regression weights.
    outlier_thresholds : dict, optional
        Thresholds for truncation. Keys: "ppi_low", "ppi_high", "markup_high".
        Defaults: {"ppi_low": -20, "ppi_high": 20, "markup_high": 100}.
    title : str
        Plot title for full-sample figure.
    figsize : tuple
        Figure size in inches.
    save_path : Path or str, optional
        Save path for the full-sample figure.
    by_industry : bool, default False
        If True, also generate per-industry plots.
    industry_col : str, default "ind2d_definition"
        Column for industry labels.
    industry_dir : Path or str, optional
        Directory for per-industry figures. Required if by_industry=True.

    Returns
    -------
    matplotlib.figure.Figure
        The full-sample figure.
    """
    if outlier_thresholds is None:
        outlier_thresholds = {"ppi_low": -20, "ppi_high": 20, "markup_high": 100}

    p = scatter_data.copy()

    # Truncate outliers
    p = p[p["cagr_PPI"] >= outlier_thresholds.get("ppi_low", -20)]
    p = p[p["cagr_PPI"] <= outlier_thresholds.get("ppi_high", 20)]
    p = p[p["cagr_markup"] <= outlier_thresholds.get("markup_high", 100)]
    if "markup_low" in outlier_thresholds:
        p = p[p["cagr_markup"] >= outlier_thresholds["markup_low"]]

    # Full sample plot
    fig = _scatter_with_regression(
        p, "cagr_markup", "cagr_PPI", weight,
        x_label="Markup Growth", y_label="PPI Growth",
        title=title, figsize=figsize,
    )

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight")
        logger.info(f"Saved Figure 2 to {save_path}")

    # Per-industry plots
    if by_industry and industry_col in p.columns:
        if industry_dir is None:
            raise ValueError("industry_dir must be provided when by_industry=True")
        industry_dir = Path(industry_dir)
        industry_dir.mkdir(parents=True, exist_ok=True)

        for sector in p[industry_col].dropna().unique():
            temp = p[p[industry_col] == sector]
            if len(temp) < 3:
                continue
            ind_fig = _scatter_with_regression(
                temp, "cagr_markup", "cagr_PPI", weight,
                x_label="Markup Growth", y_label="PPI Growth",
                title=str(sector), figsize=figsize,
            )
            ind_fig.savefig(industry_dir / f"{sector}.pdf", bbox_inches="tight")
            plt.close(ind_fig)

    return fig


def _scatter_with_regression(
    data: pd.DataFrame,
    x_var: str,
    y_var: str,
    weight_var: str,
    x_label: str = "",
    y_label: str = "",
    title: str = "",
    figsize: tuple[int, int] = (15, 10),
) -> plt.Figure:
    """Create scatter plot with weighted OLS regression line and R^2."""
    import matplotlib.patches as mpl_patches
    import seaborn as sns

    fig, ax = plt.subplots(figsize=figsize)

    # Scatter
    size_col = "dot_size" if "dot_size" in data.columns else None
    sns.scatterplot(
        data=data, x=x_var, y=y_var,
        size=size_col, color="darkgreen", alpha=1, legend=False, ax=ax,
    )

    # Weighted OLS using numpy (avoids sklearn dependency)
    valid = data[[x_var, y_var, weight_var]].dropna()
    if len(valid) >= 2:
        x_vals = valid[x_var].to_numpy()
        y_vals = valid[y_var].to_numpy()
        w = valid[weight_var].to_numpy()

        # Weighted least squares: y = a + b*x
        X_design = np.column_stack([np.ones_like(x_vals), x_vals])
        W = np.diag(w)
        beta = np.linalg.lstsq(X_design.T @ W @ X_design, X_design.T @ W @ y_vals, rcond=None)[0]
        y_pred = X_design @ beta

        # Weighted R^2
        ss_res = np.sum(w * (y_vals - y_pred) ** 2)
        ss_tot = np.sum(w * (y_vals - np.average(y_vals, weights=w)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        sort_idx = np.argsort(x_vals)
        ax.plot(x_vals[sort_idx], y_pred[sort_idx], color="gray")

        handles = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white", lw=0, alpha=0)]
        labels = [f"R$^2$: {r2:.4f}"]
        ax.legend(
            handles, labels, loc="best", fontsize=20, frameon=True,
            fancybox=True, framealpha=0.7, borderpad=0.3,
            handlelength=0, handletextpad=0,
        )

        logger.info(f"  {title} — beta_hat: {beta[1]:.4f}, R^2: {r2:.4f}")

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
        ax.set_title(title)
    fig.tight_layout()

    return fig
