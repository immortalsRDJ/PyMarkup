"""
Pymkp Markup Dashboard — Interactive firm-level markup explorer.

Reads pre-computed firm-level parquet and lets users aggregate on the fly
by estimator method, weighting scheme, industry, and time range.

Usage:
    python dashboard_app.py
    # Opens at http://localhost:8050
"""

from pathlib import Path

import pandas as pd
from dash import Dash, Input, Output, callback, dcc, html
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
NAICS_PATH = Path(__file__).parent / "Input" / "Other" / "NAICS_2D_Description.xlsx"

def load_data():
    # Find the newest parquet file
    parquet_files = sorted(DATA_DIR.glob("firm_markups_*.parquet"))
    if not parquet_files:
        raise FileNotFoundError("No parquet files found in data/. Run: python scripts/build_dashboard_data.py")
    df = pd.read_parquet(parquet_files[-1])  # latest by name (sorted alphabetically = chronologically)
    # Load NAICS descriptions
    if NAICS_PATH.exists():
        naics = pd.read_excel(NAICS_PATH)
        naics_map = dict(zip(naics["ind2d"], naics["sector_definition"]))
    else:
        naics_map = {}
    return df, naics_map

DF, NAICS_MAP = load_data()

# Build industry options
industries_in_data = sorted(DF["ind2d"].dropna().unique().astype(int))
industry_options = [
    {"label": f"{ind} - {NAICS_MAP.get(ind, 'Unknown')}", "value": ind}
    for ind in industries_in_data
]

# Markup measure options
MEASURES = {
    "markup_iv_spec1": "Wooldridge IV - Spec 1 (COGS+K)",
    "markup_iv_spec2": "Wooldridge IV - Spec 2 (COGS+K+SGA)",
    "markup_cs": "Cost Share",
    "markup_acf": "ACF",
}

WEIGHTS = {
    "revenue": "Revenue-weighted mean",
    "cost": "Cost-weighted mean",
    "median": "Median",
    "mean": "Unweighted mean",
}

# ---------------------------------------------------------------------------
# App layout
# ---------------------------------------------------------------------------

app = Dash(__name__)
app.title = "Pymkp Markup Dashboard"

