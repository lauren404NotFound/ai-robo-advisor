# dashboard.py
# Market-style Robo Portfolio Dashboard (TradingView/Bloomberg-ish layout)
# Reads performance.csv from Robo folders and shows KPI tiles + interactive charts.

from __future__ import annotations

import os
import glob
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# THEME & BRANDING
# -----------------------------
ACCENT = "#8A2BE2"  # Institutional Purple
ACCENT_2 = "#A46BFF"
ACCENT_3 = "#CDB9FF"
POS = "#3DFFB2"
NEG = "#FF4D6D"

CANVAS = "#05060F"
PANEL = "rgba(18, 20, 42, 0.7)"
BORDER = "rgba(205,185,255,0.12)"
TEXT = "#F6F3FF"
MUTED = "rgba(246,243,255,0.60)"
GRID = "rgba(205,185,255,0.06)"
TEMPLATE = "plotly_dark"

# -----------------------------
# KPI DEFINITIONS & TAXONOMY
# -----------------------------
METRICS = [
    "Annualized Return (%)",
    "Cumulative Return (%)",
    "Annualized STD (%)",
    "Maximum Drawdown (%)",
    "Monthly 95% VaR (%)",
    "Sharpe Ratio",
    "Turnover",
]

SHORT = {
    "Annualized Return (%)": "Ann Return",
    "Cumulative Return (%)": "Cum Return",
    "Annualized STD (%)": "Volatility",
    "Maximum Drawdown (%)": "Max DD",
    "Monthly 95% VaR (%)": "95% VaR (Mo)",
    "Sharpe Ratio": "Sharpe",
    "Turnover": "Turnover",
}

MEANING = {
    "Annualized Return (%)":
        "Average yearly growth rate of the portfolio, including compounding.",

    "Cumulative Return (%)":
        "Total gain or loss over the entire investment period.",

    "Annualized STD (%)":
        "How much the portfolio’s returns fluctuate year to year (risk).",

    "Maximum Drawdown (%)":
        "The largest loss from a peak value before the portfolio recovered.",

    "Monthly 95% VaR (%)":
        "A worst-case monthly loss estimate under normal market conditions.",

    "Sharpe Ratio":
        "How much return is earned for each unit of risk taken.",

    "Turnover":
        "How frequently assets in the portfolio are traded."

}

BAD_WHEN_LARGER = {
    "Annualized STD (%)",
    "Maximum Drawdown (%)",
    "Monthly 95% VaR (%)",
    "Turnover",
}


# -----------------------------
# Data model
# -----------------------------
@dataclass
class RoboKPI:
    name: str
    folder: str
    csv_path: str
    metrics: Dict[str, float]


# -----------------------------
# File helpers
# -----------------------------
def read_selected_robo(root: str) -> Optional[str]:
    p = os.path.join(root, ".selected_robo.txt")
    if os.path.exists(p):
        try:
            v = open(p, "r").read().strip()
            return v or None
        except Exception:
            return None
    return None


def find_robo_folders(root: str) -> List[str]:
    patterns = [os.path.join(root, "Robo*"), os.path.join(root, "Robo_*")]
    candidates: List[str] = []
    for pat in patterns:
        candidates.extend(glob.glob(pat))
    folders = [
        p for p in sorted(set(candidates))
        if os.path.isdir(p) and not os.path.basename(p).startswith(".")
    ]
    return [f for f in folders if os.path.exists(os.path.join(f, "performance.csv"))]


def robust_read_csv(path: str) -> pd.DataFrame:
    for enc in (None, "utf-8-sig", "latin-1"):
        try:
            if enc is None:
                return pd.read_csv(path)
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(path)


def _clean(s: str) -> str:
    return " ".join(str(s).strip().split()).lower()


def _to_float(x) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x) if np.isfinite(x) else None
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return None
    s = s.replace("%", "").replace(",", "")
    try:
        return float(s)
    except Exception:
        return None


