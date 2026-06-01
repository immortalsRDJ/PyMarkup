"""
Generate report figures for markup analysis.

This script produces four key figures:
1. Full sample vs. DEU sample comparison (BMY critique replication)
2. Revenue-weighted vs. Cost-weighted aggregation comparison
3. Firm-level contribution ranking (top pushers and pullers)
4. Top markup firms comparison across years (e.g., 2000 vs 2016)

Usage:
    python scripts/generate_report_figures.py
    python scripts/generate_report_figures.py --method cost_share
    python scripts/generate_report_figures.py --output-dir Output/report
    python scripts/generate_report_figures.py --figures 1,2,3,4
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PyMarkup import MarkupPipeline, PipelineConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class PipelineCache:
    """Cache pipeline results to avoid redundant computation."""

    def __init__(self, config_path: Path, method: str):
        self.config_path = config_path
        self.method = method
        self._full_sample = None
        self._deu_sample = None

    def get_full_sample(self):
        """Get or compute full sample results."""
        if self._full_sample is None:
            logger.info("Running pipeline with FULL sample...")
            config = PipelineConfig.from_yaml(self.config_path)
            config.use_deu_sample = False
            config.estimator.method = self.method

            pipeline = MarkupPipeline(config)
            pipeline.run_data_preparation()
            elasticities = pipeline.run_estimation()
            markups = pipeline.run_markup_calculation(elasticities)

            self._full_sample = {
                "pipeline": pipeline,
                "markups": markups,
                "panel_data": pipeline.panel_data,
            }
        return self._full_sample

    def get_deu_sample(self):
        """Get or compute DEU sample results."""
        if self._deu_sample is None:
            logger.info("Running pipeline with DEU sample...")
            config = PipelineConfig.from_yaml(self.config_path)
            config.use_deu_sample = True
            config.estimator.method = self.method

            pipeline = MarkupPipeline(config)
            pipeline.run_data_preparation()
            elasticities = pipeline.run_estimation()
            markups = pipeline.run_markup_calculation(elasticities)

            self._deu_sample = {
                "pipeline": pipeline,
                "markups": markups,
                "panel_data": pipeline.panel_data,
            }
        return self._deu_sample


def setup_plot_style():
    """Set up matplotlib style for publication-quality figures."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update({
        "font.size": 20,
        "axes.titlesize": 24,
        "axes.labelsize": 20,
        "xtick.labelsize": 18,
        "ytick.labelsize": 18,
        "legend.fontsize": 18,
        "figure.figsize": (14, 10),
        "lines.linewidth": 3,
    })


def compute_aggregate_markup_weighted(
    firm_markups: pd.DataFrame,
    panel_data: pd.DataFrame,
    weight_type: str = "revenue",
) -> pd.DataFrame:
    """
    Compute aggregate markup with specified weighting.

    Parameters
    ----------
    firm_markups : pd.DataFrame
        Firm-level markups with gvkey, year, markup columns
    panel_data : pd.DataFrame
        Panel data with sale_D, cogs_D columns
    weight_type : str
        "revenue" for sale_D weighting, "cost" for cogs_D weighting

    Returns
    -------
    pd.DataFrame
        Yearly aggregate markups
    """
    df = firm_markups.merge(
        panel_data[["gvkey", "year", "sale_D", "cogs_D"]],
        on=["gvkey", "year"],
        how="left",
    )

    # Remove invalid markups
    df = df[df["markup"].notna() & (df["markup"] > 0) & (df["markup"] < 50)]

    if weight_type == "revenue":
        weight_col = "sale_D"
    elif weight_type == "cost":
        weight_col = "cogs_D"
    else:
        raise ValueError(f"Unknown weight_type: {weight_type}")

    # Compute weighted average by year
    df["total_weight"] = df.groupby("year")[weight_col].transform("sum")
    df["weight"] = df[weight_col] / df["total_weight"]
    df["weighted_markup"] = df["markup"] * df["weight"]

    agg = df.groupby("year").agg(
        markup=("weighted_markup", "sum"),
        n_firms=("gvkey", "nunique"),
    ).reset_index()

    return agg