app.layout = html.Div(
    style={"fontFamily": "Segoe UI, Helvetica, Arial, sans-serif", "margin": "0 auto",
           "maxWidth": "1200px", "padding": "20px"},
    children=[
        # Header
        html.H1("Aggregate Markup Trends", style={"marginBottom": "5px"}),
        html.P(
            [html.A("PyPI: pip install Pymkp", href="https://pypi.org/project/Pymkp/",
                     target="_blank", style={"color": "#1f77b4"})],
            style={"color": "#666", "marginBottom": "30px"},
        ),

        # Controls row
        html.Div(
            style={"display": "flex", "gap": "20px", "flexWrap": "wrap", "marginBottom": "20px"},
            children=[
                html.Div([
                    html.Label("Markup Measure", style={"fontWeight": "bold", "fontSize": "14px"}),
                    dcc.Dropdown(
                        id="measure",
                        options=[{"label": v, "value": k} for k, v in MEASURES.items()],
                        value="markup_iv_spec1",
                        clearable=False,
                        style={"width": "250px"},
                    ),
                ]),
                html.Div([
                    html.Label("Aggregation", style={"fontWeight": "bold", "fontSize": "14px"}),
                    dcc.Dropdown(
                        id="weight",
                        options=[{"label": v, "value": k} for k, v in WEIGHTS.items()],
                        value="revenue",
                        clearable=False,
                        style={"width": "250px"},
                    ),
                ]),
                html.Div([
                    html.Label("Industries", style={"fontWeight": "bold", "fontSize": "14px"}),
                    dcc.Dropdown(
                        id="industries",
                        options=industry_options,
                        value=[],
                        multi=True,
                        placeholder="All industries",
                        style={"width": "400px"},
                    ),
                    dcc.Checklist(
                        id="show-individual",
                        options=[{"label": " Show individual industry lines", "value": "show"}],
                        value=["show"],
                        style={"marginTop": "5px", "fontSize": "13px"},
                    ),
                ]),
            ],
        ),

        # Year range slider
        html.Div([
            html.Label("Year Range", style={"fontWeight": "bold", "fontSize": "14px"}),
            dcc.RangeSlider(
                id="year-range",
                min=int(DF["year"].min()),
                max=int(DF["year"].max()),
                value=[1955, int(DF["year"].max())],
                marks={y: str(y) for y in range(1960, int(DF["year"].max()) + 1, 10)},
                step=1,
                tooltip={"placement": "bottom"},
            ),
        ], style={"marginBottom": "20px"}),

        # Chart
        dcc.Graph(id="markup-chart", style={"height": "500px"}),

        # Stats row
        html.Div(id="stats-row", style={
            "display": "flex", "gap": "30px", "marginTop": "10px",
            "padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "8px",
        }),

        # Top/Bottom firms section
        html.Hr(style={"marginTop": "30px"}),
        html.H3("Firm Rankings", style={"marginBottom": "10px"}),
        html.Div(
            style={"display": "flex", "gap": "20px", "marginBottom": "15px", "alignItems": "center"},
            children=[
                html.Div([
                    html.Label("Measure", style={"fontWeight": "bold", "fontSize": "13px"}),
                    dcc.Dropdown(
                        id="table-measure",
                        options=[{"label": v, "value": k} for k, v in MEASURES.items()],
                        value="markup_iv_spec1",
                        clearable=False,
                        style={"width": "250px"},
                    ),
                ]),
                html.Div([
                    html.Label("From", style={"fontWeight": "bold", "fontSize": "13px"}),
                    dcc.Dropdown(
                        id="table-year-start",
                        options=[{"label": str(y), "value": y} for y in range(int(DF["year"].min()), int(DF["year"].max()) + 1)],
                        value=2018,
                        clearable=False,
                        style={"width": "100px"},
                    ),
                ]),
                html.Div([
                    html.Label("To", style={"fontWeight": "bold", "fontSize": "13px"}),
                    dcc.Dropdown(
                        id="table-year-end",
                        options=[{"label": str(y), "value": y} for y in range(int(DF["year"].min()), int(DF["year"].max()) + 1)],
                        value=int(DF["year"].max()),
                        clearable=False,
                        style={"width": "100px"},
                    ),
                ]),
            ],
        ),
        html.Div(
            style={"display": "flex", "gap": "20px", "flexWrap": "wrap"},
            children=[
                html.Div([
                    html.H4(id="top-title", style={"marginBottom": "5px"}),
                    html.Div(id="top-table"),
                ], style={"flex": "1", "minWidth": "300px"}),
                html.Div([
                    html.H4(id="bottom-title", style={"marginBottom": "5px"}),
                    html.Div(id="bottom-table"),
                ], style={"flex": "1", "minWidth": "300px"}),
                html.Div([
                    html.H4(id="contrib-title", style={"marginBottom": "5px"}),
                    dcc.RadioItems(
                        id="contrib-weight",
                        options=[
                            {"label": " Revenue share x markup", "value": "revenue"},
                            {"label": " Cost share x markup", "value": "cost"},
                        ],
                        value="revenue",
                        style={"fontSize": "12px", "color": "#888", "marginBottom": "8px"},
                    ),
                    html.Div(id="contrib-table"),
                ], style={"flex": "1", "minWidth": "300px"}),
            ],
        ),

        # Firm-level markup plot
        html.Hr(style={"marginTop": "30px"}),
        html.H3("Firm-Level Markup", style={"marginBottom": "10px"}),
        html.Div(
            style={"display": "flex", "gap": "20px", "marginBottom": "15px", "alignItems": "center",
                    "flexWrap": "wrap"},
            children=[
                html.Div([
                    html.Label("Measure", style={"fontWeight": "bold", "fontSize": "13px"}),
                    dcc.Dropdown(
                        id="firm-measure",
                        options=[{"label": v, "value": k} for k, v in MEASURES.items()],
                        value="markup_iv_spec1",
                        clearable=False,
                        style={"width": "250px"},
                    ),
                ]),
                html.Div([
                    html.Label("From", style={"fontWeight": "bold", "fontSize": "13px"}),
                    dcc.Dropdown(
                        id="firm-year-start",
                        options=[{"label": str(y), "value": y} for y in range(int(DF["year"].min()), int(DF["year"].max()) + 1)],
                        value=1955,
                        clearable=False,
                        style={"width": "100px"},
                    ),
                ]),
                html.Div([
                    html.Label("To", style={"fontWeight": "bold", "fontSize": "13px"}),
                    dcc.Dropdown(
                        id="firm-year-end",
                        options=[{"label": str(y), "value": y} for y in range(int(DF["year"].min()), int(DF["year"].max()) + 1)],
                        value=int(DF["year"].max()),
                        clearable=False,
                        style={"width": "100px"},
                    ),
                ]),
                html.Div([
                    html.Label("Search firms (multiple)", style={"fontWeight": "bold", "fontSize": "13px"}),
                    dcc.Dropdown(
                        id="firm-search",
                        options=[],
                        value=["6008"],  # Intel Corp
                        multi=True,
                        placeholder="Type firm name...",
                        style={"width": "500px"},
                    ),
                ]),
            ],
        ),
        dcc.Graph(id="firm-chart", style={"height": "400px"}),

        # Footer
        html.Hr(),
        html.P(
            ["Source: Compustat via WRDS | ",
             html.A("Pymkp on PyPI", href="https://pypi.org/project/Pymkp/", target="_blank")
             ],
            style={"color": "#999", "fontSize": "12px"},
        ),
    ],
)

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@callback(
    Output("markup-chart", "figure"),
    Output("stats-row", "children"),
    Input("measure", "value"),
    Input("weight", "value"),
    Input("industries", "value"),
    Input("year-range", "value"),
    Input("show-individual", "value"),
)
def update_chart(measure, weight, industries, year_range, show_individual):
    # Filter
    mask = (DF["year"] >= year_range[0]) & (DF["year"] <= year_range[1])
    filtered = DF[mask].copy()

    if industries:
        filtered = filtered[filtered["ind2d"].isin(industries)]

    # Drop NaN for selected measure
    filtered = filtered.dropna(subset=[measure])

    if filtered.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data for selected filters", showarrow=False,
                           font=dict(size=20, color="gray"))
        return fig, []

    # Aggregate helper
    def _aggregate(data):
        if weight == "revenue":
            return (
                data.groupby("year", group_keys=False)
                .apply(lambda g: (g[measure] * g["sale_D"]).sum() / g["sale_D"].sum(),
                       include_groups=False)
                .reset_index(name="value")
            )
        elif weight == "cost":
            return (
                data.groupby("year", group_keys=False)
                .apply(lambda g: (g[measure] * g["cogs_D"]).sum() / g["cogs_D"].sum(),
                       include_groups=False)
                .reset_index(name="value")
            )
        elif weight == "median":
            return data.groupby("year")[measure].median().reset_index(name="value")
        else:  # mean
            return data.groupby("year")[measure].mean().reset_index(name="value")

    # Build figure
    fig = go.Figure()

    if industries and len(industries) > 1:
        # Multiple industries selected → one line per industry + aggregate
        # Aggregate line (all selected industries combined)
        agg_all = _aggregate(filtered).sort_values("year")
        fig.add_trace(go.Scatter(
            x=agg_all["year"], y=agg_all["value"],
            mode="lines",
            line=dict(color="#1f77b4", width=3),
            name="Avg of selected industries",
        ))
        # Per-industry lines (only if checkbox is checked)
        if "show" in (show_individual or []):
            colors = ["#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
                      "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#aec7e8"]
            for i, ind in enumerate(sorted(industries)):
                ind_data = filtered[filtered["ind2d"] == ind]
                if ind_data.empty:
                    continue
                ind_agg = _aggregate(ind_data).sort_values("year")
                label = f"{int(ind)} - {NAICS_MAP.get(int(ind), 'Unknown')}"
                fig.add_trace(go.Scatter(
                    x=ind_agg["year"], y=ind_agg["value"],
                    mode="lines",
                    line=dict(color=colors[i % len(colors)], width=1.5, dash="dash"),
                    name=label,
                ))
        agg = agg_all
    else:
        # No industry filter or single industry → one line
        agg = _aggregate(filtered).sort_values("year")
        fig.add_trace(go.Scatter(
            x=agg["year"], y=agg["value"],
            mode="lines",
            line=dict(color="#1f77b4", width=2.5),
            name=MEASURES.get(measure, measure),
        ))

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Year",
        yaxis_title=MEASURES.get(measure, measure),
        margin=dict(l=60, r=20, t=40, b=40),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # Stats (based on aggregate of all selected)
    latest = agg["value"].iloc[-1]
    mean_val = agg["value"].mean()
    n_firms = filtered.groupby("year")["gvkey"].nunique().mean()

    stats = [
        _stat_card("Latest", f"{latest:.3f}"),
        _stat_card("Mean", f"{mean_val:.3f}"),
        _stat_card("Min", f"{agg['value'].min():.3f}"),
        _stat_card("Max", f"{agg['value'].max():.3f}"),
        _stat_card("Avg firms/year", f"{n_firms:,.0f}"),
    ]

    return fig, stats


