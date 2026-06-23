from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.theme import current_theme


def base_layout(fig, height=360):
    t = current_theme()
    fig.update_layout(
        template=t["plotly_template"],
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t["text"]),
        margin=dict(l=18, r=18, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.14)", zerolinecolor="rgba(148,163,184,0.18)")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.14)", zerolinecolor="rgba(148,163,184,0.18)")
    return fig


def line_chart(df: pd.DataFrame, x: str, y: str | list[str], title="", height=360, markers=True):
    if df.empty:
        return go.Figure()
    fig = px.line(df, x=x, y=y, markers=markers, title=title)
    return base_layout(fig, height)


def bar_chart(df: pd.DataFrame, x: str, y: str, color: str | None = None, title="", height=360, orientation="v"):
    if df.empty:
        return go.Figure()
    fig = px.bar(df, x=x, y=y, color=color, title=title, orientation=orientation)
    return base_layout(fig, height)


def geographic_figure(state_df: pd.DataFrame, property_df: pd.DataFrame):
    t = current_theme()
    fig = go.Figure()
    if state_df is not None and not state_df.empty:
        valid_states = {
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA",
            "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT",
            "VA", "WA", "WV", "WI", "WY", "DC"
        }
        state_map_df = state_df[state_df["State"].astype(str).str.upper().isin(valid_states)].copy()
        if not state_map_df.empty:
            fig.add_trace(go.Choropleth(
                locations=state_map_df["State"],
                z=state_map_df["Properties"],
                locationmode="USA-states",
                colorscale="Blues",
                marker_line_color="rgba(255,255,255,.35)",
                colorbar_title="Properties",
                text=state_map_df.apply(lambda r: f"{r['State']}<br>Properties: {r['Properties']}<br>Alerts: {r['Alerts']}<br>Avg CPT: ${r['Cost/Treatment']:.2f}" if pd.notna(r.get('Cost/Treatment')) else f"{r['State']}<br>Properties: {r['Properties']}<br>Alerts: {r['Alerts']}", axis=1),
                hoverinfo="text",
                showscale=True,
            ))
    if property_df is not None and not property_df.empty and {"lat", "lon"}.issubset(property_df.columns):
        color_map = {"Critical": "#EF4444", "Review": "#F59E0B", "Info": "#60A5FA", "Normal": "#22C55E"}
        for status, g in property_df.dropna(subset=["lat", "lon"]).groupby("Status"):
            fig.add_trace(go.Scattergeo(
                lon=g["lon"],
                lat=g["lat"],
                mode="markers",
                name=status,
                marker=dict(size=9, color=color_map.get(status, "#94A3B8"), line=dict(width=1, color="white"), opacity=0.92),
                text=g.apply(lambda r: f"{r['Property']}<br>{r['City']}, {r['State']}<br>Status: {r['Status']}<br>Cost: ${r['Total Cost']:,.0f}<br>Cost/Treatment: ${r['Cost/Treatment']:,.2f}" if pd.notna(r.get('Cost/Treatment')) else f"{r['Property']}<br>{r['City']}, {r['State']}<br>Status: {r['Status']}", axis=1),
                hoverinfo="text",
            ))
    fig.update_geos(scope="usa", projection_type="albers usa", showland=True, landcolor="rgba(148,163,184,0.08)", lakecolor="rgba(56,189,248,0.08)")
    fig.update_layout(
        template=t["plotly_template"],
        height=585,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t["text"]),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01),
    )
    return fig