def figure1_full_vs_deu_sample(
    cache: PipelineCache,
    method: str = "wooldridge_iv",
    output_dir: Path = Path("Output/report"),
) -> plt.Figure:
    """
    Figure 1: Full sample vs. DEU sample comparison.

    This directly addresses BMY's critique by showing how the markup trend
    differs between the restricted DEU sample and the full Compustat sample.
    """
    logger.info("=" * 60)
    logger.info("Figure 1: Full Sample vs. DEU Sample")
    logger.info("=" * 60)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get cached results
    full_data = cache.get_full_sample()
    deu_data = cache.get_deu_sample()

    # Compute aggregate markups
    logger.info("Computing aggregate markups...")
    agg_full = compute_aggregate_markup_weighted(
        full_data["markups"][method], full_data["panel_data"], weight_type="revenue"
    )
    agg_deu = compute_aggregate_markup_weighted(
        deu_data["markups"][method], deu_data["panel_data"], weight_type="revenue"
    )

    # Plot
    setup_plot_style()
    fig, ax = plt.subplots(figsize=(14, 9))

    ax.plot(agg_full["year"], agg_full["markup"],
            color="blue", linestyle="-", linewidth=3,
            label=f"Full Sample (n={agg_full['n_firms'].mean():.0f} firms/year)")
    ax.plot(agg_deu["year"], agg_deu["markup"],
            color="red", linestyle="--", linewidth=3,
            label=f"DEU Sample (n={agg_deu['n_firms'].mean():.0f} firms/year)")

    ax.set_xlabel("Year")
    ax.set_ylabel("Aggregate Markup (Revenue-Weighted)")
    ax.set_title(f"Full Sample vs. DEU Sample Markup Trends\n({method.replace('_', ' ').title()})")
    ax.legend(loc="upper left")
    ax.set_xlim(1955, agg_full["year"].max())

    # Add annotation about the difference
    year_2016 = 2016
    if year_2016 in agg_full["year"].values and year_2016 in agg_deu["year"].values:
        markup_full_2016 = agg_full[agg_full["year"] == year_2016]["markup"].values[0]
        markup_deu_2016 = agg_deu[agg_deu["year"] == year_2016]["markup"].values[0]
        diff = markup_deu_2016 - markup_full_2016
        ax.annotate(
            f"DEU - Full = {diff:+.3f} in 2016",
            xy=(year_2016, markup_deu_2016),
            xytext=(year_2016 - 15, markup_deu_2016 + 0.1),
            fontsize=16,
            arrowprops=dict(arrowstyle="->", color="gray"),
        )

    fig.tight_layout()

    # Save
    save_path = output_dir / f"Figure1_FullSample_vs_DEU_{method}.pdf"
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
    logger.info(f"Saved: {save_path}")

    # Also save data
    agg_full["sample"] = "full"
    agg_deu["sample"] = "deu"
    combined = pd.concat([agg_full, agg_deu])
    combined.to_csv(output_dir / f"Figure1_data_{method}.csv", index=False)

    return fig