@callback(
    Output("top-title", "children"),
    Output("top-table", "children"),
    Output("bottom-title", "children"),
    Output("bottom-table", "children"),
    Output("contrib-title", "children"),
    Output("contrib-table", "children"),
    Input("table-measure", "value"),
    Input("industries", "value"),
    Input("table-year-start", "value"),
    Input("table-year-end", "value"),
    Input("contrib-weight", "value"),
)
def update_tables(measure, industries, year_start, year_end, contrib_weight):
    # Filter to table period
    y0, y1 = min(year_start, year_end), max(year_start, year_end)
    mask = (DF["year"] >= y0) & (DF["year"] <= y1)
    filtered = DF[mask].copy()

    if industries:
        filtered = filtered[filtered["ind2d"].isin(industries)]

    filtered = filtered.dropna(subset=[measure])

    period = str(y0) if y0 == y1 else f"{y0}-{y1}"
    top_title = f"Top 10 Avg Markup ({period})"
    bottom_title = f"Bottom 10 Avg Markup ({period})"

    contrib_title = f"Top 10 Contributors ({period})"
    if filtered.empty:
        return top_title, "No data", bottom_title, "No data", contrib_title, "No data"

    # Average markup per firm over the period
    firm_avg = (
        filtered.groupby(["gvkey", "conm", "ind2d"])[measure]
        .mean()
        .reset_index()
        .sort_values(measure, ascending=False)
    )

    top10 = firm_avg.head(10)[["conm", "ind2d", measure]].copy()
    bottom10 = firm_avg.tail(10).sort_values(measure)[["conm", "ind2d", measure]].copy()

    # Top contributors: share × markup
    weight_col = "sale_D" if contrib_weight == "revenue" else "cogs_D"
    filtered["_share"] = filtered[weight_col] / filtered.groupby("year")[weight_col].transform("sum")
    filtered["_contribution"] = filtered["_share"] * filtered[measure]
    contrib_avg = (
        filtered.groupby(["gvkey", "conm", "ind2d"])
        .agg({measure: "mean", "_contribution": "mean", "_share": "mean"})
        .reset_index()
        .sort_values("_contribution", ascending=False)
    )
    top_contrib = contrib_avg.head(10)[["conm", "ind2d", measure, "_share", "_contribution"]].copy()

    measure_label = MEASURES.get(measure, measure)

    def _make_table(df):
        df = df.copy()
        df.columns = ["Firm", "Industry", measure_label]
        df[measure_label] = df[measure_label].map(lambda x: f"{x:.3f}")
        df["Industry"] = df["Industry"].map(lambda x: NAICS_MAP.get(int(x), str(int(x))) if pd.notna(x) else "")
        return html.Table(
            [html.Tr([html.Th(c, style={"padding": "6px 12px", "borderBottom": "2px solid #ddd",
                                         "textAlign": "left", "fontSize": "13px"}) for c in df.columns])]
            + [html.Tr([html.Td(row[c], style={"padding": "5px 12px", "borderBottom": "1px solid #eee",
                                                "fontSize": "13px"}) for c in df.columns])
               for _, row in df.iterrows()],
            style={"borderCollapse": "collapse", "width": "100%"},
        )

    def _make_contrib_table(df):
        df = df.copy()
        df.columns = ["Firm", "Industry", "Markup", "Share", "Contribution"]
        df["Markup"] = df["Markup"].map(lambda x: f"{x:.3f}")
        df["Share"] = df["Share"].map(lambda x: f"{x:.4f}")
        df["Contribution"] = df["Contribution"].map(lambda x: f"{x:.4f}")
        df["Industry"] = df["Industry"].map(lambda x: NAICS_MAP.get(int(x), str(int(x))) if pd.notna(x) else "")
        return html.Table(
            [html.Tr([html.Th(c, style={"padding": "6px 12px", "borderBottom": "2px solid #ddd",
                                         "textAlign": "left", "fontSize": "13px"}) for c in df.columns])]
            + [html.Tr([html.Td(row[c], style={"padding": "5px 12px", "borderBottom": "1px solid #eee",
                                                "fontSize": "13px"}) for c in df.columns])
               for _, row in df.iterrows()],
            style={"borderCollapse": "collapse", "width": "100%"},
        )

    return (top_title, _make_table(top10), bottom_title, _make_table(bottom10),
            contrib_title, _make_contrib_table(top_contrib))