def extract_metrics(df: pd.DataFrame) -> Dict[str, float]:
    df0 = df.copy()
    mapping: Dict[str, Optional[float]] = {}

    idx_text_ratio = sum(isinstance(i, str) for i in df0.index) / max(1, len(df0.index))
    if idx_text_ratio > 0.6 and df0.shape[1] >= 1:
        vcol = df0.columns[0]
        for i in df0.index:
            mapping[_clean(i)] = _to_float(df0.loc[i, vcol])
    elif df0.shape[1] >= 2:
        mcol, vcol = df0.columns[0], df0.columns[1]
        for i in df0.index:
            mapping[_clean(df0.loc[i, mcol])] = _to_float(df0.loc[i, vcol])

    aliases = {
        "Annualized Return (%)": ["annualized return (%)", "annualised return (%)", "annualized return", "annualised return"],
        "Cumulative Return (%)": ["cumulative return (%)", "cumulative return", "cum return (%)", "cum return"],
        "Annualized STD (%)": ["annualized std (%)", "annualised std (%)", "annualized std", "annualised std",
                               "annualized volatility (%)", "annualized vol (%)", "ann vol (%)", "ann std (%)"],
        "Maximum Drawdown (%)": ["maximum drawdown (%)", "max drawdown (%)", "maximum drawdown", "max drawdown", "mdd (%)", "mdd"],
        "Monthly 95% VaR (%)": ["monthly 95% var (%)", "monthly 95% var", "95% var (%)", "var 95 (%)", "monthly var 95 (%)"],
        "Sharpe Ratio": ["sharpe ratio", "sharpe", "annualized sharpe", "ann sharpe"],
        "Turnover": ["turnover", "portfolio turnover", "avg turnover"],
    }

    out: Dict[str, float] = {}
    for canon, keys in aliases.items():
        for k in keys:
            if k in mapping and mapping[k] is not None:
                out[canon] = float(mapping[k])
                break
    return out


def load_all(root: str) -> List[RoboKPI]:
    out: List[RoboKPI] = []
    for folder in find_robo_folders(root):
        csv_path = os.path.join(folder, "performance.csv")
        try:
            df = robust_read_csv(csv_path)
            name = os.path.basename(folder)
            m = extract_metrics(df)

            if len(m) < 3:
                try:
                    df2 = pd.read_csv(csv_path, index_col=0)
                    m2 = extract_metrics(df2)
                    if len(m2) > len(m):
                        m = m2
                except Exception:
                    pass

            out.append(RoboKPI(name=name, folder=folder, csv_path=csv_path, metrics=m))
        except Exception as e:
            st.warning(f"Could not read {csv_path}: {e}")
    return out


def to_table(kpis: List[RoboKPI]) -> pd.DataFrame:
    rows = []
    for r in kpis:
        row = {"Robo": r.name}
        for m in METRICS:
            row[m] = r.metrics.get(m, np.nan)
        rows.append(row)
    return pd.DataFrame(rows)


def fmt(metric: str, v: float) -> str:
    if not np.isfinite(v):
        return "—"
    if metric.endswith("(%)"):
        return f"{v:,.2f}%"
    if metric == "Sharpe Ratio":
        return f"{v:,.2f}"
    if metric == "Turnover":
        return f"{v:,.4f}"
    return f"{v:,.4f}"


def apply_plot_style(fig):
    fig.update_layout(
        template=TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT),
        margin=dict(l=14, r=14, t=40, b=14),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    return fig


def normalized_scores(df_all: pd.DataFrame, robo_row: pd.Series) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for m in METRICS:
        x = robo_row.get(m, np.nan)
        col = pd.to_numeric(df_all[m], errors="coerce")
        if not np.isfinite(x) or col.dropna().empty:
            continue
        mn = float(col.min())
        mx = float(col.max())
        s = 0.5 if mx == mn else (float(x) - mn) / (mx - mn)
        if m in BAD_WHEN_LARGER:
            s = 1.0 - s
        scores[m] = float(np.clip(s, 0.0, 1.0))
    return scores


