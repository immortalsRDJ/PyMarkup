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
    agg_markup: pd.DataFrame,
    agg_markup_ppi_matched: pd.DataFrame | None = None,
    agg_markup_dleu: pd.DataFrame | None = None,
    year_range: tuple[int, int] | None = None,
    figsize: tuple[int, int] = (15, 10),
    save_path: Path | str | None = None,
) -> plt.Figure:
    """
    Plot aggregate markup comparison over time (Figure 1).

    Replicates legacy script ``1. Generate Figure 1 - Aggregate Markup.py``.
    Plots up to 3 series: DLEU benchmark, replication (all firms),
    and firms matched to PPI.

    Parameters
    ----------
    agg_markup : pd.DataFrame
        Aggregate markup for all firms with columns: year, MARKUP_spec1
        (from ``agg_markup_annual.csv``).
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

    Returns
    -------
    matplotlib.figure.Figure
    """
    _apply_agg_style()

    # Merge all series
    p = agg_markup.rename(
        columns={"MARKUP_spec1": "agg_markup_all_firms"}
    ).copy()

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
    fig.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight")
        logger.info(f"Saved Figure 1 to {save_path}")

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
    if "ppi" not in df.columns:
        ppi_merge_key = "ind2d" if "ind2d" in ppi_data.columns else "naics"
        df = df.merge(ppi_data, on=[ppi_merge_key, "year"], how="left")
    df = df.dropna(subset=["ppi"])

    # Merge CPI (skip if panel already has it)
    if "CPI" not in df.columns:
        df = df.merge(cpi_data, on="year", how="left")

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