# Build firm options for search (unique firm names)
_FIRM_OPTIONS = (
    DF[["gvkey", "conm"]].drop_duplicates()
    .sort_values("conm")
    .apply(lambda r: {"label": r["conm"], "value": r["gvkey"]}, axis=1)
    .tolist()
)


@callback(
    Output("firm-search", "options"),
    Input("firm-measure", "value"),
)
def update_firm_options(measure):
    valid_gvkeys = DF.dropna(subset=[measure])["gvkey"].unique()
    return [opt for opt in _FIRM_OPTIONS if opt["value"] in valid_gvkeys]


@callback(
    Output("firm-chart", "figure"),
    Input("firm-search", "value"),
    Input("firm-measure", "value"),
    Input("firm-year-start", "value"),
    Input("firm-year-end", "value"),
)
def update_firm_chart(gvkeys, measure, year_start, year_end):
    fig = go.Figure()

    if not gvkeys:
        fig.add_annotation(text="Search and select firms above", showarrow=False,
                           font=dict(size=16, color="gray"))
        fig.update_layout(template="plotly_white", margin=dict(l=60, r=20, t=40, b=40))
        return fig

    y0, y1 = min(year_start, year_end), max(year_start, year_end)
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
              "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]

    for i, gvkey in enumerate(gvkeys[:20]):  # cap at 20 firms to keep it responsive
        firm_data = DF[(DF["gvkey"] == gvkey) & (DF["year"] >= y0) & (DF["year"] <= y1)].copy()
        firm_data = firm_data.dropna(subset=[measure]).sort_values("year")
        if firm_data.empty:
            continue
        name = firm_data["conm"].iloc[0]
        fig.add_trace(go.Scatter(
            x=firm_data["year"], y=firm_data[measure],
            mode="lines+markers",
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=4),
            name=name,
        ))

    measure_label = MEASURES.get(measure, measure)
    fig.update_layout(
        template="plotly_white",
        xaxis_title="Year",
        yaxis_title=measure_label,
        margin=dict(l=60, r=20, t=40, b=40),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def _stat_card(label, value):
    return html.Div([
        html.Div(label, style={"color": "#666", "fontSize": "12px"}),
        html.Div(value, style={"fontSize": "22px", "fontWeight": "bold"}),
    ])


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=8050)
