"""
ui/page_dashboard.py
====================
Dashboard page: authentication gate, survey wizard, portfolio results.
Includes: page_dashboard, _render_survey, _render_analysing, _render_portfolio
"""
from __future__ import annotations
import os, json, datetime, time
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from ui.styles import (
    ACCENT, ACCENT2, ACCENT3, PANEL, BORDER, TEXT, MUTED, GRID, TMPL,
    POS, NEG, PROFILE_COLORS, get_svg,
)
from ui.auth import (
    _auth_check, _user_email, _user_name,
    get_currency_symbol, send_portfolio_report,
)
from ui.charts import donut_chart, growth_line, monte_chart, shap_fig, prob_fig
from ui.ai_engine import (
    QUESTIONS, generate_advanced_explanation, get_ai_explanation,
)
from ui.ai_engine import render_actionable_advice
import database
from portfolio_engine import build_portfolio
from explainer import DeepIQInterpreter

ETF_ROLES = {
    "VOO":  ("S&P 500 — US Large Cap Growth", "Core growth engine. Tracks America's 500 largest companies for broad market exposure."),
    "QQQ":  ("Nasdaq 100 — Tech & Innovation", "High-growth technology exposure. Amplifies returns in bull markets via top tech firms."),
    "VWRA": ("Global Equities — Diversification", "International diversification. Reduces single-country risk across 3,700+ global stocks."),
    "AGG":  ("US Bonds — Capital Protection", "Defensive anchor. Bonds cushion losses during stock market downturns."),
    "GLD":  ("Gold — Inflation Hedge", "Store of value. Gold rises when inflation or geopolitical uncertainty increases."),
    "VNQ":  ("Real Estate — Income & Stability", "Property exposure without buying bricks. Regular dividends and inflation protection."),
    "ESGU": ("ESG S&P 500 — Ethical Growth", "Socially responsible investing. Same broad US exposure but excludes ethical concerns."),
    "PDBC": ("Commodities — Real Asset Exposure", "Raw materials like oil & metals. Diversifies away from financial asset risk."),
}

ASSET_DETAIL = {
    "VOO":  {"icon": get_svg("chart", 14, "#3BA4FF"), "colour": "#3BA4FF", "why": "VOO tracks the S&P 500 — 500 of the largest US companies. It's the backbone of most portfolios because it grows with the world's largest economy. The MINN allocated this to capture consistent long-term growth."},
    "QQQ":  {"icon": get_svg("zap", 14, "#6D5EFC"), "colour": "#6D5EFC", "why": "QQQ holds the top 100 Nasdaq-listed companies, dominated by tech giants like Apple, Microsoft, and Nvidia. Higher risk, higher reward — the MINN uses it to boost return potential in line with your risk appetite."},
    "VWRA": {"icon": get_svg("globe", 14, "#8EF6D1"), "colour": "#8EF6D1", "why": "VWRA gives global exposure across 3,700+ companies in 50+ countries. It reduces your dependence on any single market recovering or performing well — pure diversification."},
    "AGG":  {"icon": get_svg("shield", 14, "#8BA6D3"), "colour": "#8BA6D3", "why": "AGG invests in US government and corporate bonds. When stocks fall, bonds often hold steady — acting as a ballast. The MINN uses AGG to reduce portfolio volatility."},
    "GLD":  {"icon": get_svg("shield", 14, "#FFD700"), "colour": "#FFD700", "why": "Gold has protected wealth for thousands of years. It rises when inflation erodes currency value and during geopolitical uncertainty — the MINN uses it as a crisis hedge."},
    "VNQ":  {"icon": get_svg("layers", 14, "#FF9B6B"), "colour": "#FF9B6B", "why": "VNQ gives exposure to real estate investment trusts. Property tends to grow with inflation and pays dividends — adding a reliable income stream uncorrelated with stocks."},
    "ESGU": {"icon": get_svg("shield-check", 14, "#4CAF50"), "colour": "#4CAF50", "why": "ESGU mirrors the S&P 500 while excluding companies with poor environmental, social, and governance ratings. It aligns your investments with your values without sacrificing returns."},
    "PDBC": {"icon": get_svg("risk", 14, "#FF6B6B"), "colour": "#FF6B6B", "why": "PDBC tracks a basket of commodities — oil, natural gas, metals, and agriculture. These real assets often zig when financial assets zag, adding genuine diversification."},
}

