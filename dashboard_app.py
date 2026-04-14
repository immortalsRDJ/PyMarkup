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
    df = pd.read_parquet(DATA_DIR / "firm_markups.parquet")
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
)
def update_chart(measure, weight, industries, year_range):
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
            name="All selected",
        ))
        # Per-industry lines
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