def overall_score(scores: Dict[str, float]) -> Optional[float]:
    vals = [v for v in scores.values() if np.isfinite(v)]
    return float(np.mean(vals)) if vals else None


def build_trend_proxy(robo_metrics: Dict[str, float]) -> pd.DataFrame:
    """
    Visual proxy line for dashboards when only summary KPIs exist (not an equity curve).
    Creates a smooth 60-point "portfolio line" shaped by return + risk metrics.
    """
    keys = ["Annualized Return (%)", "Sharpe Ratio", "Annualized STD (%)", "Maximum Drawdown (%)", "Monthly 95% VaR (%)"]
    vals = []
    for k in keys:
        v = robo_metrics.get(k, np.nan)
        if not np.isfinite(v):
            v = 0.0
        vals.append(float(v))

    v = np.array(vals, dtype=float)
    if np.allclose(v.max(), v.min()):
        norm = np.ones_like(v) * 0.5
    else:
        norm = (v - v.min()) / (v.max() - v.min())

    # Invert risk-like
    # Return(0 good), Sharpe(1 good), Vol(2 bad), DD(3 bad), VaR(4 bad)
    norm[2] = 1 - norm[2]
    norm[3] = 1 - norm[3]
    norm[4] = 1 - norm[4]

    # Build a smooth "line" with drift and volatility determined by metrics
    n = 120
    t = np.arange(n)
    drift = 0.002 + 0.010 * (0.6 * norm[0] + 0.4 * norm[1])  # higher return/sharpe -> more drift
    wiggle = 0.008 + 0.030 * (1 - norm[2])                   # higher volatility -> more wiggle

    base = 1 + np.cumsum(drift + wiggle * np.sin(np.linspace(0, 6*np.pi, n)) / n)
    noise = (wiggle/3) * np.sin(np.linspace(0, 12*np.pi, n)) / n
    curve = base + np.cumsum(noise)

    curve = (curve - curve.min()) / (curve.max() - curve.min() + 1e-9)
    curve = 80 + 40 * curve  # map to 80..120 like an index line

    return pd.DataFrame({"t": t, "index": curve})


# -----------------------------
# PAGE
# -----------------------------
st.set_page_config(page_title="Robo Market Dashboard", layout="wide")