def figure2_revenue_vs_cost_weighted(
    cache: PipelineCache,
    method: str = "wooldridge_iv",
    output_dir: Path = Path("Output/report"),
) -> plt.Figure:
    """
    Figure 2: Revenue-weighted vs. Cost-weighted aggregation.

    Cost-weighted gives higher weight to high-cost, low-profit firms,
    potentially correcting for "big firm bias" in revenue weighting.
    """
    logger.info("=" * 60)
    logger.info("Figure 2: Revenue-Weighted vs. Cost-Weighted Aggregation")
    logger.info("=" * 60)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get cached results (use full sample)
    full_data = cache.get_full_sample()

    # Compute aggregate markups with different weights
    logger.info("Computing aggregate markups with different weights...")
    agg_revenue = compute_aggregate_markup_weighted(
        full_data["markups"][method], full_data["panel_data"], weight_type="revenue"
    )
    agg_cost = compute_aggregate_markup_weighted(
        full_data["markups"][method], full_data["panel_data"], weight_type="cost"
    )

    # Plot
    setup_plot_style()
    fig, ax = plt.subplots(figsize=(14, 9))

    ax.plot(agg_revenue["year"], agg_revenue["markup"],
            color="blue", linestyle="-", linewidth=3,
            label="Revenue-Weighted")
    ax.plot(agg_cost["year"], agg_cost["markup"],
            color="green", linestyle="--", linewidth=3,
            label="Cost-Weighted")

    ax.set_xlabel("Year")
    ax.set_ylabel("Aggregate Markup")
    ax.set_title(f"Revenue-Weighted vs. Cost-Weighted Markup Aggregation\n({method.replace('_', ' ').title()})")
    ax.legend(loc="upper left")
    ax.set_xlim(1955, agg_revenue["year"].max())

    # Add annotation about interpretation
    ax.text(
        0.98, 0.02,
        "Large gap → Strong reallocation effect\nSmall gap → Within-firm changes dominate",
        transform=ax.transAxes,
        fontsize=16,
        verticalalignment="bottom",
        horizontalalignment="right",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    fig.tight_layout()

    # Save
    save_path = output_dir / f"Figure2_RevenueVsCost_{method}.pdf"
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
    logger.info(f"Saved: {save_path}")

    # Also save data
    agg_revenue["weight_type"] = "revenue"
    agg_cost["weight_type"] = "cost"
    combined = pd.concat([agg_revenue, agg_cost])
    combined.to_csv(output_dir / f"Figure2_data_{method}.csv", index=False)

    return fig


def figure3_firm_contribution_ranking(
    cache: PipelineCache,
    method: str = "wooldridge_iv",
    output_dir: Path = Path("Output/report"),
    base_year: int = 1980,
    end_year: int = 2016,
    top_n: int = 10,
) -> plt.Figure:
    """
    Figure 3: Firm-level contribution ranking.

    Shows top 10 firms that push markup up (pushers) and
    top 10 that pull it down (pullers), with NAICS sector labels.
    """
    logger.info("=" * 60)
    logger.info("Figure 3: Firm-Level Contribution Ranking")
    logger.info("=" * 60)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get cached results (use full sample)
    full_data = cache.get_full_sample()

    # Merge with panel data for weights and firm info
    # Note: markups already has ind2d, so don't include it from panel_data
    logger.info("Computing firm contributions...")
    df = full_data["markups"][method].merge(
        full_data["panel_data"][["gvkey", "year", "sale_D", "cogs_D", "conm"]],
        on=["gvkey", "year"],
        how="left",
    )

    # Filter valid markups
    df = df[df["markup"].notna() & (df["markup"] > 0) & (df["markup"] < 50)]

    # Ensure ind2d is numeric
    df["ind2d"] = pd.to_numeric(df["ind2d"], errors="coerce")

    # Load NAICS descriptions
    naics_path = Path("Input/Other/NAICS_2D_Description.xlsx")
    if naics_path.exists():
        naics_desc = pd.read_excel(naics_path)
        naics_desc.columns = naics_desc.columns.str.strip().str.lower()
        # Rename to sector_name for consistency
        if "sector_definition" in naics_desc.columns:
            naics_desc = naics_desc.rename(columns={"sector_definition": "sector_name"})
        naics_desc["ind2d"] = pd.to_numeric(naics_desc["ind2d"], errors="coerce")
        df = df.merge(naics_desc[["ind2d", "sector_name"]], on="ind2d", how="left")
    else:
        df["sector_name"] = df["ind2d"].astype(str)

    # Compute contribution to aggregate markup change
    # Contribution = weight_i * (markup_i - avg_markup)

    # Get data for base and end years
    df_base = df[df["year"] == base_year].copy()
    df_end = df[df["year"] == end_year].copy()

    # For firms present in both years, compute their contribution to the change
    firms_both = set(df_base["gvkey"]) & set(df_end["gvkey"])
    logger.info(f"Firms present in both {base_year} and {end_year}: {len(firms_both)}")

    df_base = df_base[df_base["gvkey"].isin(firms_both)]
    df_end = df_end[df_end["gvkey"].isin(firms_both)]

    # Compute weights in both years
    total_sales_end = df_end["sale_D"].sum()
    total_sales_base = df_base["sale_D"].sum()
    df_end["weight"] = df_end["sale_D"] / total_sales_end
    df_base["weight_base"] = df_base["sale_D"] / total_sales_base

    # Compute markup change for each firm
    df_change = df_end[["gvkey", "conm", "ind2d", "sector_name", "markup", "weight"]].merge(
        df_base[["gvkey", "markup", "weight_base"]].rename(columns={"markup": "markup_base"}),
        on="gvkey",
    )
    df_change["markup_change"] = df_change["markup"] - df_change["markup_base"]

    # Contribution to aggregate markup change = weight * markup_change
    # Note: This uses end-year weights, so sum ≠ true aggregate change
    df_change["contribution"] = df_change["weight"] * df_change["markup_change"]

    # Compute TRUE aggregate markup change (for annotation)
    true_agg_base = (df_change["markup_base"] * df_change["weight_base"]).sum()
    true_agg_end = (df_change["markup"] * df_change["weight"]).sum()
    true_agg_change = true_agg_end - true_agg_base

    # Sort by contribution
    df_change = df_change.sort_values("contribution", ascending=False)

    # Get top pushers (positive contribution) and pullers (negative contribution)
    top_pushers = df_change.head(top_n).copy()
    top_pullers = df_change.tail(top_n).copy()

    # Combine for plotting
    top_pushers["group"] = "Pushers (↑)"
    top_pullers["group"] = "Pullers (↓)"
    plot_data = pd.concat([top_pushers, top_pullers.iloc[::-1]])  # Reverse pullers for plotting

    # Create label with company name and sector
    plot_data["label"] = plot_data.apply(
        lambda x: f"{x['conm'][:20]}... ({x['sector_name'][:15]})"
        if pd.notna(x['conm']) and len(str(x['conm'])) > 20
        else f"{x['conm']} ({x['sector_name'][:15]})" if pd.notna(x['conm'])
        else f"gvkey={x['gvkey']}",
        axis=1
    )

    # Plot
    setup_plot_style()
    fig, ax = plt.subplots(figsize=(14, 10))

    colors = ["green" if c > 0 else "red" for c in plot_data["contribution"]]
    y_pos = range(len(plot_data))

    bars = ax.barh(y_pos, plot_data["contribution"], color=colors, alpha=0.7, edgecolor="black")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(plot_data["label"], fontsize=14)
    ax.axvline(0, color="black", linewidth=1)

    ax.set_xlabel(f"Contribution to Aggregate Markup Change ({base_year}-{end_year})")
    ax.set_title(f"Top {top_n} Firms Pushing and Pulling Aggregate Markup\n({method.replace('_', ' ').title()}, {base_year}-{end_year})")

    # Add separator line between pushers and pullers
    # Note: barh plots from bottom (y=0) to top, so pushers (first 10) are at bottom, pullers at top
    ax.axhline(top_n - 0.5, color="gray", linestyle="--", linewidth=1)
    ax.text(ax.get_xlim()[1] * 0.9, top_n + 0.5, "PULLERS", fontsize=16, ha="right", va="bottom", color="red", fontweight="bold")
    ax.text(ax.get_xlim()[1] * 0.9, top_n - 1.5, "PUSHERS", fontsize=16, ha="right", va="top", color="green", fontweight="bold")

    # Add annotation with true aggregate markup change
    ax.text(
        0.02, 0.98,
        f"Aggregate markup: {true_agg_base:.2f} ({base_year}) → {true_agg_end:.2f} ({end_year})\n"
        f"True change: {true_agg_change:+.4f}\n"
        f"Top {top_n} pushers contribution: {top_pushers['contribution'].sum():+.4f}\n"
        f"Top {top_n} pullers contribution: {top_pullers['contribution'].sum():+.4f}",
        transform=ax.transAxes,
        fontsize=14,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    fig.tight_layout()

    # Save
    save_path = output_dir / f"Figure3_FirmContribution_{method}_{base_year}_{end_year}.pdf"
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
    logger.info(f"Saved: {save_path}")

    # Save data
    df_change.to_csv(output_dir / f"Figure3_data_{method}_{base_year}_{end_year}.csv", index=False)

    # Also save top contributors summary
    summary = pd.concat([
        top_pushers[["conm", "ind2d", "sector_name", "markup_base", "markup", "markup_change", "weight", "contribution"]],
        top_pullers[["conm", "ind2d", "sector_name", "markup_base", "markup", "markup_change", "weight", "contribution"]],
    ])
    summary.to_csv(output_dir / f"Figure3_top_contributors_{method}_{base_year}_{end_year}.csv", index=False)
    logger.info(f"Saved contributor summary")

    return fig


def figure4_top_markup_firms(
    cache: PipelineCache,
    method: str = "wooldridge_iv",
    output_dir: Path = Path("Output/report"),
    year1: int = 2000,
    year2: int = 2016,
    top_n: int = 15,
    min_weight: float = 0.001,
) -> plt.Figure:
    """
    Figure 4: Top markup firms comparison across years.

    Shows the top N high-markup firms (filtered by minimum market share)
    in two different years, highlighting new entrants like tech giants.
    """
    logger.info("=" * 60)
    logger.info(f"Figure 4: Top Markup Firms ({year1} vs {year2})")
    logger.info("=" * 60)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get cached results (use full sample)
    full_data = cache.get_full_sample()
    markups = full_data["markups"][method]
    panel_data = full_data["panel_data"]

    # Merge markups with panel data
    df = markups.merge(
        panel_data[["gvkey", "year", "sale_D", "conm"]],
        on=["gvkey", "year"],
        how="left",
    )

    # Compute weights by year
    df["weight"] = df.groupby("year")["sale_D"].transform(lambda x: x / x.sum())

    def get_top_markup_firms(df, year, top_n, min_weight):
        """Get top N firms by markup in a given year, filtered by minimum weight."""
        year_df = df[df["year"] == year].copy()
        year_df = year_df[year_df["weight"] >= min_weight]
        year_df = year_df[year_df["markup"].notna() & (year_df["markup"] > 0) & (year_df["markup"] < 50)]
        year_df = year_df.nlargest(top_n, "markup")
        return year_df[["conm", "markup", "weight", "sale_D"]]

    # Get data for both years
    df_year1 = get_top_markup_firms(df, year1, top_n, min_weight)
    df_year2 = get_top_markup_firms(df, year2, top_n, min_weight)

    logger.info(f"\n{year1} Top {top_n}:")
    for _, row in df_year1.iterrows():
        name = row['conm'][:30] if pd.notna(row['conm']) else "Unknown"
        logger.info(f"  {name:30s} markup={row['markup']:.2f}")

    logger.info(f"\n{year2} Top {top_n}:")
    for _, row in df_year2.iterrows():
        name = row['conm'][:30] if pd.notna(row['conm']) else "Unknown"
        logger.info(f"  {name:30s} markup={row['markup']:.2f}")

    # Create figure
    setup_plot_style()
    fig, axes = plt.subplots(1, 2, figsize=(18, 10))

    # Year 1 plot
    ax1 = axes[0]
    df_year1_sorted = df_year1.sort_values("markup", ascending=True)
    colors1 = plt.cm.Blues(np.linspace(0.4, 0.9, len(df_year1_sorted)))
    ax1.barh(range(len(df_year1_sorted)), df_year1_sorted["markup"], color=colors1)
    ax1.set_yticks(range(len(df_year1_sorted)))
    ax1.set_yticklabels(
        [name[:25] if pd.notna(name) else "Unknown" for name in df_year1_sorted["conm"]],
        fontsize=14
    )
    ax1.set_xlabel("Markup", fontsize=16)
    ax1.set_title(f"Top {top_n} High-Markup Firms ({year1})", fontsize=20, fontweight='bold')
    ax1.axvline(x=1, color='red', linestyle='--', alpha=0.5)
    ax1.set_xlim(0, max(df_year1_sorted["markup"]) * 1.15)

    for i, (idx, row) in enumerate(df_year1_sorted.iterrows()):
        ax1.text(row['markup'] + 0.1, i, f"{row['markup']:.2f}", va='center', fontsize=12)

    # Year 2 plot
    ax2 = axes[1]
    df_year2_sorted = df_year2.sort_values("markup", ascending=True)
    colors2 = plt.cm.Oranges(np.linspace(0.4, 0.9, len(df_year2_sorted)))
    ax2.barh(range(len(df_year2_sorted)), df_year2_sorted["markup"], color=colors2)
    ax2.set_yticks(range(len(df_year2_sorted)))
    ax2.set_yticklabels(
        [name[:25] if pd.notna(name) else "Unknown" for name in df_year2_sorted["conm"]],
        fontsize=14
    )
    ax2.set_xlabel("Markup", fontsize=16)
    ax2.set_title(f"Top {top_n} High-Markup Firms ({year2})", fontsize=20, fontweight='bold')
    ax2.axvline(x=1, color='red', linestyle='--', alpha=0.5)
    ax2.set_xlim(0, max(df_year2_sorted["markup"]) * 1.15)

    for i, (idx, row) in enumerate(df_year2_sorted.iterrows()):
        ax2.text(row['markup'] + 0.1, i, f"{row['markup']:.2f}", va='center', fontsize=12)

    # Add note about new entrants
    new_in_year2 = set(df_year2["conm"]) - set(df_year1["conm"])
    if new_in_year2:
        new_firms_str = ", ".join(list(new_in_year2)[:5])
        if len(new_in_year2) > 5:
            new_firms_str += f", ... (+{len(new_in_year2) - 5} more)"
        fig.text(
            0.5, 0.02,
            f"New in {year2} Top {top_n}: {new_firms_str}",
            ha='center', fontsize=14, style='italic'
        )

    plt.tight_layout(rect=[0, 0.05, 1, 1])

    # Save
    save_path = output_dir / f"Figure4_TopMarkupFirms_{year1}_vs_{year2}_{method}.pdf"
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
    logger.info(f"Saved: {save_path}")

    # Also save PNG
    save_path_png = output_dir / f"Figure4_TopMarkupFirms_{year1}_vs_{year2}_{method}.png"
    fig.savefig(save_path_png, dpi=150, bbox_inches="tight")

    # Save data
    df_year1["year"] = year1
    df_year2["year"] = year2
    combined = pd.concat([df_year1, df_year2])
    combined.to_csv(output_dir / f"Figure4_data_{year1}_{year2}_{method}.csv", index=False)

    return fig


def figure5_top_firms_annual(
    cache: PipelineCache,
    method: str = "wooldridge_iv",
    output_dir: Path = Path("Output/report"),
    year_start: int = 1980,
    year_end: int = 2016,
    top_n: int = 10,
    min_weight: float = 0.001,
) -> plt.Figure:
    """
    Figure 5: Markup trajectories of top firms over time (line graph).

    Selects firms that appear most frequently in the top-N markup ranking
    (filtered by minimum market share) across all years, then plots each
    firm's markup as a line over time. Firm names are labelled at the
    right end of each line.
    """
    logger.info("=" * 60)
    logger.info(f"Figure 5: Top Markup Firms Line Graph ({year_start}-{year_end})")
    logger.info("=" * 60)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get cached results (use full sample)
    full_data = cache.get_full_sample()
    markups = full_data["markups"][method]
    panel_data = full_data["panel_data"]

    # Merge markups with panel data
    df = markups.merge(
        panel_data[["gvkey", "year", "sale_D", "conm"]],
        on=["gvkey", "year"],
        how="left",
    )
    df = df[df["markup"].notna() & (df["markup"] > 0) & (df["markup"] < 50)]
    df["weight"] = df.groupby("year")["sale_D"].transform(lambda x: x / x.sum())

    # Filter to year range and minimum weight
    df = df[(df["year"] >= year_start) & (df["year"] <= year_end)]
    df = df[df["weight"] >= min_weight]

    if df.empty:
        logger.warning("No data in range")
        return plt.figure()

    # For each year, flag which firms are in the top N
    df["rank"] = df.groupby("year")["markup"].rank(ascending=False, method="first")
    df["is_top"] = df["rank"] <= top_n

    # Pick a canonical company name per gvkey (most recent)
    name_map = (
        df.sort_values("year")
        .drop_duplicates(subset="gvkey", keep="last")
        .set_index("gvkey")["conm"]
    )

    # Count how many years each firm appears in the top N
    top_counts = (
        df[df["is_top"]]
        .groupby("gvkey")
        .size()
        .sort_values(ascending=False)
    )

    # Select firms: those that appear in top N most frequently
    selected_gvkeys = top_counts.head(top_n).index.tolist()
    logger.info(f"Selected {len(selected_gvkeys)} firms appearing most in top {top_n}")

    for gvkey in selected_gvkeys:
        name = name_map.get(gvkey, gvkey)
        count = top_counts[gvkey]
        logger.info(f"  {str(name)[:30]:30s}  top-{top_n} in {count} years")

    # Build line data: one series per firm
    plot_df = df[df["gvkey"].isin(selected_gvkeys)].copy()
    plot_df["name"] = plot_df["gvkey"].map(name_map)

    # Plot
    setup_plot_style()
    fig, ax = plt.subplots(figsize=(16, 10))

    # Use a qualitative colormap with enough distinct colours
    cmap = plt.cm.get_cmap("tab20", len(selected_gvkeys))

    for i, gvkey in enumerate(selected_gvkeys):
        firm = plot_df[plot_df["gvkey"] == gvkey].sort_values("year")
        name = name_map.get(gvkey, str(gvkey))
        short_name = name[:22] if pd.notna(name) else str(gvkey)

        ax.plot(
            firm["year"], firm["markup"],
            color=cmap(i), linewidth=2, alpha=0.85,
            marker="o", markersize=3,
        )
        # Label at the right end of each line
        last = firm.iloc[-1]
        ax.text(
            last["year"] + 0.3, last["markup"], short_name,
            fontsize=9, va="center", color=cmap(i), fontweight="bold",
        )

    ax.axhline(1, color="grey", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_xlabel("Year")
    ax.set_ylabel("Markup")
    ax.set_title(
        f"Markup Trajectories of Top {top_n} Firms "
        f"({method.replace('_', ' ').title()}, {year_start}-{year_end})",
    )
    ax.set_xlim(year_start - 0.5, year_end + 5)  # extra room for labels

    fig.tight_layout()

    # Save
    save_path = output_dir / f"Figure5_TopFirms_Annual_{year_start}_{year_end}_{method}.pdf"
    fig.savefig(save_path, dpi=200, bbox_inches="tight")
    logger.info(f"Saved: {save_path}")

    save_path_png = output_dir / f"Figure5_TopFirms_Annual_{year_start}_{year_end}_{method}.png"
    fig.savefig(save_path_png, dpi=150, bbox_inches="tight")

    # Save data
    all_tops = []
    for year in sorted(df["year"].unique()):
        ydf = df[df["year"] == year]
        top = ydf.nlargest(top_n, "markup")[["conm", "gvkey", "year", "markup", "weight", "sale_D"]]
        top["rank"] = range(1, len(top) + 1)
        all_tops.append(top)
    if all_tops:
        pd.concat(all_tops).to_csv(
            output_dir / f"Figure5_data_{year_start}_{year_end}_{method}.csv", index=False
        )

    return fig


def main():
    parser = argparse.ArgumentParser(description="Generate report figures for markup analysis")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"), help="Path to config.yaml")
    parser.add_argument("--method", type=str, default="wooldridge_iv",
                        choices=["wooldridge_iv", "cost_share", "acf"],
                        help="Estimation method to use")
    parser.add_argument("--output-dir", type=Path, default=Path("Output/report"), help="Output directory")
    parser.add_argument("--figures", type=str, default="1,2,3,4", help="Comma-separated list of figures to generate (1,2,3,4,5)")
    parser.add_argument("--base-year", type=int, default=1980, help="Base year for Figure 3")
    parser.add_argument("--end-year", type=int, default=2016, help="End year for Figure 3")
    parser.add_argument("--fig4-year1", type=int, default=2008, help="First year for Figure 4")
    parser.add_argument("--fig4-year2", type=int, default=2020, help="Second year for Figure 4")
    parser.add_argument("--fig5-start", type=int, default=1980, help="Start year for Figure 5 annual panels")
    parser.add_argument("--fig5-end", type=int, default=2016, help="End year for Figure 5 annual panels")
    parser.add_argument("--fig5-topn", type=int, default=10, help="Number of top firms per year in Figure 5")
    args = parser.parse_args()

    figures_to_generate = [int(x.strip()) for x in args.figures.split(",")]

    logger.info("=" * 60)
    logger.info("Report Figure Generation")
    logger.info("=" * 60)
    logger.info(f"Config: {args.config}")
    logger.info(f"Method: {args.method}")
    logger.info(f"Output: {args.output_dir}")
    logger.info(f"Figures: {figures_to_generate}")

    # Create pipeline cache to avoid redundant computation
    cache = PipelineCache(args.config, args.method)

    if 1 in figures_to_generate:
        logger.info("\n" + "=" * 60)
        fig1 = figure1_full_vs_deu_sample(cache, args.method, args.output_dir)
        plt.close(fig1)

    if 2 in figures_to_generate:
        logger.info("\n" + "=" * 60)
        fig2 = figure2_revenue_vs_cost_weighted(cache, args.method, args.output_dir)
        plt.close(fig2)

    if 3 in figures_to_generate:
        logger.info("\n" + "=" * 60)
        fig3 = figure3_firm_contribution_ranking(
            cache, args.method, args.output_dir,
            base_year=args.base_year, end_year=args.end_year,
        )
        plt.close(fig3)

    if 4 in figures_to_generate:
        logger.info("\n" + "=" * 60)
        fig4 = figure4_top_markup_firms(
            cache, args.method, args.output_dir,
            year1=args.fig4_year1, year2=args.fig4_year2,
        )
        plt.close(fig4)

    if 5 in figures_to_generate:
        logger.info("\n" + "=" * 60)
        fig5 = figure5_top_firms_annual(
            cache, args.method, args.output_dir,
            year_start=args.fig5_start, year_end=args.fig5_end,
            top_n=args.fig5_topn,
        )
        plt.close(fig5)

    logger.info("\n" + "=" * 60)
    logger.info("All figures generated successfully!")
    logger.info(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()
