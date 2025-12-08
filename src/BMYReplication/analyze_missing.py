"""
Python translation of ``Analyze_Missing.do``.

Generates the missing-SG&A figures/tables and runs fixed-effects regressions
mirroring the Stata output. Assumes ``Create_Data`` has been run without
including interest expense in COGS (uses ``data_main_upd_trim_1.dta``).
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

from .utils import INTERMEDIATE_DIR, OUTPUT_FIGURES_DIR, TEMP_DIR, ensure_directories, read_dta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


def load_data() -> pd.DataFrame:
    path = INTERMEDIATE_DIR / "data_main_upd_trim_1.dta"
    if not path.exists():
        raise FileNotFoundError(f"Run create_data.py first. Missing {path}")
    return read_dta(path)


def add_naics_description() -> pd.DataFrame:
    """Load NAICS descriptions and add the 99 'Unclassified' row."""
    excel_path = TEMP_DIR.parent / "rawData" / "NAICS_2D_Description.xlsx"
    df = pd.read_excel(excel_path, sheet_name="Sheet1")
    df = df.rename(columns={"sector_definition": "ind2d_definition"})
    df = pd.concat(
        [df, pd.DataFrame({"ind2d": [99], "ind2d_definition": ["Unclassified"]})],
        ignore_index=True,
    )
    return df.sort_values("ind2d")


def prep_base(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sga_missing"] = df["xsga_D"].isna()
    df["ln_sale_D"] = np.log(df["sale_D"])
    df["ln_cogs_D"] = np.log(df["cogs_D"])
    df["sale_cogs_ratio"] = df["s_g"]
    return df


def plot_missing_over_time(df: pd.DataFrame) -> None:
    agg = (
        df.assign(obs_dummy=1, missing_sales=lambda d: d["sale_D"].where(d["sga_missing"]))
        .groupby("year")
        .agg(total_obs=("obs_dummy", "sum"), missing_obs=("sga_missing", "sum"), total_sales=("sale_D", "sum"), missing_sales=("missing_sales", "sum"))
        .reset_index()
    )
    agg["frac_missing_obs"] = agg["missing_obs"] / agg["total_obs"]
    agg["frac_missing_sales"] = agg["missing_sales"] / agg["total_sales"]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(agg["year"], agg["frac_missing_obs"], label="Observations with Missing SG&A", color="green")
    ax.plot(agg["year"], agg["frac_missing_sales"], label="Sales with Missing SG&A", color="orange", linestyle="--")
    ax.set_ylabel("Fraction")
    ax.set_ylim(0, 0.4)
    ax.grid(axis="x", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out_path = OUTPUT_FIGURES_DIR / "fig_frac_sga_obs_sale_by_year.pdf"
    fig.savefig(out_path)
    LOGGER.info("Saved %s", out_path)


def write_industry_table(df: pd.DataFrame, naics: pd.DataFrame) -> None:
    merged = df.merge(naics, on="ind2d", how="left")
    collapsed = (
        merged.assign(missing_sales=lambda d: d["sale_D"].where(d["sga_missing"]), total_sales=lambda d: d["sale_D"])
        .groupby(["ind2d", "ind2d_definition"])
        .agg(total_obs=("sale_D", "count"), missing_obs=("sga_missing", "sum"), total_sales=("total_sales", "sum"), missing_sales=("missing_sales", "sum"))
        .reset_index()
    )
    collapsed["frac_obs_missing"] = collapsed["missing_obs"] / collapsed["total_obs"] * 100
    collapsed["frac_sales_missing"] = collapsed["missing_sales"] / collapsed["total_sales"] * 100
    full_total_sales = collapsed["total_sales"].sum()
    collapsed["share_all_sales"] = collapsed["total_sales"] / full_total_sales * 100

    collapsed["defn_clean"] = (
        collapsed["ind2d_definition"]
        .str.replace("&", r"\&", regex=False)
        .str.replace("_", r"\_", regex=False)
    )

    outfile = OUTPUT_FIGURES_DIR / "tab_frac_sga_obs_sale_by_ind2d.tex"
    with outfile.open("w") as fh:
        fh.write(r"\begin{table}[t]" + "\n")
        fh.write(r"\centering \footnotesize" + "\n")
        fh.write(r"\caption{Summary of Missing SG\&A Information by 2-Digit NAICS Code}" + "\n")
        fh.write(r"\begin{tabular}{llccc}" + "\n")
        fh.write(r"\hline \hline" + "\n")
        fh.write(r"&& Share of All & Observations & Sales \rule[0mm]{0mm}{4mm} \\" + "\n")
        fh.write(r"NAICS Code & Definition & Sales (\%) & Missing (\%) & Missing (\%) \\" + "\n")
        fh.write(r"\hline" + "\n")

        for _, row in collapsed.sort_values("ind2d").iterrows():
            ind = int(row["ind2d"])
            defn = row["defn_clean"]
            f1, f2, f3 = (f"{row['share_all_sales']:.2f}", f"{row['frac_obs_missing']:.2f}", f"{row['frac_sales_missing']:.2f}")
            if ind == 56:
                fh.write(f"{ind} & Administrative and Support and Waste & {f1} & {f2} & {f3} \\\n")
                fh.write(r"& $\quad$ Management and Remediation Services \\" + "\n")
            elif ind == 11:
                fh.write(f"{ind} & {defn} & {f1} & {f2} & {f3} \\\n")
            else:
                fh.write(f"{ind} & {defn} & {f1} & {f2} & {f3} \\\n")

        fh.write(r"\hline" + "\n")
        fh.write(r"\end{tabular}" + "\n")
        fh.write(r"\end{table}" + "\n")
    LOGGER.info("Saved %s", outfile)


def _run_panel_reg(
    df: pd.DataFrame,
    dep: str,
    include_firm_fe: bool,
    add_trend: bool = False,
) -> Dict[str, float]:
    """Run the fixed-effects regressions using linearmodels' PanelOLS."""
    work = df.dropna(subset=[dep, "sga_missing"]).copy()
    work = work.set_index(["gvkey", "year"])

    exog_cols = ["sga_missing"]
    if add_trend:
        work["year_demeaned"] = work.index.get_level_values("year") - work.index.get_level_values("year").mean()
        work["sga_missing_trend"] = work["sga_missing"] * work["year_demeaned"]
        exog_cols.append("sga_missing_trend")

    exog = work[exog_cols]
    exog = exog.assign(const=1.0)

    model = PanelOLS(
        work[dep],
        exog,
        time_effects=True,
        entity_effects=include_firm_fe,
        other_effects=work["ind2d"],
    )
    res = model.fit(cov_type="clustered", cluster_entity=True)
    result = {
        "beta": float(res.params["sga_missing"]),
        "se": float(res.std_errors["sga_missing"]),
        "r2": float(res.rsquared),
        "n": int(res.nobs),
    }
    if add_trend:
        result["trend_beta"] = float(res.params.get("sga_missing_trend", np.nan))
        result["trend_se"] = float(res.std_errors.get("sga_missing_trend", np.nan))
    return result