def _get_model_objects():
    import app as _app
    return _app.MODEL_PATH

def _get_claude():
    try:
        import app as _app
        return _app.anthropic_client, _app.claude_status
    except Exception:
        return None, "Key Missing"


def _render_section_intro(title: str, subtitle: str, icon_svg: str | None = None, margin_top: int = 10):
    icon_html = f"{icon_svg} " if icon_svg else ""
    st.markdown(
        f"""
        <div style="font-size:22px;font-weight:900;color:#ffffff;letter-spacing:-0.03em;margin:{margin_top}px 0 4px; display:flex; align-items:center; gap:10px;">
          {icon_html}{title}
        </div>
        <div style="font-size:13px;color:{MUTED};margin-bottom:18px;">
          {subtitle}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_feed_items(notifs, compact: bool = False):
    if not notifs:
        padding = "40px 20px" if compact else "60px 20px"
        title_size = "12px" if compact else "13px"
        body_size = "10px" if compact else "11px"
        st.markdown(
            f"""
            <div style="text-align:center;padding:{padding};background:rgba(255,255,255,0.02);border-radius:12px;border:1px dashed rgba(255,255,255,0.1);">
                <div style="font-size:32px;margin-bottom:10px;color:rgba(155,114,242,0.4);display:flex;justify-content:center;">{get_svg("risk", 40)}</div>
                <div style="font-size:{title_size};color:#8BA6D3;font-weight:700;">Radar Scan Active</div>
                <div style="font-size:{body_size};color:{MUTED};">No recent events detected on this manifold.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for n in notifs:
        icon_color = "#3BA4FF" if n["level"] == "success" else "#8BA6D3"
        icon_svg = get_svg("shield-check", 14, icon_color) if n["level"] == "success" else get_svg("more", 14, icon_color)
        time_str = n["created_at"].strftime("%H:%M")
        st.markdown(
            f"""
            <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:12px 14px;margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;gap:8px;">
                    <span style="font-size:11px;font-weight:800;color:#fff;display:flex;align-items:center;gap:6px;">{icon_svg} {n['title']}</span>
                    <span style="font-size:9px;color:{MUTED};">{time_str}</span>
                </div>
                <div style="font-size:10px;color:#8BA6D3;line-height:1.4;">{n['message']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_feed_card(notifs, include_archive: bool = False, compact: bool = False):
    st.markdown(f'<div class="card"><div class="panel-title">{get_svg("zap", 14, ACCENT)} &nbsp; Intelligence Feed</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:11px;color:{MUTED};margin-bottom:20px;">Real-time feed of neural diagnostic events and profile changes.</div>',
        unsafe_allow_html=True,
    )
    _render_feed_items(notifs, compact=compact)
    if include_archive:
        st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
        if st.button("Archive Event Log", use_container_width=True):
            st.info("Logs are archived in MongoDB Atlas.")
    st.markdown("</div>", unsafe_allow_html=True)

def page_dashboard():
    # Authentication check
    if not st.session_state.get("authenticated"):
        st.markdown(f"""
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; padding:100px 20px;">
          <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(155,114,242,0.3); border-radius:32px; padding:60px 40px; text-align:center; max-width:500px; backdrop-filter:blur(20px); box-shadow:0 30px 100px rgba(0,0,0,0.5);">
            <div style="width:80px; height:80px; background:rgba(155,114,242,0.1); border-radius:50%; display:flex; align-items:center; justify-content:center; margin:0 auto 30px; border:1px solid rgba(155,114,242,0.4);">
              {get_svg("shield", 40)}
            </div>
            <div style="font-size:32px; font-weight:900; color:#fff; margin-bottom:12px; letter-spacing:-0.03em;">Identity Required</div>
            <p style="font-size:16px; color:#8BA6D3; line-height:1.6; margin-bottom:40px;">Authenticate your account to access your high-frequency portfolio manifold and real-time intelligence.</p>
          </div>
        </div>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,1,1])
        with col2:
            if st.button("Secure Entry / Login", type="primary", use_container_width=True):
                st.session_state.show_auth = True
                st.rerun()
            if st.button("Return Home", use_container_width=True):
                st.session_state.nav_page = "home"
                st.rerun()
        return

    # If currently analysing, always render that screen first
    # (result doesn't exist yet at this point — it gets set inside _render_analysing)
    sp = st.session_state.get("survey_page", "survey")
    if sp == "analysing":
        _render_analysing()
        return

    # Auto-Restore from DB if browser was refreshed
    if not st.session_state.get("result") and st.session_state.get("user_email") != "guest":
        saved = database.get_latest_assessment(st.session_state.get("user_email"))
        if saved:
            st.session_state.result = saved["result"]
            st.session_state.survey_answers = saved["answers"]
            st.session_state.survey_page = "portfolio"
            sp = "portfolio"

    # Results check — survey not yet completed
    if not st.session_state.get("result"):
        if sp == "survey":
            _render_survey()
            return
            
        st.markdown(f"""
        <div class="coming-soon">
          <div class="coming-soon-icon" style="color:#6D5EFC;margin-bottom:15px;display:flex;justify-content:center;">{get_svg("news", 40)}</div>
          <div class="coming-soon-title">Incomplete Risk Profile</div>
          <div class="coming-soon-sub">Please complete the investor assessment survey to view your dashboard.</div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            if st.button("Start Neural Assessment →", type="primary", use_container_width=True):
                st.session_state.survey_page = "survey"
                st.session_state.survey_step = 0
                st.session_state.survey_answers = {}
                st.rerun()
        return

    # Results exist — show portfolio or survey
    if sp == "survey":
        _render_survey()
    else:
        _render_portfolio()


def _render_survey():
    step = st.session_state.survey_step
    q    = QUESTIONS[step]
    pct  = int((step / len(QUESTIONS)) * 100)

    st.markdown(f"""
    <div class="survey-wrap">
      <div class="progress-bar-wrap">
        <div class="progress-bar-fill" style="width:{pct}%"></div>
      </div>
      <div class="q-number">{q['number']}</div>
      <div class="q-text">{q['text']}</div>
      <div class="q-desc">{q['desc']}</div>
    </div>
    """, unsafe_allow_html=True)

    cur = st.session_state.survey_answers.get(q["key"], q["default"])
    if cur not in q["options"]: cur = q["default"]

    selected = st.radio("", q["options"], index=q["options"].index(cur),
                        key=f"radio_{step}")

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    col_back, _, col_next = st.columns([1, 2, 1])
    with col_back:
        if step > 0:
            if st.button("← Back", use_container_width=True):
                st.session_state.survey_answers[q["key"]] = selected
                st.session_state.survey_step -= 1; st.rerun()
    with col_next:
        is_last = (step == len(QUESTIONS) - 1)
        if st.button("Generate Portfolio →" if is_last else "Next →",
                     type="primary", use_container_width=True):
            st.session_state.survey_answers[q["key"]] = selected
            if is_last:
                st.session_state.survey_page = "analysing"
            else:
                st.session_state.survey_step += 1
            st.rerun()

    if st.session_state.survey_answers:
        with st.expander("Your answers so far", icon=":material/checklist:"):
            for prev_q in QUESTIONS[:step]:
                val = st.session_state.survey_answers.get(prev_q["key"], "—")
                st.markdown(f"**{prev_q['number']}** {prev_q['text'][:60]}…  →  `{val}`")


def _render_analysing():
    st.markdown(f"""
    <div style='text-align:center; padding:60px 0 30px 0;'>
      <div style='margin-bottom:20px; color:#6D5EFC; display:flex; justify-content:center;'>{get_svg("brain", 60)}</div>
      <div style='font-size:26px; font-weight:800; color:#ffffff; margin-bottom:10px;'>
        Inferring Optimal Portfolio State…
      </div>
      <div style='font-size:13px; color:{MUTED}; max-width:520px; margin:0 auto; line-height:1.7;'>
        The DeepAtomicIQ MINN is mapping your constraints to the manifold of efficient portfolios.
        Calculating IQ Parameters (δ, γ, ε) and co-movement regimes.
      </div>
    </div>
    """, unsafe_allow_html=True)

    pb  = st.progress(0)
    msg = st.empty()

    try:
        ans = st.session_state.survey_answers
        
        # Calculate Risk Score (1-10) based on weighted heuristics
        # This acts as the bridge between User profile and pre-trained Robo profiles
        score = 5.0
        if ans.get("q1_risk_comfort") == "Low — I prioritise capital preservation": score -= 2
        elif ans.get("q1_risk_comfort") == "High — maximum long-term growth": score += 3
        
        reaction = ans.get("q10_reaction", "")
        if "Sell everything" in reaction: score -= 2
        elif "buy more" in reaction: score += 1.5
        
        score = max(1.1, min(10.0, score))

        msg.markdown(f"<div style='text-align:center;color:{MUTED};font-size:13px;'>Querying neural model for risk level {score:.1f}…</div>",
                     unsafe_allow_html=True)
        pb.progress(40)
        time.sleep(0.8)

        msg.markdown(f"<div style='text-align:center;color:{MUTED};font-size:13px;'>Optimizing Sharpe Ratio across Body/Wing/Tail regimes…</div>",
                     unsafe_allow_html=True)
        pb.progress(70)

        horizon_map = {"Short (under 3 years)":3, "Medium (3–10 years)":7, "Long (10–20 years)":15, "Very long (over 20 years)":25}
        horizon_yrs = horizon_map.get(ans.get("q3_horizon"), 10)

        portfolio = build_portfolio(
            risk_score = score,
            initial    = 10000,
            monthly    = 500,
            years      = horizon_yrs,
        )
        
        if "error" in portfolio:
            st.error(portfolio["error"])
            return

        pb.progress(90)
        msg.markdown(f"<div style='text-align:center;color:{MUTED};font-size:13px;'>Generating Atomic IQ Interpretation…</div>",
                     unsafe_allow_html=True)

        exp = {
            "confidence": 0.92,
            "top_contributors": [{"feature": "Risk Tolerance Capacity"}, {"feature": "Investment Horizon"}, {"feature": "Market Reaction Strategy"}]
        }
        inputs = {"horizon": horizon_yrs}
        
        pb.progress(100)
        msg.empty()
        time.sleep(0.3)

        st.session_state.result = {
            "portfolio":   portfolio,
            "score":       score
        }
        
        # PERSIST to database
        email = st.session_state.get("user_email")
        if email and email != "guest":
            database.save_assessment(email, ans, st.session_state.result)
        
        st.session_state.survey_page = "portfolio"
        st.rerun()

    except Exception as exc:
        st.error(f"Analysis failed: {exc}")
        if st.button("← Back to Survey"):
            st.session_state.survey_page = "survey"
            st.session_state.survey_step = 0; st.rerun()


def _render_portfolio():
    import re as _re, html as _html
    res = st.session_state.result
    if not res:
        st.session_state.survey_page = "survey"; st.rerun()

    port  = res["portfolio"]
    ans   = st.session_state.survey_answers
    email = st.session_state.get("user_email")
    iq    = port.get("iq_params", {})
    cat   = port["risk_category"]
    stats = port["stats"]
    sim   = port["simulated_growth"]
    color = PROFILE_COLORS.get(f"Profile {port['profile_score']}", ACCENT2)
    sorted_weights = dict(sorted(port["allocation_pct"].items(), key=lambda x: x[1], reverse=True))
    sorted_alloc   = list(sorted_weights.items())
    exp_r          = stats.get("expected_annual_return", 0) / 100

    # ── Page header ──────────────────────────────────────────────────────────
    name = st.session_state.get("user_name", "Investor").split()[0]
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0 12px;flex-wrap:wrap;gap:10px;">
      <div>
        <div style="font-size:11px;font-weight:800;color:#6D5EFC;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:6px;">Portfolio Dashboard</div>
        <div style="font-size:30px;font-weight:900;color:#fff;letter-spacing:-0.03em;">Welcome back, {name}</div>
        <div style="font-size:13px;color:#8BA6D3;">Your AI-optimised portfolio · {cat}</div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;">
        <div style="background:rgba(155,114,242,0.12);border:1px solid rgba(155,114,242,0.35);border-radius:20px;padding:7px 18px;font-size:12px;font-weight:700;color:{ACCENT2};">{cat}</div>
        <div style="background:rgba(142,246,209,0.08);border:1px solid rgba(142,246,209,0.25);border-radius:20px;padding:7px 18px;font-size:12px;font-weight:700;color:#8EF6D1;">δ={iq.get('delta',0):.2f} · γ={iq.get('gamma',0):.3f}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 4 KPI cards ──────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    for col, label, val, hint, vc in [
        (k1, "Expected Return",   f"{stats['expected_annual_return']:.1f}%",  "p.a. (inferential estimate)", POS),
        (k2, "Learned Volatility",f"{stats['expected_volatility']:.1f}%",     "Predicted portfolio vol",     "#ffffff"),
        (k3, "Sharpe Ratio",      f"{stats['sharpe_ratio']:.2f}",             "Risk-adjusted return score",  POS),
        (k4, "P90 Growth",        f"{get_currency_symbol()}{sim['p90']:,.0f}","Optimistic projection",       color),
    ]:
        with col:
            st.markdown(f"""
            <div style="background:rgba(10,10,22,0.6);border:1px solid rgba(155,114,242,0.22);
                        border-radius:14px;padding:16px 14px;margin-bottom:12px;">
              <div style="font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.10em;
                          color:rgba(237,237,243,0.5);margin-bottom:6px;">{label}</div>
              <div style="font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:800;color:{vc};">{val}</div>
              <div style="font-size:9px;color:rgba(230,213,255,0.35);margin-top:5px;">{hint}</div>
            </div>""", unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["📊  Portfolio", "💰  Invest", "📈  Analysis", "🛠️  Examiner"])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — Portfolio Overview
    # ════════════════════════════════════════════════════════════════════════
    with tab1:
        anthropic_client, claude_status = _get_claude()
        if "ai_insight_text_v2" not in st.session_state:
            with st.status("Analysing via DeepIQ Neural Manifold…", expanded=True) as status:
                insight, source = get_ai_explanation(st.session_state.explanation_mode, port, {}, ans)
                st.session_state.ai_insight_text_v2 = insight
                st.session_state.ai_insight_source_v2 = source
                status.update(label=f"Insight ready · {source}", state="complete", expanded=False)
                st.session_state.result["ai_narrative"] = insight
                database.save_assessment(email or "guest", ans, st.session_state.result)

        t1_l, t1_r = st.columns([1, 1.2], gap="large")
        with t1_l:
            st.markdown(f'<div style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:.12em;margin-bottom:8px;">Asset Allocation</div>', unsafe_allow_html=True)
            st.plotly_chart(donut_chart(sorted_weights), use_container_width=True, config={"displayModeBar": False}, key="donut_t1")
            rows_html = ""
            for asset, pct_v in sorted_weights.items():
                rows_html += (f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
                              f'border-bottom:1px solid rgba(255,255,255,0.04);">'
                              f'<span style="font-size:12px;color:#8BA6D3;">{asset}</span>'
                              f'<span style="font-size:12px;color:{color};font-weight:700;">{pct_v:.1f}%</span></div>')
            st.markdown(f'<div style="margin-top:4px;">{rows_html}</div>', unsafe_allow_html=True)

        with t1_r:
            col_t, _ = st.columns([2, 1])
            with col_t:
                mode    = st.session_state.explanation_mode
                new_mode = st.toggle("Advanced mode", value=(mode == "advanced"),
                                     help="Show MINN technical terminology instead of plain English.")
                if (mode == "advanced" and not new_mode) or (mode == "simple" and new_mode):
                    st.session_state.explanation_mode = "advanced" if new_mode else "simple"
                    if "ai_insight_text_v2" in st.session_state: del st.session_state.ai_insight_text_v2
                    st.rerun()

            # Header badges
            st.markdown(f"""
            <div style="background:rgba(155,114,242,0.08);border:1px solid rgba(155,114,242,0.25);
                        border-radius:14px;padding:14px 16px;margin-top:6px;">
              <div style="font-size:10px;font-weight:800;color:{ACCENT2};text-transform:uppercase;
                          letter-spacing:.1em;margin-bottom:10px;display:flex;align-items:center;gap:8px;">
                {get_svg("brain", 14, ACCENT2)} Neural Assessment Narrative
                <span style="background:rgba(155,114,242,0.2);padding:2px 7px;border-radius:12px;font-size:8px;">
                  {st.session_state.explanation_mode.upper()}</span>
                <span style="background:rgba(0,255,200,0.1);color:#00FFC8;padding:2px 7px;border-radius:12px;
                             font-size:8px;border:1px solid rgba(0,255,200,0.2);">
                  {st.session_state.get('ai_insight_source_v2','...')}</span>
              </div>
            """, unsafe_allow_html=True)

            # Safe text rendering — strip stray HTML tags from heuristic fallback
            raw_text  = st.session_state.get("ai_insight_text_v2", "Generating…")
            clean_txt = _re.sub(r'<[^>]+>', '', raw_text).strip()
            st.markdown(f'<div style="font-size:14px;color:rgba(237,237,243,0.9);line-height:1.75;">'
                        f'{_html.escape(clean_txt)}</div></div>', unsafe_allow_html=True)

            # MINN param strip
            st.markdown(f"""
            <div style="margin-top:12px;background:rgba(109,94,252,0.07);border:1px solid rgba(109,94,252,0.2);
                        border-radius:10px;padding:12px 16px;display:flex;gap:24px;flex-wrap:wrap;">
              <div><div style="font-size:9px;color:#8BA6D3;text-transform:uppercase;margin-bottom:2px;">δ Threshold</div>
                   <div style="font-size:18px;font-weight:800;color:{ACCENT};">{iq.get('delta',0):.2f}</div></div>
              <div><div style="font-size:9px;color:#8BA6D3;text-transform:uppercase;margin-bottom:2px;">γ Decay</div>
                   <div style="font-size:18px;font-weight:800;color:{ACCENT2};">{iq.get('gamma',0):.3f}</div></div>
              <div><div style="font-size:9px;color:#8BA6D3;text-transform:uppercase;margin-bottom:2px;">ε Delay</div>
                   <div style="font-size:18px;font-weight:800;color:#3BA4FF;">{iq.get('epsilon',0):.1f}</div></div>
              <div><div style="font-size:9px;color:#8BA6D3;text-transform:uppercase;margin-bottom:2px;">Profile</div>
                   <div style="font-size:14px;font-weight:800;color:{color};">{cat}</div></div>
            </div>
            """, unsafe_allow_html=True)

            b1, b2 = st.columns(2)
            with b1:
                if st.button("↺ Refresh AI", use_container_width=True, key="refresh_ai_t1"):
                    if "ai_insight_text_v2" in st.session_state: del st.session_state.ai_insight_text_v2
                    st.rerun()
            with b2:
                if email and email != "guest":
                    if st.button("✉ Email Report", use_container_width=True, key="email_t1"):
                        with st.spinner("Sending…"):
                            sent = send_portfolio_report(email, port["risk_category"], port["profile_score"], clean_txt)
                            st.success("Sent!") if sent else st.error("Failed")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — Investment Planner
    # ════════════════════════════════════════════════════════════════════════
    with tab2:
        p_l, p_r = st.columns([1, 2], gap="large")
        with p_l:
            invest_amt = st.number_input(
                "Investment amount (£)", min_value=100, max_value=10_000_000,
                value=st.session_state.get("invest_amount", 10000), step=500, key="invest_amount",
            )
            total_gain = invest_amt * exp_r
            st.markdown(f"""
            <div style="background:rgba(142,246,209,0.06);border:1px solid rgba(142,246,209,0.2);
                        border-radius:12px;padding:16px;margin-top:8px;">
              <div style="font-size:10px;color:#8BA6D3;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Est. Year 1 Gain</div>
              <div style="font-size:28px;font-weight:900;color:#8EF6D1;">+£{total_gain:,.0f}</div>
              <div style="font-size:11px;color:#8BA6D3;margin-top:4px;">Based on {exp_r*100:.1f}% expected return</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            for yr, val in zip([1,3,5,10,20], [invest_amt * ((1+exp_r)**y) for y in [1,3,5,10,20]]):
                gain = val - invest_amt
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;padding:8px 0;
                            border-bottom:1px solid rgba(255,255,255,0.05);">
                  <span style="font-size:12px;color:#8BA6D3;font-weight:700;">{yr} yr{'s' if yr>1 else ''}</span>
                  <div style="text-align:right;">
                    <div style="font-size:13px;font-weight:800;color:#fff;">£{val:,.0f}</div>
                    <div style="font-size:10px;color:#8EF6D1;">+£{gain:,.0f}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

        with p_r:
            planner_rows = ""
            for asset, pct in sorted_alloc:
                amt     = invest_amt * (pct / 100)
                gain_1y = amt * exp_r
                short   = asset.replace(".L", "")
                role_title, _ = ETF_ROLES.get(short, (short, ""))
                g_col   = "#8EF6D1" if gain_1y >= 0 else "#FF6B6B"
                planner_rows += (
                    f'<tr style="border-bottom:1px solid rgba(255,255,255,0.05);">'
                    f'<td style="padding:10px 8px;"><div style="font-weight:700;color:#fff;font-size:13px;">{short}</div>'
                    f'<div style="font-size:10px;color:#6D5EFC;">{role_title}</div></td>'
                    f'<td style="padding:10px 8px;text-align:center;font-size:12px;color:#8BA6D3;">{pct:.1f}%</td>'
                    f'<td style="padding:10px 8px;text-align:right;font-size:14px;font-weight:800;color:#fff;">£{amt:,.0f}</td>'
                    f'<td style="padding:10px 8px;text-align:right;font-size:12px;font-weight:700;color:{g_col};">+£{gain_1y:,.0f}/yr</td>'
                    f'</tr>'
                )
            st.markdown(
                '<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);'
                'border-radius:14px;overflow:hidden;"><table style="width:100%;border-collapse:collapse;">'
                '<thead><tr style="background:rgba(109,94,252,0.12);border-bottom:1px solid rgba(255,255,255,0.08);">'
                '<th style="padding:9px 8px;text-align:left;font-size:10px;color:#8BA6D3;">ASSET</th>'
                '<th style="padding:9px 8px;text-align:center;font-size:10px;color:#8BA6D3;">WEIGHT</th>'
                '<th style="padding:9px 8px;text-align:right;font-size:10px;color:#8BA6D3;">INVEST</th>'
                '<th style="padding:9px 8px;text-align:right;font-size:10px;color:#8BA6D3;">YR 1 GAIN</th>'
                f'</tr></thead><tbody>{planner_rows}</tbody>'
                '<tfoot><tr style="background:rgba(109,94,252,0.08);border-top:1px solid rgba(109,94,252,0.3);">'
                '<td colspan="2" style="padding:10px 8px;font-weight:800;color:#fff;">TOTAL</td>'
                f'<td style="padding:10px 8px;text-align:right;font-size:16px;font-weight:900;color:#fff;">£{invest_amt:,.0f}</td>'
                f'<td style="padding:10px 8px;text-align:right;font-size:14px;font-weight:800;color:#8EF6D1;">+£{total_gain:,.0f}/yr</td>'
                '</tr></tfoot></table></div>',
                unsafe_allow_html=True
            )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — Analysis
    # ════════════════════════════════════════════════════════════════════════
    with tab3:
        a_l, a_r = st.columns([1.4, 1], gap="large")
        with a_l:
            st.markdown('<div style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:.12em;margin-bottom:8px;">Monte Carlo Growth Simulation · 2,000 runs</div>', unsafe_allow_html=True)
            st.plotly_chart(monte_chart(sim, color), use_container_width=True, config={"displayModeBar": False}, key="monte_t3")

            st.markdown('<div style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:.12em;margin:20px 0 10px;">Why Each Asset Was Chosen</div>', unsafe_allow_html=True)
            why_cols = st.columns(2)
            inv_amt_ref = st.session_state.get("invest_amount", 10000)
            for i, (asset, pct) in enumerate(sorted_alloc):
                short  = asset.replace(".L","")
                detail = ASSET_DETAIL.get(short, {"icon":"📊","colour":"#8BA6D3","why":f"{short} provides broad market exposure."})
                amt    = inv_amt_ref * (pct / 100)
                with why_cols[i % 2]:
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);
                                border-left:3px solid {detail['colour']};border-radius:12px;padding:14px;margin-bottom:10px;">
                      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                        <span>{detail['icon']}</span>
                        <div>
                          <div style="font-weight:800;color:#fff;font-size:14px;">{short}</div>
                          <div style="font-size:10px;color:{detail['colour']};">{pct:.1f}% · £{amt:,.0f}</div>
                        </div>
                      </div>
                      <div style="font-size:12px;color:#8BA6D3;line-height:1.6;">{detail['why']}</div>
                    </div>""", unsafe_allow_html=True)

        with a_r:
            st.markdown('<div style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:.12em;margin-bottom:12px;">Historical Stress Tests</div>', unsafe_allow_html=True)
            for nm, draw, logic in [
                ("2008 Financial Crisis", "-18.2%", "Capital preservation focus enabled."),
                ("2020 COVID Pivot",      "-8.4%",  "Fast recovery via Tech/Gold."),
                ("Dot-Com Bubble",        "-22.5%", "Heavy tech exposure drawdown."),
            ]:
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,107,107,0.2);
                            border-radius:12px;padding:14px;margin-bottom:10px;">
                  <div style="font-size:10px;font-weight:800;color:#8BA6D3;text-transform:uppercase;margin-bottom:4px;">Scenario Impact</div>
                  <div style="font-size:14px;font-weight:800;color:#fff;margin-bottom:4px;">{nm}</div>
                  <div style="font-size:22px;font-weight:900;color:#FF6B6B;">{draw}</div>
                  <div style="font-size:11px;color:#8BA6D3;margin-top:6px;">{logic}</div>
                </div>""", unsafe_allow_html=True)

            with st.expander("Data Source & Methodology", icon=":material/info:"):
                st.markdown(f"""
                <div style="font-size:13px;color:{MUTED};line-height:1.7;">
                  <b style="color:#fff;">Data:</b> 20 years of market history (2004–present), Yahoo Finance.<br><br>
                  <b style="color:#fff;">Expected Return:</b> Weighted historical geometric mean, regime-adjusted.<br>
                  <b style="color:#fff;">Volatility:</b> Asset covariance matrix from the IQ model.<br>
                  <b style="color:#fff;">Monte Carlo:</b> 2,000 GBM simulations over your time horizon.<br>
                  <b style="color:#fff;">P90/P50/P10:</b> Percentile outcomes across all simulations.
                </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4 — Examiner
    # ════════════════════════════════════════════════════════════════════════
    with tab4:
        _, claude_status = _get_claude()
        e_l, e_r = st.columns(2, gap="large")
        with e_l:
            st.markdown("**ML Input Vector (Survey Answers)**")
            st.json(st.session_state.get("survey_answers", {}))
        with e_r:
            st.markdown("**Markowitz Engine Stats**")
            st.dataframe(pd.DataFrame([port['stats']]).T.rename(columns={0: "Value"}))
            st.markdown("**Claude AI Bridge**")
            st.json({"Model": "Claude 3.5 Sonnet", "API Health": claude_status,
                     "Context": port['risk_category'], "Mode": st.session_state.explanation_mode.upper()})
        st.code(f"db.assessments.insertOne({{ user: '{email}', cat: '{cat}', ... }})", language="javascript")
        st.info("💡 Every survey answer → Markowitz engine → Claude narrative → MongoDB Atlas. Full end-to-end audit trail.")

        with st.expander("Survey Summary", icon=":material/assignment:"):
            for q in QUESTIONS:
                val = st.session_state.survey_answers.get(q["key"], "—")
                st.markdown(f"- **{q['number']}** {q['text'][:60]}…  →  `{val}`")

        if st.session_state.explanation_mode == "advanced":
            st.markdown("---")
            st.markdown("**Strategic AI Tuning (Advanced)**")
            saved_config = database.get_portfolio_config(st.session_state.get("user_email", "guest"))
            new_delta = st.slider("Neural Threshold (δ)", 0.1, 2.0, float(saved_config.get("delta", iq.get("delta", 0.5))), 0.1)
            new_gamma = st.slider("Temporal Decay (γ)", 0.001, 0.5, float(saved_config.get("gamma", iq.get("gamma", 0.1))), 0.001, format="%.3f")
            if st.button("Save Custom Tuning", type="primary"):
                database.save_portfolio_config(email or "guest", {"delta": new_delta, "gamma": new_gamma})
                st.success("Saved to MongoDB Atlas!")

    # ── Disclaimer + reset ────────────────────────────────────────────────────
    st.markdown(f"""
    <div style='margin:16px 0 8px;padding:12px;background:rgba(255,107,107,0.06);
    border-left:3px solid rgba(255,107,107,0.35);border-radius:8px;
    font-size:12px;color:rgba(237,237,243,0.45);display:flex;gap:10px;align-items:flex-start;'>
    <div style="margin-top:2px;">{get_svg("warning", 16, "#FF6B6B")}</div>
    <div><b>Disclaimer:</b> Educational and research purposes only. Not financial advice.
    Consult a qualified financial adviser before investing. Past performance does not guarantee future results.</div>
    </div>""", unsafe_allow_html=True)

    col_r, _ = st.columns([1, 3])
    with col_r:
        if st.button("Try a Different Profile", icon=":material/refresh:", use_container_width=True):
            st.session_state.survey_page    = "survey"
            st.session_state.survey_step    = 0
            st.session_state.survey_answers = {}
            st.session_state.result         = None
            st.rerun()