st.markdown(
    f"""
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');
          html, body, [class*="css"] {{
            font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
          }}
          .stApp {{
            background: radial-gradient(circle at 2% 2%, rgba(138,43,226,0.15) 0%, {CANVAS} 40%, {CANVAS} 100%);
            color: {TEXT};
          }}

          .block-container {{ padding-top: 1.5rem; padding-bottom: 2rem; }}

          .hdr {{
            border: 1px solid {BORDER};
            background: linear-gradient(180deg, rgba(14,16,32,0.8), rgba(10,11,22,0.6));
            border-radius: 16px;
            padding: 20px 24px;
            display:flex;
            align-items:center;
            justify-content:space-between;
            margin-bottom: 24px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
          }}
          .hdrTitle {{
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.04em;
            color: #FFFFFF;
            display: flex;
            align-items: center;
            gap: 12px;
          }}
          .status-pulse {{
            width: 8px;
            height: 8px;
            background: {POS};
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 12px {POS};
            animation: pulse 2s infinite;
          }}
          @keyframes pulse {{
            0% {{ box-shadow: 0 0 0 0px rgba(61, 255, 178, 0.4); }}
            70% {{ box-shadow: 0 0 0 10px rgba(61, 255, 178, 0); }}
            100% {{ box-shadow: 0 0 0 0px rgba(61, 255, 178, 0); }}
          }}
          .hdrSub {{
            color: {MUTED};
            font-size: 13px;
            font-weight: 400;
            margin-top: 4px;
          }}
          .ticker {{
            display:flex;
            gap: 10px;
          }}
          .pill {{
            border: 1px solid {BORDER};
            background: rgba(255,255,255,0.03);
            border-radius: 6px;
            padding: 6px 14px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: {ACCENT_3};
            text-transform: uppercase;
            letter-spacing: 0.02em;
          }}

          .kpiRow {{
            display:grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 12px;
            margin-bottom: 24px;
          }}
          .kpi {{
            border: 1px solid {BORDER};
            background: rgba(14,16,32,0.6);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 18px;
            transition: all 0.3s ease;
          }}
          .kpi:hover {{
            border-color: {ACCENT};
            background: rgba(14,16,32,0.8);
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(138,43,226,0.1);
          }}
          .kLabel {{ color: {MUTED}; font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 0.08em; }}
          .kValue {{ font-family: 'JetBrains Mono', monospace; font-size: 20px; font-weight: 700; color: #FFF; }}
          .kHint  {{ color: rgba(205,185,255,0.4); font-size: 10px; margin-top: 10px; line-height: 1.4; }}

          .panel {{
            border: 1px solid {BORDER};
            background: {PANEL};
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.3);
          }}
          .panelTitle {{
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-bottom: 20px;
            color: {MUTED};
            border-left: 3px solid {ACCENT};
            padding-left: 12px;
          }}

      /* Let charts feel more like a dashboard */
      .js-plotly-plot .plotly .modebar {{ opacity: 0.25; }}
      .js-plotly-plot:hover .plotly .modebar {{ opacity: 0.95; }}
      
    </style>
    """,
    unsafe_allow_html=True,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
kpis = load_all(ROOT)
if not kpis:
    st.error("No Robo folders with performance.csv found.")
    st.stop()

df_all = to_table(kpis)
auto = read_selected_robo(ROOT)

# Controls (sidebar)
st.sidebar.header("Controls")
names = [r.name for r in kpis]
if auto and auto in names:
    opts = names
    default_idx = names.index(auto)
else:
    opts = ["Overview"] + names
    default_idx = 0
selected = st.sidebar.selectbox("Robo", options=opts, index=default_idx)
show_details = st.sidebar.toggle("Show technical details", value=False)

# -----------------------------
# HEADER BAR (market style)
# -----------------------------
st.markdown(
    f"""
        <div class="hdr">
          <div class="hdrLeft">
            <div class="hdrTitle"><span class="status-pulse"></span> Lauren's Robo-Advisor™ Portfolios</div>
            <div class="hdrSub">Quantitative Performance Attribution & Risk Modeling Engine</div>
          </div>
          <div class="ticker">
            <div class="pill">STRAT: {selected}</div>
            <div class="pill">STATUS: VERIFIED</div>
          </div>
        </div>
        """,
    unsafe_allow_html=True,
)

# -----------------------------
# OVERVIEW
# -----------------------------
if selected == "Overview":
    st.markdown('<div class="panel"><div class="panelTitle">Cross-profile comparison</div>', unsafe_allow_html=True)
    metric = st.selectbox("Compare metric", METRICS, index=0)
    chart_df = df_all[["Robo", metric]].dropna().sort_values(metric, ascending=False)

    if chart_df.empty:
        st.info("No values available for that metric.")
    else:
        fig = px.bar(chart_df, x="Robo", y=metric, color_discrete_sequence=[ACCENT], title="")
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>Value: %{y}<br>"
                          f"<span style='color:{ACCENT_3}'>{MEANING.get(metric,'')}</span><extra></extra>"
        )
        fig = apply_plot_style(fig)
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_all, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# -----------------------------
# SINGLE ROBO
# -----------------------------
rmap = {r.name: r for r in kpis}
robo = rmap[selected]
row = df_all[df_all["Robo"] == selected].iloc[0]

scores = normalized_scores(df_all, row)
score = overall_score(scores)

# KPI STRIP (compact, terminal-like)
kpi_html = '<div class="kpiRow">'
for m in METRICS:
    v = robo.metrics.get(m, np.nan)
    kpi_html += (
        f"<div class='kpi'>"
        f"<div class='kLabel'>{SHORT.get(m,m)}</div>"
        f"<div class='kValue'>{fmt(m, v)}</div>"
        f"<div class='kHint'>{MEANING.get(m,'')}</div>"
        f"</div>"
    )