def run_regressions(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    results: Dict[str, Dict[str, float]] = {}
    specs = [
        ("ln_sale_D", False),
        ("ln_sale_D", True),
        ("ln_cogs_D", False),
        ("ln_cogs_D", True),
        ("sale_cogs_ratio", False),
        ("sale_cogs_ratio", True),
    ]
    for idx, (dep, firm_fe) in enumerate(specs, start=1):
        results[f"m{idx}"] = _run_panel_reg(df, dep, include_firm_fe=firm_fe)
    return results


def run_trend_regressions(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    results: Dict[str, Dict[str, float]] = {}
    specs = [
        ("ln_sale_D", False),
        ("ln_sale_D", True),
        ("ln_cogs_D", False),
        ("ln_cogs_D", True),
        ("sale_cogs_ratio", False),
        ("sale_cogs_ratio", True),
    ]
    for idx, (dep, firm_fe) in enumerate(specs, start=1):
        results[f"m{idx}"] = _run_panel_reg(df, dep, include_firm_fe=firm_fe, add_trend=True)
    return results


def export_reg_tables(results: Dict[str, Dict[str, float]], outfile: Path, include_trend: bool = False) -> None:
    with outfile.open("w") as fh:
        fh.write(r"\begin{table}[t]" + "\n")
        fh.write(r"\centering \footnotesize" + "\n")
        caption = "Interaction of Missing SG&A with Time Trend" if include_trend else "Relationships between Missing SG&A and Sales, COGS, and Sales/COGS"
        fh.write(rf"\caption{{{caption}}}" + "\n")
        fh.write(r"\begin{tabular}{lcccccc}" + "\n")
        fh.write(r"\hline \hline" + "\n")
        fh.write(r" & Sales & Sales & COGS & COGS & Sales/COGS & Sales/COGS\rule[0mm]{0mm}{4mm} \\" + "\n")
        fh.write(r"\hline" + "\n")

    def row_for(key: str, stat: str, paren: bool = False) -> str:
        pieces = []
        for i in range(1, 7):
            val = results[f"m{i}"][stat]
            fmt = f"{val:6.3f}" if stat != "n" else f"{int(val):,}"
            pieces.append(f" ({fmt})" if paren else f" {fmt}")
        return " &".join(pieces)

        fh.write("SG\\&A Missing &" + row_for("m1", "beta") + r" \rule[0mm]{0mm}{4mm} \\" + "\n")
        fh.write(" &" + row_for("m1", "se", paren=True) + r" \\" + "\n")
        if include_trend:
            fh.write("SG\\&A Missing $\\times$ Trend &" + row_for("m1", "trend_beta") + r" \\" + "\n")
            fh.write(" &" + row_for("m1", "trend_se", paren=True) + r" \\" + "\n")

        fh.write(r"\\" + "\n")
        fh.write(r"Year Fixed Effects & yes & yes & yes & yes & yes & yes \\" + "\n")
        fh.write(r"Industry Fixed Effects & yes & yes & yes & yes & yes & yes \\" + "\n")
        fh.write(r"Firm Fixed Effects & no & yes & no & yes & no & yes \\" + "\n")
        fh.write(r"\\" + "\n")
        fh.write("R-squared &" + row_for("m1", "r2") + r" \\" + "\n")
        fh.write(r"\hline" + "\n")
        fh.write(
            r"\multicolumn{7}{p{5.6in}}{\rule[0mm]{0mm}{4mm}\scriptsize{Notes: Standard errors clustered by firm.}}"
            + "\n"
        )
        fh.write(r"\end{tabular}" + "\n")
        fh.write(r"\end{table}" + "\n")
    LOGGER.info("Saved %s", outfile)


def main() -> None:
    ensure_directories()
    naics = add_naics_description()
    base = prep_base(load_data())
    plot_missing_over_time(base)
    write_industry_table(base, naics)

    reg_results = run_regressions(base)
    export_reg_tables(reg_results, OUTPUT_FIGURES_DIR / "reg_unweighted_log_sga_missing.tex")

    trend_results = run_trend_regressions(base)
    export_reg_tables(trend_results, OUTPUT_FIGURES_DIR / "reg_unweighted_log_sga_missing_time_trend_interaction.tex", include_trend=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replicate Analyze_Missing.do in Python.")
    main()
