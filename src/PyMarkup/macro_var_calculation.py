#!/usr/bin/env python3
"""
--------------------------------------------------
Generate updated DLEU-style macro variable table:
    Columns: year | USGDP | usercost

Inputs:
    {data_dir}/DLEU/GDPDEF.csv             (annual GDP deflator, year-end)
    {data_dir}/DLEU/GS10.csv               (annual 10-year Treasury yield, year-end)
    {data_dir}/DLEU/macro_vars_new_old.xlsx (existing file, 1954–2022)

Outputs:
    {data_dir}/DLEU/macro_vars_new.xlsx    (updated, 1954–2024)

Rules:
    - USGDP: rebased to 2009 = 100
    - inflation = Δ(GDPDEF) / GDPDEF(-1)
    - usercost = (GS10/100 - inflation) + 0.11
    - Append only new years (> latest year in old file)
--------------------------------------------------
"""

import os
import pandas as pd
from path_plot_config import data_dir


def generate_and_update_macro_vars(path_gdpdef, path_gs10, old_path, output_path):
    """Generate new macro vars and append to existing old dataset."""

    # ---------- GDPDEF (annual) ----------
    df_p = pd.read_csv(path_gdpdef)
    df_p.columns = df_p.columns.str.lower()
    df_p["observation_date"] = pd.to_datetime(df_p["observation_date"])
    df_p["year"] = df_p["observation_date"].dt.year
    df_p = df_p.sort_values("year").reset_index(drop=True)

    # Inflation (year-over-year)
    df_p["pi"] = df_p["gdpdef"].pct_change()

    # Rebase GDPDEF to 2009 = 100
    base_value = df_p.loc[df_p["year"] == 2009, "gdpdef"].values[0]
    df_p["USGDP"] = df_p["gdpdef"] / base_value * 100

    # ---------- GS10 (annual) ----------
    df_r = pd.read_csv(path_gs10)
    df_r.columns = df_r.columns.str.lower()
    df_r["observation_date"] = pd.to_datetime(df_r["observation_date"])
    df_r["year"] = df_r["observation_date"].dt.year

    # ---------- Merge ----------
    df_new = pd.merge(df_p[["year", "USGDP", "pi"]],
                      df_r[["year", "gs10"]],
                      on="year", how="inner")

    # Compute user cost
    df_new["usercost"] = (df_new["gs10"] / 100 - df_new["pi"]) + 0.11
    df_new = df_new[df_new["year"] >= 1954][["year", "USGDP", "usercost"]].reset_index(drop=True)

    # ---------- Read old file ----------
    df_old = pd.read_excel(old_path)
    df_old.columns = ["year", "USGDP", "usercost"]

    # ---------- Append only new years ----------
    latest_year = df_old["year"].max()
    df_append = df_new[df_new["year"] > latest_year]
    df_updated = pd.concat([df_old, df_append], ignore_index=True).sort_values("year").reset_index(drop=True)

    # ---------- Save ----------
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_updated.to_excel(output_path, index=False)

    print(f"Updated macro vars saved to: {output_path}")
    print(f"Coverage: {df_updated['year'].min()}–{df_updated['year'].max()}")
    print(df_updated.tail())


if __name__ == "__main__":
    path_gdpdef = os.path.join(data_dir, "DLEU", "GDPDEF.csv")
    path_gs10 = os.path.join(data_dir, "DLEU", "GS10.csv")
    old_path = os.path.join(data_dir, "DLEU", "macro_vars_new_old.xlsx")
    output_path = os.path.join(data_dir, "DLEU", "macro_vars_new.xlsx")

    generate_and_update_macro_vars(path_gdpdef, path_gs10, old_path, output_path)