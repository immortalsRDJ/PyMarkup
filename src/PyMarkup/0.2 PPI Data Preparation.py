#!/usr/bin/env python3
"""
--------------------------------------------------
Converts BLS 'pc.data.0.Current.txt' into quarterly
and annual PPI datasets.

Rules:
    - Quarterly data: use quarter-end months (M03, M06, M09, M12)
    - Annual data: use December (M12) only

Inputs:
    {data_dir}/PPI/pc.data.0.Current.txt
    {data_dir}/PPI/PPI_quarterly_old.csv
    {data_dir}/PPI/PPI_annual_old.csv

Outputs (updated/merged):
    {data_dir}/PPI/PPI_quarterly.csv
    {data_dir}/PPI/PPI_annual.csv
--------------------------------------------------
"""

import os
import pandas as pd
from path_plot_config import data_dir


def drop_index_col(df: pd.DataFrame) -> pd.DataFrame:
    """Drop the first column if it is an unnamed index."""
    if df.columns[0].lower().startswith("unnamed"):
        df = df.iloc[:, 1:]
    return df


def process_ppi_data(input_path: str, output_dir: str) -> None:
    """Convert raw BLS PPI data into quarterly and annual CSVs, merging with old datasets."""

    # Read space-delimited text file
    df = pd.read_csv(
        input_path,
        delim_whitespace=True,
        dtype=str,
        engine="python"
    )

    # Keep relevant columns
    df = df[["series_id", "year", "period", "value"]]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["year"] = df["year"].astype(int)

    # Extract NAICS code (first 6 digits after PCU, removing '-')
    df["naics_code"] = df["series_id"].str.slice(start=3, stop=9).str.replace("-", "", regex=False)
    df = df[df["naics_code"].str.match(r"^\d{2,6}$")]

    # Keep only relevant months for quarterly/annual data
    valid_months = ["M03", "M06", "M09", "M12"]
    df = df[df["period"].isin(valid_months)]

    # Map months to quarters
    month_to_q = {"M03": 1, "M06": 2, "M09": 3, "M12": 4}
    df["quarter"] = df["period"].map(month_to_q)
    df["date"] = df["year"].astype(str) + "Q" + df["quarter"].astype(str)

    # ----------------------------
    # Quarterly data (quarter-end values)
    # ----------------------------
    df_q = (
        df[["year", "quarter", "value", "naics_code", "date"]]
        .rename(columns={"value": "PPI"})
        .sort_values(["naics_code", "year", "quarter"])
        .reset_index(drop=True)
    )

    # ----------------------------
    # Annual data (use M12 only)
    # ----------------------------
    df_a = (
        df[df["period"] == "M12"][["year", "naics_code", "value"]]
        .rename(columns={"value": "PPI"})
        .sort_values(["naics_code", "year"])
        .reset_index(drop=True)
    )

    # ----------------------------
    # Merge with old datasets (if available)
    # ----------------------------
    path_q_old = os.path.join(output_dir, "PPI_quarterly_old.csv")
    path_a_old = os.path.join(output_dir, "PPI_annual_old.csv")
    path_q_new = os.path.join(output_dir, "PPI_quarterly.csv")
    path_a_new = os.path.join(output_dir, "PPI_annual.csv")

    if os.path.exists(path_q_old):
        old_q = pd.read_csv(path_q_old)
        old_q = drop_index_col(old_q)
        df_q = pd.concat([old_q, df_q], ignore_index=True)
        df_q = (
            df_q.sort_values(["naics_code", "year", "quarter"])
            .drop_duplicates(["naics_code", "year", "quarter"], keep="last")
            .reset_index(drop=True)
        )

    if os.path.exists(path_a_old):
        old_a = pd.read_csv(path_a_old)
        old_a = drop_index_col(old_a)
        df_a = pd.concat([old_a, df_a], ignore_index=True)
        df_a = (
            df_a.sort_values(["naics_code", "year"])
            .drop_duplicates(["naics_code", "year"], keep="last")
            .reset_index(drop=True)
        )

    # ----------------------------
    # Save updated outputs
    # ----------------------------
    os.makedirs(output_dir, exist_ok=True)
    df_q.to_csv(path_q_new, index=False)
    df_a.to_csv(path_a_new, index=False)

    print(f"Quarterly data saved to: {path_q_new}")
    print(f"Annual data saved to: {path_a_new}")
    print(f"Coverage: {df_a['year'].min()}–{df_a['year'].max()}")
    print(f"Industries processed: {df_a['naics_code'].nunique()}")


if __name__ == "__main__":
    input_path = os.path.join(data_dir, "PPI", "pc.data.0.Current.txt")
    output_dir = os.path.join(data_dir, "PPI")
    process_ppi_data(input_path, output_dir)