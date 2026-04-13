"""Pymkp Markup Dashboard — Aggregate quarterly markup trends."""

import pandas as pd
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Pymkp Markup Tracker", layout="wide")

DATA_DIR = Path(__file__).parent / "data" / "dashboard"


@st.cache_data
def load_quarterly():
    path = DATA_DIR / "agg_markup_quarterly.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df = df.sort_values("quarter")
    # Parse year from quarter string for filtering
    df["year"] = df["quarter"].str[:4].astype(int)
    return df


@st.cache_data
def load_annual():
    path = DATA_DIR / "agg_markup_annual.csv"
    if not path.exists():
        return None
    return pd.read_csv(path).sort_values("year")


# Header
st.title("Aggregate Markup Trend")
st.caption(
    "Firm-level markups estimated using [DLEU (2020)](https://doi.org/10.1093/qje/qjz041) "
    "methodology — Wooldridge IV elasticities applied to Compustat data. "
    "Install: `pip install Pymkp`"
)

quarterly = load_quarterly()
annual = load_annual()

if quarterly is None and annual is None:
    st.error(
        "No dashboard data found. Run locally first:\n\n"
        "```\npython scripts/build_dashboard_data.py\n```"
    )
    st.stop()

# Controls
col1, col2 = st.columns([1, 3])

with col1:
    freq = st.radio("Frequency", ["Quarterly", "Annual"], index=0)
    if freq == "Quarterly" and quarterly is not None:
        df = quarterly
        time_col = "quarter"
    elif annual is not None:
        df = annual
        time_col = "year"
    else:
        df = quarterly if quarterly is not None else annual
        time_col = "quarter" if quarterly is not None else "year"

    year_min = int(df["year"].min())
    year_max = int(df["year"].max())
    yr_range = st.slider("Year range", year_min, year_max, (year_min, year_max))

# Filter
mask = (df["year"] >= yr_range[0]) & (df["year"] <= yr_range[1])
filtered = df[mask]

with col2:
    # Line chart
    chart_data = filtered.set_index(time_col)[["agg_markup"]]
    chart_data.columns = ["Aggregate Markup"]
    st.line_chart(chart_data, height=500)

# Stats
st.markdown("---")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest", f"{filtered['agg_markup'].iloc[-1]:.3f}")
c2.metric("Mean", f"{filtered['agg_markup'].mean():.3f}")
c3.metric("Min", f"{filtered['agg_markup'].min():.3f}")
c4.metric("Max", f"{filtered['agg_markup'].max():.3f}")

# Data table
with st.expander("Show data"):
    st.dataframe(filtered[[time_col, "agg_markup"]].reset_index(drop=True), use_container_width=True)

# Footer
st.markdown("---")
st.markdown(
    "**Source:** Compustat via WRDS | "
    "**Method:** Wooldridge IV ([DLEU 2020](https://doi.org/10.1093/qje/qjz041)) | "
    "**Package:** [Pymkp](https://pypi.org/project/Pymkp/)"
)
