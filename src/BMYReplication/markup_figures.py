"""
Python translation of ``Markup_Figures.do`` using matplotlib and pandas.

Generates:
- figure1.eps / figure2.eps / figure_altWeights.eps
- figure1_drop3254.eps / figure_man32.eps / figure_man.eps
- figureDEU3a.eps / figureDEU3b.eps / figureDEU4.eps
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde

from .utils import INTERMEDIATE_DIR, OUTPUT_FIGURES_DIR, ensure_directories, read_dta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


def _line_plot(years: Iterable[int], series: List[Tuple[str, pd.Series, dict]], outfile: Path, ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    for label, values, style in series:
        ax.plot(years, values, label=label, **style)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("")
    ax.grid(alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outfile)
    LOGGER.info("Saved %s", outfile)


def figure1() -> None:
    df = read_dta(INTERMEDIATE_DIR / "markup_DEU.dta").merge(
        read_dta(INTERMEDIATE_DIR / "markup_full.dta"), on="year", how="left"
    )
    years = df["year"]
    series = [
        ("DEU Sample", df["MARKUP10_AGG_DEU"], {"color": "red", "linewidth": 2.5, "marker": "o"}),
        ("Full Sample", df["MARKUP10_AGG_full"], {"color": "green", "linewidth": 2.0, "marker": "s", "linestyle": "-"}),
        ("Full Sample, No F&I", df["MARKUP10_AGG_full_no52"], {"color": "black", "linewidth": 2.5, "marker": "v", "linestyle": "-."}),
    ]
    _line_plot(years, series, OUTPUT_FIGURES_DIR / "figure1.eps", "Sales Weighted Markup")


def figure2() -> None:
    df = read_dta(INTERMEDIATE_DIR / "markup_DEU.dta")
    df = df.merge(read_dta(INTERMEDIATE_DIR / "markup_full_intExp.dta"), on="year", how="left")
    df = df.merge(read_dta(INTERMEDIATE_DIR / "markup_full.dta"), on="year", how="left", suffixes=("", "_full"))
    years = df["year"]
    series = [
        ("DEU Sample", df["MARKUP10_AGG_DEU"], {"color": "red", "linewidth": 2.5, "marker": "o"}),
        ("Full Sample, Interest Expense in COGS", df["MARKUP10_AGG_full_intExp"], {"color": "green", "linewidth": 2.0, "marker": "s", "linestyle": "-"}),
        ("Full Sample, No F&I", df["MARKUP10_AGG_full_no52"], {"color": "black", "linewidth": 2.5, "marker": "v", "linestyle": "-."}),
    ]
    _line_plot(years, series, OUTPUT_FIGURES_DIR / "figure2.eps", "Sales Weighted Markup")


def figure_alt_weights() -> None:
    df = read_dta(INTERMEDIATE_DIR / "markup_DEU.dta").merge(
        read_dta(INTERMEDIATE_DIR / "markup_full.dta"), on="year", how="left"
    )
    years = df["year"]
    series = [
        ("DEU Sample, Baseline Sales Weighted", df["MARKUP10_AGG_DEU"], {"color": "red", "linewidth": 2.5}),
        ("DEU Sample, COGS Weighted", df["MARKUP10_AGGCOGS_DEU"], {"color": "purple", "linewidth": 2.5, "linestyle": "--"}),
        ("Full Sample, COGS Weighted", df["MARKUP10_AGGCOGS_full"], {"color": "green", "linewidth": 2.0, "linestyle": "-."}),
        ("Full Sample, COGS Weighted, No F&I", df["MARKUP10_AGGCOGS_full_no52"], {"color": "black", "linewidth": 2.5, "linestyle": ":"}),
    ]
    _line_plot(years, series, OUTPUT_FIGURES_DIR / "figure_altWeights.eps", "Sales Weighted Markup")


def figure_drop3254() -> None:
    df = read_dta(INTERMEDIATE_DIR / "markup_DEU.dta")
    df = df.merge(read_dta(INTERMEDIATE_DIR / "markup_full.dta"), on="year", how="left")
    df = df.merge(read_dta(INTERMEDIATE_DIR / "markup_full_no3254.dta"), on="year", how="left")
    years = df["year"]
    series = [
        ("DEU Sample", df["MARKUP10_AGG_DEU"], {"color": "red", "linewidth": 2.5}),
        ("Full Sample, No F&I, No 3254", df["MARKUP10_AGG_full_no52_no3254"], {"color": "green", "linewidth": 2.5, "linestyle": "--"}),
        ("Full Sample, No F&I", df["MARKUP10_AGG_full_no52"], {"color": "black", "linewidth": 2.5, "linestyle": "-."}),
    ]
    _line_plot(years, series, OUTPUT_FIGURES_DIR / "figure1_drop3254.eps", "Sales Weighted Markup")


def figure_man32() -> None:
    df = read_dta(INTERMEDIATE_DIR / "markup_DEU.dta").merge(read_dta(INTERMEDIATE_DIR / "markup_full.dta"), on="year", how="left")
    census = read_dta(INTERMEDIATE_DIR / "census.dta")
    df = df.merge(census[["year", "census32"]], on="year", how="left")
    years = df["year"]
    series = [
        ("DEU Sample, Sector 32", df["MARKUP10_AGG_DEU_man32"], {"color": "red", "linewidth": 2.5}),
        ("DEU Reported Census Sector 32", df["census32"], {"color": "green", "linewidth": 2.0, "linestyle": "--"}),
        ("Full Sample, Sector 32", df["MARKUP10_AGG_full_man32"], {"color": "black", "linewidth": 2.5, "linestyle": "-."}),
    ]
    _line_plot(years, series, OUTPUT_FIGURES_DIR / "figure_man32.eps", "Sales Weighted Markup")


def figure_manufacturing() -> None:
    df = read_dta(INTERMEDIATE_DIR / "markup_DEU.dta").merge(read_dta(INTERMEDIATE_DIR / "markup_full.dta"), on="year", how="left")
    census = read_dta(INTERMEDIATE_DIR / "census.dta")
    df = df.merge(census[["year", "censusman"]], on="year", how="left")
    df = df.copy()
    def _normalize(series: pd.Series) -> pd.Series:
        base = series.loc[df["year"] == 1980].mean()
        return series / base if base else series
    df["DEUnorm"] = _normalize(df["MARKUP10_AGG_DEU_man"])
    df["fullnorm"] = _normalize(df["MARKUP10_AGG_full_man"])
    df["censusnorm"] = _normalize(df["censusman"])

    years = df["year"]
    series = [
        ("DEU Sample, Manufacturing", df["DEUnorm"], {"color": "red", "linewidth": 2.5}),
        ("Census, Manufacturing", df["censusnorm"], {"color": "green", "linewidth": 2.0, "linestyle": "--"}),
        ("Full Sample, Manufacturing", df["fullnorm"], {"color": "black", "linewidth": 2.5, "linestyle": "-."}),
    ]
    _line_plot(years, series, OUTPUT_FIGURES_DIR / "figure_man.eps", "Normalized Sales Weighted Markup (1980=1)")


def _load_full_sample_for_distribution() -> pd.DataFrame:
    df = read_dta(INTERMEDIATE_DIR / "data_main_upd_trim_1.dta")
    df["id"] = df["gvkey"]
    df["s_g2"] = df["xsga"] / df["sale"]
    p1 = df.groupby("year")["s_g2"].transform(lambda x: x.quantile(0.01))
    p99 = df.groupby("year")["s_g2"].transform(lambda x: x.quantile(0.99))
    df = df[(df["s_g2"] >= p1) | df["s_g2"].isna()]
    df = df[(df["s_g2"] <= p99) | df["s_g2"].isna()]
    df = df.drop(columns=["s_g2"])
    theta = read_dta(INTERMEDIATE_DIR / "theta_W_s_window_fullSample.dta")
    df = df.merge(theta, on=["ind2d", "year"], how="left")
    df = df[df["ind2d"] != 52]
    df["mu_10"] = df["theta_WI1_ct"] * (df["sale_D"] / df["cogs_D"])
    df["mu_11"] = df["theta_WI2_ct"] * (df["sale_D"] / df["cogs_D"])
    df["TOTSALES"] = df.groupby("year")["sale_D"].transform("sum")
    df["share_firm_agg"] = df["sale_D"] / df["TOTSALES"]
    df["TOTCOST"] = df.groupby("year")[["cogs_D", "xsga_D"]].transform("sum").sum(axis=1)
    df["share_firm_cost"] = (df["cogs_D"] + df["xsga_D"]) / df["TOTCOST"]
    return df


def figure_distribution_and_decomposition() -> None:
    df = _load_full_sample_for_distribution()
    years = sorted(df["year"].unique())

    percentiles = df.groupby("year")["mu_10"].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).unstack()
    avg_markup = df.groupby("year").apply(lambda g: np.sum(g["share_firm_agg"] * g["mu_10"]))

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(years, avg_markup.values, label="Average", color="black", linewidth=2.5)
    labels = {0.9: "P90", 0.75: "P75", 0.5: "P50", 0.25: "P25", 0.1: "P10"}
    styles = {0.9: "-", 0.75: "--", 0.5: "-.", 0.25: ":", 0.1: (0, (3, 5, 1, 5))}
    for q, label in labels.items():
        ax.plot(percentiles.index, percentiles[q].values, label=label, linestyle=styles[q], linewidth=1.8, color="red")
    ax.set_xlabel("")
    ax.set_ylabel("Markup")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_FIGURES_DIR / "figureDEU3a.eps")
    LOGGER.info("Saved %s", OUTPUT_FIGURES_DIR / "figureDEU3a.eps")

    # Kernel densities for 2016 vs 1980
    fig, ax = plt.subplots(figsize=(6, 4))
    for year, style in ((2016, {"color": "red", "linestyle": "-"}), (1980, {"color": "red", "linestyle": "--"})):
        sample = df.loc[(df["year"] == year) & (df["mu_10"].between(0.5, 3.5)), "mu_10"].dropna()
        if sample.empty:
            continue
        kde = gaussian_kde(sample)
        xs = np.linspace(sample.min(), sample.max(), 200)
        ax.plot(xs, kde(xs), label=str(year), **style, linewidth=2.0)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_FIGURES_DIR / "figureDEU3b.eps")
    LOGGER.info("Saved %s", OUTPUT_FIGURES_DIR / "figureDEU3b.eps")

    # Simple decomposition approximation
    work = df[(df["year"] > 1979) & (df["year"] <= 2016) & (df["ind2d"].between(9, 99))].copy()
    work = work.sort_values(["id", "year"])
    work["ts"] = work.groupby("year")["sale_D"].transform("sum")
    work["msagg"] = work["sale_D"] / work["ts"]
    mu_agg_by_year = work.groupby("year").apply(lambda g: np.sum(g["msagg"] * g["mu_10"]))
    work = work.join(mu_agg_by_year.rename("MU_agg"), on="year")
    work["dmu"] = work.groupby("id")["mu_10"].diff()
    work["dms"] = work.groupby("id")["msagg"].diff()
    work["Lmu"] = work.groupby("id")["mu_10"].shift(1)
    work["Lms"] = work.groupby("id")["msagg"].shift(1)

    def _year_decomp(group: pd.DataFrame) -> pd.Series:
        return pd.Series(
            {
                "DMU_agg": group["MU_agg"].iloc[0],
                "Daggmu": np.nansum(group["dmu"] * group["Lms"]),
                "Daggms": np.nansum(group["dms"] * group["Lmu"]),
                "Cross_agg": np.nansum(group["dms"] * group["dmu"]),
            }
        )

    agg = work.groupby("year").apply(_year_decomp)
    agg["net_entry"] = agg["DMU_agg"].diff().fillna(0) - agg["Daggmu"] - agg["Daggms"] - agg["Cross_agg"]
    agg["REALL"] = agg["net_entry"] + agg["Daggms"] + agg["Cross_agg"]
    agg = agg.dropna()

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(agg.index, agg["DMU_agg"], label="Markup (benchmark)", color="black", linestyle="-.", linewidth=2.5)
    ax.plot(agg.index, agg["Daggmu"].cumsum(), label="Within", color="red", linestyle="--", linewidth=2.0)
    ax.plot(agg.index, (agg["Daggms"] + agg["Cross_agg"]).cumsum(), label="Reallocation", color="blue", linestyle=":", linewidth=2.0)
    ax.plot(agg.index, agg["net_entry"].cumsum(), label="Net Entry", color="green", linestyle="-", linewidth=2.0)
    ax.set_ylabel("")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_FIGURES_DIR / "figureDEU4.eps")
    LOGGER.info("Saved %s", OUTPUT_FIGURES_DIR / "figureDEU4.eps")


def main() -> None:
    ensure_directories()
    figure1()
    figure2()
    figure_alt_weights()
    figure_drop3254()
    figure_man32()
    figure_manufacturing()
    figure_distribution_and_decomposition()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replicate Markup_Figures.do in Python.")
    main()
