"""
ui/charts.py
============
Plotly chart factory functions:
  _style, donut_chart, growth_line, monte_chart, shap_fig, prob_fig
"""
from __future__ import annotations
import plotly.graph_objects as go
import streamlit as st

from ui.styles import (
    ACCENT, ACCENT2, TEXT, GRID, TMPL, POS, NEG, PROFILE_COLORS,
)
from ui.auth import get_currency_symbol

def _style(fig, height=None):
    kw = dict(template=TMPL, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
              font=dict(color=TEXT, family="Inter, system-ui, sans-serif"),
              margin=dict(l=14, r=14, t=30, b=14),
              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
    if height: kw["height"] = height
    fig.update_layout(**kw)
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    return fig

def donut_chart(alloc):
    labels = list(alloc.keys()); values = list(alloc.values())
    palette = ["#9B72F2","#B18AFF","#4AE3A0","#60A5FA","#FBBF24","#F97316","#6EE7B7"][:len(labels)]
    
    asset_descriptions = {
        "US Equities": "Shares of the largest United States companies.",
        "Global Equities": "Shares of companies from all over the world.",
        "Technology": "Shares of technology companies like Apple and Microsoft.",
        "Core Fixed Income": "Safe, stable bonds (like loans to the government).",
        "Gold": "Investments in physical gold for protection against inflation.",
        "Commodities": "Raw materials like oil, wheat, and natural gas.",
        "Real Estate": "Investments in property and real estate.",
        "ESG Equities": "Companies selected for good environmental & social practices."
    }
    custom_data = [asset_descriptions.get(lbl, "Investment asset component.") for lbl in labels]
    
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.6,
        marker_colors=palette, textinfo="percent", customdata=custom_data,
        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<br><i>%{customdata}</i><extra></extra>", textfont_size=11))
    fig.update_layout(template=TMPL, paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT), margin=dict(l=0,r=0,t=0,b=0), height=240, showlegend=True,
        legend=dict(orientation="v", valign="middle", yanchor="middle", y=0.5, xanchor="left", x=1.1))
    return fig

def growth_line(curve, color):
    r,g,b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
    currency = get_currency_symbol()
    fig = go.Figure(go.Scatter(x=curve["x"], y=curve["y"], mode="lines",
        line=dict(color=color, width=3), fill="tozeroy",
        fillcolor=f"rgba({r},{g},{b},0.08)",
        hovertemplate=f"Year %{{x:.0f}}<br>{currency}%{{y:,.0f}}<extra></extra>"))
    fig = _style(fig, 300)
    fig.update_layout(xaxis_title="Years", yaxis_title=f"Value ({currency})",
        yaxis_tickprefix=currency, yaxis_tickformat=",.0f")
    return fig

def monte_chart(sim, color):
    r,g,b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
    currency = get_currency_symbol()
    years = sim["years"]; x = list(range(years+1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x+x[::-1],
        y=[sim["p10"]]*(years+1)+[sim["p90"]]*(years+1),
        fill="toself", fillcolor=f"rgba({r},{g},{b},0.10)",
        line=dict(color="rgba(0,0,0,0)"), name="10–90th Pct", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=[sim["p50"]]*(years+1),
        line=dict(color=color, width=2.5), name="Median",
        hovertemplate=f"Year %{{x}}<br>{currency}%{{y:,.0f}}<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=[sim["p25"]]*(years+1),
        line=dict(color=color, dash="dot", width=1), name="25th",
        hovertemplate=f"Year %{{x}}<br>{currency}%{{y:,.0f}}<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=[sim["p75"]]*(years+1),
        line=dict(color=color, dash="dot", width=1), name="75th",
        hovertemplate=f"Year %{{x}}<br>{currency}%{{y:,.0f}}<extra></extra>"))
    fig = _style(fig, 300)
    fig.update_layout(xaxis_title="Years", yaxis_title=f"Value ({currency})",
        yaxis_tickprefix=currency, yaxis_tickformat=",.0f")
    return fig

def shap_fig(contributors):
    feats  = [c["feature"] for c in reversed(contributors)]
    vals   = [c["shap_value"] for c in reversed(contributors)]
    colors = [POS if v > 0 else NEG for v in vals]
    fig = go.Figure(go.Bar(x=vals, y=feats, orientation="h",
        marker_color=colors, hovertemplate="<b>%{y}</b><br>SHAP: %{x:.4f}<extra></extra>"))
    fig = _style(fig, 280)
    fig.update_layout(xaxis_title="SHAP contribution")
    return fig

def prob_fig(probs):
    cats = list(probs.keys()); vals = [p*100 for p in probs.values()]
    colors = [PROFILE_COLORS.get(c, ACCENT2) for c in cats]
    fig = go.Figure(go.Bar(x=cats, y=vals, marker_color=colors,
        hovertemplate="<b>%{x}</b><br>%{y:.1f}%<extra></extra>"))
    fig = _style(fig, 240)
    fig.update_layout(yaxis_title="Probability (%)", yaxis_range=[0,100], xaxis_tickangle=-15)
    return fig