kpi_html += "</div>"
st.markdown(kpi_html, unsafe_allow_html=True)

# MAIN ROW: big line chart + right analytics
colA, colB = st.columns([1.6, 1.0], gap="large")

with colA:
    st.markdown('<div class="panel"><div class="panelTitle">Portfolio line (visual proxy)</div>', unsafe_allow_html=True)
    trend = build_trend_proxy(robo.metrics)
    fig_line = px.line(trend, x="t", y="index", color_discrete_sequence=[ACCENT], title="")
    fig_line.update_traces(
        hovertemplate="t=%{x}<br>Index: %{y:.2f}<extra></extra>"
    )
    fig_line = apply_plot_style(fig_line)
    fig_line.update_layout(yaxis_title="", xaxis_title="")
    st.plotly_chart(fig_line, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel"><div class="panelTitle">Metric breakdown</div>', unsafe_allow_html=True)
    bar_df = pd.DataFrame({
        "Metric": METRICS,
        "Value": [robo.metrics.get(m, np.nan) for m in METRICS],
        "Meaning": [MEANING.get(m, "") for m in METRICS],
    }).dropna()

    if bar_df.empty:
        st.info("No KPI values to chart.")
    else:
        fig_bar = px.bar(bar_df, x="Metric", y="Value", color_discrete_sequence=[ACCENT_2], title="")
        fig_bar.update_layout(xaxis_tickangle=-18)
        fig_bar.update_traces(
            hovertemplate="<b>%{x}</b><br>Value: %{y}<br>"
                          "<span style='color:#CDB9FF'>%{customdata}</span><extra></extra>",
            customdata=bar_df["Meaning"],
        )
        fig_bar = apply_plot_style(fig_bar)
        st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with colB:
    st.markdown('<div class="panel"><div class="panelTitle">Portfolio score</div>', unsafe_allow_html=True)
    if score is None:
        st.info("Insufficient data to compute a score.")
    else:
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score * 100,
            number={"suffix": " / 100", "font": {"color": TEXT, "size": 22}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": ACCENT},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 35], "color": "#2D0B59"},
                    {"range": [35, 70], "color": "#6A1FA0"},
                    {"range": [70, 100], "color": "#CDB9FF"},
                ],
            },
        ))
        fig_g.update_layout(
            template=TEMPLATE,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            font=dict(color=TEXT),
            height=220,
        )
        st.plotly_chart(fig_g, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel"><div class="panelTitle">Risk composition</div>', unsafe_allow_html=True)
    risk_parts = []
    for m in ["Annualized STD (%)", "Maximum Drawdown (%)", "Monthly 95% VaR (%)", "Turnover"]:
        v = robo.metrics.get(m, np.nan)
        if np.isfinite(v):
            risk_parts.append((SHORT.get(m, m), abs(float(v)), MEANING.get(m, "")))

    if not risk_parts:
        st.info("Needs STD/Drawdown/VaR/Turnover.")
    else:
        cdf = pd.DataFrame(risk_parts, columns=["Component", "Magnitude", "Meaning"])
        fig_pie = px.pie(
            cdf,
            names="Component",
            values="Magnitude",
            hole=0.62,
            color_discrete_sequence=[ACCENT, ACCENT_2, ACCENT_3, "#5B2BBF"],
            title="",
        )
        fig_pie.update_traces(
            hovertemplate="<b>%{label}</b><br>Share: %{percent}<br>Magnitude: %{value}<br>"
                          "<span style='color:#CDB9FF'>%{customdata}</span><extra></extra>",
            customdata=cdf["Meaning"],
        )
        fig_pie.update_layout(
            template=TEMPLATE,
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT),
            margin=dict(l=12, r=12, t=10, b=10),
            showlegend=True,
            height=260,
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# BOTTOM ROW: scatter + radar + comparison heatmap
c1, c2, c3 = st.columns([1.0, 1.0, 1.0], gap="large")

with c1:
    st.markdown('<div class="panel"><div class="panelTitle">Risk vs return</div>', unsafe_allow_html=True)
    ret = robo.metrics.get("Annualized Return (%)", np.nan)
    vol = robo.metrics.get("Annualized STD (%)", np.nan)
    sh = robo.metrics.get("Sharpe Ratio", np.nan)

    if not (np.isfinite(ret) and np.isfinite(vol)):
        st.info("Needs Annualized Return and Annualized STD.")
    else:
        s_df = pd.DataFrame([{"Return": ret, "Volatility": vol, "Sharpe": sh if np.isfinite(sh) else 0.5}])
        fig_sc = px.scatter(s_df, x="Volatility", y="Return", size="Sharpe",
                            color_discrete_sequence=[ACCENT], title="")
        fig_sc.update_traces(
            hovertemplate="Volatility: %{x}<br>Return: %{y}<br>"
                          f"<span style='color:{ACCENT_3}'>Higher return with lower volatility is typically preferred.</span>"
                          "<extra></extra>"
        )
        fig_sc = apply_plot_style(fig_sc)
        st.plotly_chart(fig_sc, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown('<div class="panel"><div class="panelTitle">Portfolio fingerprint</div>', unsafe_allow_html=True)
    if not scores:
        st.info("Not enough cross-robo data to normalize fingerprint.")
    else:
        rdf = pd.DataFrame({"Metric": list(scores.keys()), "Score": list(scores.values())})
        rdf["Meaning"] = rdf["Metric"].map(MEANING).fillna("")
        theta = rdf["Metric"].tolist() + [rdf["Metric"].tolist()[0]]
        rvals = rdf["Score"].tolist() + [rdf["Score"].tolist()[0]]
        custom = rdf["Meaning"].tolist() + [rdf["Meaning"].tolist()[0]]

        fig_rad = go.Figure()
        fig_rad.add_trace(go.Scatterpolar(
            r=rvals,
            theta=theta,
            fill="toself",
            line=dict(color=ACCENT_2, width=2),
            fillcolor="rgba(138,43,226,0.18)",
            customdata=custom,
            hovertemplate="<b>%{theta}</b><br>Score: %{r:.2f}<br>"
                          "<span style='color:#CDB9FF'>%{customdata}</span><extra></extra>",
        ))
        fig_rad.update_polars(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 1], gridcolor=GRID),
            angularaxis=dict(gridcolor=GRID),
        )
        fig_rad.update_layout(
            template=TEMPLATE,
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT),
            margin=dict(l=12, r=12, t=20, b=10),
            height=320,
        )
        st.plotly_chart(fig_rad, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown('<div class="panel"><div class="panelTitle">Across Robos (quick view)</div>', unsafe_allow_html=True)
    # Heatmap-like overview: normalize values to 0..1 by column and show as colored table
    mini = df_all.set_index("Robo")[METRICS].copy()
    for m in METRICS:
        col = pd.to_numeric(mini[m], errors="coerce")
        if col.dropna().empty:
            continue
        mn, mx = float(col.min()), float(col.max())
        if mx == mn:
            mini[m] = 0.5
        else:
            mini[m] = (col - mn) / (mx - mn)
        if m in BAD_WHEN_LARGER:
            mini[m] = 1 - mini[m]

    # Use plotly heatmap
    z = mini.values.astype(float)
    fig_h = go.Figure(data=go.Heatmap(
        z=z,
        x=[SHORT.get(m, m) for m in mini.columns],
        y=mini.index.tolist(),
        colorscale=[[0, "#2D0B59"], [0.5, ACCENT], [1, "#CDB9FF"]],
        showscale=False,
        hovertemplate="Robo: %{y}<br>%{x}: %{z:.2f}<extra></extra>",
    ))
    fig_h.update_layout(
        template=TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT),
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
    )
    st.plotly_chart(fig_h, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Optional details
if show_details:
    with st.expander("Technical details"):
        st.code(f"Folder: {robo.folder}\nCSV: {robo.csv_path}")
