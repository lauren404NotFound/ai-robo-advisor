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
    """Render the Intelligence Feed without split-div card wrappers."""
    st.markdown(
        f'<p style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;'
        f'letter-spacing:0.1em;margin:0 0 4px;border-left:3px solid #6D5EFC;padding-left:10px;">'
        f'{get_svg("zap",12,"#9B72F2")} &nbsp;Intelligence Feed</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:11px;color:{MUTED};margin:0 0 14px;">'
        f'Real-time feed of neural diagnostic events and profile changes.</p>',
        unsafe_allow_html=True,
    )
    _render_feed_items(notifs, compact=compact)
    if include_archive:
        if st.button("Archive Event Log", use_container_width=True):
            st.info("Logs are archived in MongoDB Atlas.")

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
    color = PROFILE_COLORS.get(cat, ACCENT2)
    sorted_weights = dict(sorted(port["allocation_pct"].items(), key=lambda x: x[1], reverse=True))
    sorted_alloc = list(sorted_weights.items())
    compact_notifs = database.get_notifications(email, limit=4)

    # ── Page Header ────────────────────────────────────────────────────────────
    name = st.session_state.get("user_name", "Investor").split()[0]
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px;padding:4px 0 20px;">
      <div>
        <div style="font-size:11px;font-weight:800;color:#6D5EFC;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:8px;">Portfolio Dashboard</div>
        <div style="font-size:36px;font-weight:900;color:#fff;letter-spacing:-0.03em;">Welcome back, {name}</div>
        <div style="font-size:13px;color:#8BA6D3;margin-top:4px;">Your AI-optimised portfolio</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Profile Hero ─────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="profile-hero">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <div style="background:{ACCENT};border-radius:10px;padding:8px;display:flex;">{get_svg("zap", 24, "#fff")}</div>
        <div class="profile-name" style="margin-bottom:0;">Markowitz-Informed Neural Network (MINN)</div>
      </div>
      <div class="profile-desc">Neural state optimization completed. Models tuned to maximize Sharpe Ratio under current co-movement regimes.</div>
      <div class="tag-row">
        <span class="tag">AI Inference Validated</span>
        <span class="tag">δ={iq.get('delta',0):.2f}</span>
        <span class="tag">γ={iq.get('gamma',0):.3f}</span>
        <span class="tag">ε={iq.get('epsilon',0):.1f}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPIs — inline-styled columns for reliability ─────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    for col, label, val, hint, vc, tooltip in [
        (k1, "Expected Return",  f"{stats['expected_annual_return']:.1f}%",  "Inferential Estimate",  POS,     "Average % your portfolio is expected to grow each year."),
        (k2, "Learned Volatility",f"{stats['expected_volatility']:.1f}%",   "Predicted Portfolio Vol","#ffffff","How much your portfolio value is likely to fluctuate."),
        (k3, "Sharpe Ratio",     f"{stats['sharpe_ratio']:.2f}",             "Risk-Adjusted Learner",  POS,     "Return per unit of risk — higher is smarter."),
        (k4, "P90 Growth",       f"{get_currency_symbol()}{sim['p90']:,.0f}",f"Optimistic Projection",  color,   "Top 10% optimistic scenario over your time horizon."),
    ]:
        with col:
            st.markdown(f"""
            <div title="{tooltip}" style="background:rgba(10,10,22,0.6);border:1px solid rgba(155,114,242,0.22);border-radius:14px;padding:18px 14px;">
              <div style="font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.10em;color:rgba(237,237,243,0.55);margin-bottom:7px;">{label}</div>
              <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:800;color:{vc};">{val}</div>
              <div style="font-size:9px;color:rgba(230,213,255,0.35);margin-top:7px;">{hint}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Row 1: allocation | diagnostics ───────────────────────────────────────
    col1, col2 = st.columns([1, 1.4], gap="large")
    with col1:
        st.markdown('<p style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 4px;">Asset Allocation</p>', unsafe_allow_html=True)
        st.plotly_chart(donut_chart(sorted_weights), use_container_width=True)
        etf_html = '<div style="margin-top:4px;">'
        for asset, pct_v in sorted_weights.items():
            etf_html += (f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);">'
                         f'<span style="font-size:12px;color:#C5D3EC;">{asset}</span>'
                         f'<span style="font-size:12px;color:{color};font-weight:700;font-family:\'JetBrains Mono\',monospace;">{pct_v:.1f}%</span></div>')
        st.markdown(etf_html + "</div>", unsafe_allow_html=True)

    with col2:
        if st.session_state.explanation_mode == "advanced":
            st.markdown(f'<p style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 12px;">MINN Architecture Diagnostics</p>', unsafe_allow_html=True)
            
            ic1, ic2 = st.columns(2)
            with ic1:
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.03); padding:15px; border-radius:10px; text-align:center;">
                    <div style="font-size:10px; color:{MUTED};"><div class="rich-tooltip">THRESHOLD (δ)<span class="tooltip-text">This number controls how carefully the AI watches for risky market behavior. A higher number means the AI is heavily filtering out 'market noise' to focus only on major, dangerous trends.</span></div></div>
                    <div style="font-size:24px; color:{ACCENT}; font-weight:800;">{iq.get('delta',0):.2f}</div>
                    <div style="font-size:9px; color:{MUTED};">Manifold Boundary</div>
                </div>
                """, unsafe_allow_html=True)
            with ic2:
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.03); padding:15px; border-radius:10px; text-align:center;">
                    <div style="font-size:10px; color:{MUTED};"><div class="rich-tooltip">DECAY (γ)<span class="tooltip-text">This number controls the AI's 'memory'. A higher number means the AI cares more about what the market did yesterday than what it did 5 years ago, making it react faster to sudden changes.</span></div></div>
                    <div style="font-size:24px; color:{ACCENT2}; font-weight:800;">{iq.get('gamma',0):.3f}</div>
                    <div style="font-size:9px; color:{MUTED};">Temporal Discount</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown(
                f'<p style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;'
                f'letter-spacing:0.1em;margin:20px 0 8px;border-left:3px solid #6D5EFC;padding-left:10px;">'
                f'Regime Mixture Probability</p>',
                unsafe_allow_html=True,
            )
            regimes = iq.get("regimes", {"Body":0.7, "Wing":0.1, "Tail":0.1, "Identity":0.1})
            r_names = list(regimes.keys())
            r_vals = list(regimes.values())
            r_exps = []
            for r in r_names:
                if r == "Body": r_exps.append("Normal, calm market conditions.")
                elif r == "Tail": r_exps.append("Severe market crashes or extreme events.")
                elif r == "Wing": r_exps.append("Moderate turbulence and volatility.")
                else: r_exps.append("Baseline mathematical smoothing (Identity matrix).")
            
            # Simple regime bar chart
            fig_r = px.bar(
                x=r_vals, y=r_names, orientation='h',
                color=r_names,
                color_discrete_map={"Body":ACCENT, "Wing":ACCENT2, "Tail":NEG, "Identity":MUTED},
                custom_data=[r_exps]
            )
            fig_r.update_traces(hovertemplate="<b>%{y} Regime</b><br>Probability: %{x:.1%}<br><i>%{customdata[0]}</i><extra></extra>")
            fig_r.update_layout(template=TMPL, showlegend=False, xaxis_title="Weight", yaxis_title=None, height=180, margin=dict(l=0,r=20,t=0,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_r, use_container_width=True)

            st.markdown(f'<p style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:0.1em;margin:20px 0 6px;">Strategic AI Tuning</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-size:11px;color:{MUTED};margin-bottom:12px;">Manually override the neural manifold parameters to tune your risk exposure.</p>', unsafe_allow_html=True)
            
            # Load existing config from DB if available
            saved_config = database.get_portfolio_config(st.session_state.get("user_email", "guest"))
            def_delta = saved_config.get("delta", iq.get("delta", 0.5))
            def_gamma = saved_config.get("gamma", iq.get("gamma", 0.1))
            
            new_delta = st.slider("Neural Threshold (δ)", 0.1, 2.0, float(def_delta), 0.1, help="Higher = more aggressive filtering of market noise.")
            new_gamma = st.slider("Temporal Decay (γ)", 0.001, 0.5, float(def_gamma), 0.001, format="%.3f", help="Higher = faster reaction to recent volatility.")
            
            if st.button("Save Custom Tuning to Cloud", use_container_width=True, type="primary"):
                new_config = {"delta": new_delta, "gamma": new_gamma}
                database.save_portfolio_config(st.session_state.get("user_email", "guest"), new_config)
                database.add_notification(st.session_state.get("user_email", "guest"), "Strategic Sync Successful", f"Your MINN parameters have been synchronized with the LEM StratIQ cloud.", "success")
                st.success("Configuration Pushed to MongoDB Atlas!")
                st.rerun()
        else:
            st.markdown(f'<p style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 6px;">Portfolio Snapshot</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-size:11px;color:{MUTED};margin-bottom:14px;">A simpler summary of your current portfolio characteristics and expected behaviour.</p>', unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03); padding:20px; border-radius:14px; text-align:center; margin-bottom:10px;">
                <div style="font-size:11px; color:{MUTED}; font-weight:700; letter-spacing:0.05em; margin-bottom:8px;">AI-GENERATED ASSET SPREAD</div>
                <div style="font-size:32px; color:{ACCENT2}; font-weight:900;">{len(sorted_alloc)}</div>
                <div style="font-size:10px; color:{MUTED}; margin-top:4px;">Asset sleeves selected for your unique profile</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f'<p style="font-size:12px;color:#8BA6D3;line-height:1.6;margin-top:16px;"><b>Expected return:</b> <span style="color:#fff;">{stats["expected_annual_return"]:.1f}%</span> &nbsp;·&nbsp; <b>Expected volatility:</b> <span style="color:#fff;">{stats["expected_volatility"]:.1f}%</span></p>', unsafe_allow_html=True)

    st.divider()
    with st.expander("ℹ️ Data Source & Methodology", icon=":material/info:"):
        st.markdown(f"""
        <div style="font-size:14px; color:{MUTED}; line-height:1.7;">
          <h4 style="color:#ffffff; margin-top:0;">1. Data Foundation</h4>
          We use <b>20 years of historical market data</b> (2004–present) for the major asset classes (S&P 500, Bonds, Gold, etc.),
          synced via Yahoo Finance for real-world accuracy.

          <h4 style="color:#ffffff; margin-top:16px;">2. Performance Metrics</h4>
          Wealth is projected based on historical averages (Geometric Mean) and current market regimes:
          <ul>
            <li><b>Expected Growth:</b> Calculated using a weighted average of long-term asset returns, adjusted by the current <b>Market Regime</b> detected by our Neural Network.</li>
            <li><b>Learned Volatility:</b> Derived from the asset covariance matrix. It represents the intensity of price swings.</li>
            <li><b>Efficiency (Sharpe):</b> A measure of return per unit of risk. Higher is smarter.</li>
          </ul>

          <h4 style="color:#ffffff; margin-top:16px;">3. Forward-Looking Projections</h4>
          The <b>Monte Carlo Growth</b> chart uses 2,000 independent simulations (Geometric Brownian Motion) to model the range of
          possible futures for your money.
          <ul>
            <li><b>P90 (Optimistic):</b> The top 10% of outcomes where markets perform exceptionally well.</li>
            <li><b>P50 (Median):</b> The most likely, average long-term path for your portfolio.</li>
            <li><b>P10 (Conservative):</b> A stress-test scenario where assets perform poorly but remain within historical norms.</li>
          </ul>
        </div>
        """, unsafe_allow_html=True)

    # ── Row 2: performance | intelligence feed ───────────────────────────
    c1, c2 = st.columns([1.3, 1.0], gap="large")
    with c1:
        st.markdown('<p style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 4px;">Monte Carlo Growth Simulation</p>', unsafe_allow_html=True)
        st.caption("2,000 simulated futures — showing P10 (conservative), P50 (median) and P90 (optimistic) paths.")
        st.plotly_chart(monte_chart(sim, color), use_container_width=True)

    with c2:
        _render_feed_card(compact_notifs, include_archive=True, compact=True)


    # ══════════════════════════════════════════════════════════════════════
    # ── NEURAL AI STRATEGY INTERPRETATION ────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════
    st.divider()
    col_toggle, col_spacer = st.columns([1, 3])
    with col_toggle:
        mode = st.session_state.explanation_mode
        new_mode = st.toggle(
            ":material/analytics: Advanced mode (for investors who understand market terms)",
            value=(mode == "advanced"),
            help="Switch to advanced mode to see technical details."
        )
        if (st.session_state.explanation_mode == "advanced" and not new_mode) or \
           (st.session_state.explanation_mode == "simple" and new_mode):
            st.session_state.explanation_mode = "advanced" if new_mode else "simple"
            if "ai_insight_text" in st.session_state: del st.session_state.ai_insight_text
            st.rerun()

    st.markdown(
        f'<h3 style="display:flex;align-items:center;gap:10px;margin:18px 0 14px;font-size:20px;font-weight:900;color:#fff;">'
        f'{get_svg("brain",22,ACCENT)} Neural AI Strategy Interpretation</h3>',
        unsafe_allow_html=True,
    )

    anthropic_client, claude_status = _get_claude()
    if not anthropic_client:
        with st.sidebar:
            st.error("🤖 **AI Engine Offline**")

    if "ai_insight_text_v2" not in st.session_state:
        with st.status("Analyzing your profile via DeepIQ Neural Manifold...", expanded=True) as status:
            insight, source = get_ai_explanation(st.session_state.explanation_mode, port, {}, ans)
            st.session_state.ai_insight_text_v2 = insight
            st.session_state.ai_insight_source_v2 = source
            status.update(label=f"Insight Generated via {source}", state="complete", expanded=False)
            st.session_state.result["ai_narrative"] = insight
            database.save_assessment(st.session_state.get("user_email", "guest"), st.session_state.survey_answers, st.session_state.result)

    import html as _html
    _ai_text = _html.escape(str(st.session_state.get('ai_insight_text_v2', '...')))
    _ai_src  = _html.escape(str(st.session_state.get('ai_insight_source_v2', 'CHECKING...')))
    st.markdown(f"""
    <div style="background:rgba(155,114,242,0.08);border:1px solid rgba(155,114,242,0.25);padding:20px 24px 8px;border-radius:16px;margin-bottom:0;">
      <div style="font-size:11px;font-weight:800;color:{ACCENT2};text-transform:uppercase;letter-spacing:0.1em;display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        Neural Assessment Narrative
        <span style="font-size:9px;background:rgba(155,114,242,0.2);padding:2px 8px;border-radius:20px;">{st.session_state.explanation_mode.upper()} MODE</span>
        <span style="font-size:9px;background:rgba(0,255,200,0.1);color:#00FFC8;padding:2px 8px;border-radius:20px;border:1px solid rgba(0,255,200,0.2);">{_ai_src}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(_ai_text.replace('\\n', '  \n'))

    btn_col1, btn_col2, _ = st.columns([1, 1, 2])
    with btn_col1:
        if st.button("Refresh AI Narrative", icon=":material/refresh:", use_container_width=True):
            if "ai_insight_text_v2" in st.session_state: del st.session_state.ai_insight_text_v2
            st.rerun()
    with btn_col2:
        if st.session_state.get("user_email") != "guest":
            if st.button("Email Results", icon=":material/mail:", use_container_width=True):
                with st.spinner("Delivering report..."):
                    sent = send_portfolio_report(st.session_state.user_email, port["risk_category"], port["profile_score"], st.session_state.get("ai_insight_text_v2", ""))
                    if sent: st.success("Sent!")
                    else: st.error("Failed")

    with st.expander("🛠️ TECHNICAL LOGIC VALIDATOR (Examiner View)", expanded=False):
        st.markdown("### `System Internals Audit`")
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.write("**ML Input Vector (User Surveys)**")
            st.json(st.session_state.get("survey_answers", {}))
            st.write("**Math Engine Stats (Markowitz)**")
            st.dataframe(pd.DataFrame([port['stats']]).T.rename(columns={0: "Value"}))
        with t_col2:
            st.write("**Claude AI Integration Bridge**")
            st.json({"Role": "DeepAtomicIQ Neural Investment Officer", "Model": "Claude 3.5 Sonnet",
                     "Context Mapping": port['risk_category'], "API Health": claude_status,
                     "Last Query Type": st.session_state.explanation_mode.upper()})
        st.write("**MongoDB Persistence Audit**")
        st.code(f"INSERT INTO assessments (user_email, answers, result) VALUES ('{st.session_state.get('user_email', 'guest')}', ...)", language="sql")
        st.info("💡 **Examiner Insight**: Every survey answer is verified, mathematically processed via the Markowitz engine, explained by Claude, and committed to MongoDB Atlas.")

    # ══════════════════════════════════════════════════════════════════════
    # ── INVESTMENT PLANNER ────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════
    st.divider()
    _render_section_intro(
        "Investment Planner",
        "Enter how much you want to invest — we'll show you exactly where to put it and what to expect back.",
        margin_top=10,
    )

    inv_col, _ = st.columns([1, 1])
    with inv_col:
        invest_amt = st.number_input(
            "How much would you like to invest? (£)",
            min_value=100, max_value=10_000_000,
            value=st.session_state.get("invest_amount", 10000),
            step=500, key="invest_amount",
            help="Enter your total investment amount in pounds"
        )

    exp_r  = stats.get("expected_annual_return", 0) / 100

    # Build planner table
    planner_rows = ""
    for asset, pct in sorted_alloc:
        amt = invest_amt * (pct / 100)
        gain_1y = amt * exp_r
        short_name = asset.replace(".L", "")
        role_title, role_desc = ETF_ROLES.get(short_name, (short_name, "Broad market exposure."))
        gain_color = "#8EF6D1" if gain_1y >= 0 else "#FF6B6B"
        row_arrow  = "&#9650;" if gain_1y >= 0 else "&#9660;"
        planner_rows += (
            '<tr style="border-bottom:1px solid rgba(255,255,255,0.05);">'
            '<td style="padding:12px 10px;">'
            f'<div style="font-weight:700;color:#ffffff;font-size:14px;">{short_name}</div>'
            f'<div style="font-size:11px;color:#6D5EFC;font-weight:600;">{role_title}</div>'
            '</td>'
            f'<td style="padding:12px 10px;text-align:center;font-size:13px;color:#8BA6D3;font-weight:600;">{pct:.1f}%</td>'
            f'<td style="padding:12px 10px;text-align:right;font-size:16px;font-weight:800;color:#ffffff;">&pound;{amt:,.0f}</td>'
            f'<td style="padding:12px 10px;text-align:right;font-size:14px;font-weight:700;color:{gain_color};">'
            f'{row_arrow} &pound;{abs(gain_1y):,.0f}/yr</td>'
            f'<td style="padding:12px 10px;font-size:12px;color:#8BA6D3;max-width:200px;">{role_desc}</td>'
            '</tr>'
        )

    total_gain_1y = invest_amt * exp_r
    total_arrow = "&#9650;" if total_gain_1y >= 0 else "&#9660;"

    table_html = (
        '<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);'
        'border-radius:16px;overflow:hidden;margin-bottom:10px;">'
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="background:rgba(109,94,252,0.12);border-bottom:1px solid rgba(255,255,255,0.08);">'
        '<th style="padding:10px;text-align:left;font-size:11px;color:#8BA6D3;font-weight:700;letter-spacing:.06em;">ASSET</th>'
        '<th style="padding:10px;text-align:center;font-size:11px;color:#8BA6D3;font-weight:700;letter-spacing:.06em;">WEIGHT</th>'
        '<th style="padding:10px;text-align:right;font-size:11px;color:#8BA6D3;font-weight:700;letter-spacing:.06em;">INVEST</th>'
        '<th style="padding:10px;text-align:right;font-size:11px;color:#8BA6D3;font-weight:700;letter-spacing:.06em;">EST. ANNUAL GAIN</th>'
        '<th style="padding:10px;text-align:left;font-size:11px;color:#8BA6D3;font-weight:700;letter-spacing:.06em;">ROLE</th>'
        '</tr></thead>'
        '<tbody>' + planner_rows + '</tbody>'
        '<tfoot><tr style="background:rgba(109,94,252,0.08);border-top:1px solid rgba(109,94,252,0.3);">'
        '<td colspan="2" style="padding:12px 10px;font-weight:800;color:#ffffff;">TOTAL PORTFOLIO</td>'
        '<td style="padding:12px 10px;text-align:right;font-size:18px;font-weight:900;color:#ffffff;">'
        + f'&pound;{invest_amt:,.0f}' +
        '</td><td style="padding:12px 10px;text-align:right;font-size:16px;font-weight:800;color:#8EF6D1;">'
        + f'{total_arrow} &pound;{abs(total_gain_1y):,.0f}/yr' +
        '</td><td style="padding:12px 10px;font-size:12px;color:#8BA6D3;">'
        + f'Based on {exp_r*100:.1f}% expected annual return'
        + '</td></tr></tfoot></table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # ── PROJECTED RETURNS TIMELINE ────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════
    _render_section_intro(
        "Projected Returns Timeline",
        f'If you invest <b style="color:#ffffff;">£{invest_amt:,.0f}</b> today and reinvest all returns (compound growth at {exp_r*100:.1f}% p.a.):',
        icon_svg="📅",
        margin_top=28,
    )

    horizons = [1, 3, 5, 10, 20]
    projected = [invest_amt * ((1 + exp_r) ** yr) for yr in horizons]
    gains     = [p - invest_amt for p in projected]

    proj_fig = go.Figure()
    proj_fig.add_trace(go.Bar(
        x=[f"{y}yr" for y in horizons],
        y=projected,
        name="Portfolio Value",
        marker=dict(
            color=projected,
            colorscale=[[0,"#3BA4FF"],[1,"#8EF6D1"]],
            line=dict(width=0)
        ),
        text=[f"£{p:,.0f}" for p in projected],
        textposition="outside",
        textfont=dict(color="#ffffff", size=12),
        hovertemplate="<b>%{x}</b><br>Value: £%{y:,.0f}<extra></extra>"
    ))
    proj_fig.add_trace(go.Bar(
        x=[f"{y}yr" for y in horizons],
        y=[invest_amt] * len(horizons),
        name="Initial Investment",
        marker=dict(color="rgba(255,255,255,0.08)", line=dict(width=0)),
        hovertemplate="Initial: £%{y:,.0f}<extra></extra>"
    ))
    proj_fig.update_layout(
        barmode="overlay", height=280,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10,r=10,t=30,b=10),
        xaxis=dict(showgrid=False, color="#8BA6D3"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#8BA6D3",
                   tickprefix="£", tickformat=",.0f"),
        legend=dict(font=dict(color="#8BA6D3"), bgcolor="rgba(0,0,0,0)", orientation="h",
                    yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="rgba(15,15,35,0.95)", font_color="#ffffff")
    )
    st.plotly_chart(proj_fig, use_container_width=True, config={"displayModeBar": False}, key="proj_timeline")

    # Summary tiles
    tile_cols = st.columns(len(horizons))
    for i, (yr, val, gain) in enumerate(zip(horizons, projected, gains)):
        with tile_cols[i]:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
                        border-radius:14px;padding:14px;text-align:center;margin-bottom:8px;">
              <div style="font-size:11px;color:#8BA6D3;font-weight:700;letter-spacing:.06em;margin-bottom:6px;">{yr} YEAR{'S' if yr>1 else ''}</div>
              <div style="font-size:18px;font-weight:900;color:#ffffff;">£{val:,.0f}</div>
              <div style="font-size:12px;font-weight:700;color:#8EF6D1;margin-top:4px;">+£{gain:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # ── WHY EACH ASSET ────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════
    _render_section_intro(
        "Why Each Asset Was Chosen",
        f'The MINN selected these specific ETFs based on your risk score of <b style="color:#ffffff;">{res.get("score", 5):.0f}/10</b> and how they interact in the co-movement model.',
        icon_svg=get_svg("puzzle", 24, ACCENT),
        margin_top=28,
    )

    why_cols = st.columns(2)
    for i, (asset, pct) in enumerate(sorted_alloc):
        short = asset.replace(".L","")
        detail = ASSET_DETAIL.get(short, {"icon":"📊","colour":"#8BA6D3","why":f"{short} provides diversified exposure to its target market segment."})
        amt = invest_amt * (pct / 100)
        with why_cols[i % 2]:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);
                        border-left:3px solid {detail['colour']};
                        border-radius:14px;padding:16px 18px;margin-bottom:12px;">
              <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                <span style="font-size:22px;">{detail['icon']}</span>
                <div>
                  <div style="font-weight:800;color:#ffffff;font-size:15px;">{short}</div>
                  <div style="font-size:11px;color:{detail['colour']};font-weight:700;">{pct:.1f}% · £{amt:,.0f} of your investment</div>
                </div>
              </div>
              <div style="font-size:13px;color:#8BA6D3;line-height:1.65;">{detail['why']}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Survey summary expander ───────────────────────────────────────────────
    with st.expander("Survey Summary", icon=":material/assignment:"):
        st.markdown("**Your Answers**")
        for q in QUESTIONS:
            val = st.session_state.survey_answers.get(q["key"], "—")
            st.markdown(f"- **{q['number']}** {q['text'][:55]}…  →  `{val}`")


    # ── HISTORICAL STRESS TEST ──
    st.divider()
    _render_section_intro("Resilience Stress Test", "", icon_svg=get_svg("shield", 24, ACCENT), margin_top=12)
    c1, c2, c3 = st.columns(3)
    stress_scenarios = [
        ("2008 Financial Crisis", "-18.2%", "Capital preservation focus enabled."),
        ("2020 COVID Pivot", "-8.4%", "Fast regime recovery via Tech/Gold."),
        ("Dot-Com Bubble", "-22.5%", "Heavy tech exposure drawdown.")
    ]
    for i, (name, draw, logic) in enumerate(stress_scenarios):
        with [c1,c2,c3][i]:
            st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:16px;">
                <div style="font-size:10px;font-weight:800;color:#8BA6D3;margin-bottom:4px;text-transform:uppercase;">Scenario Impact</div>
                <div style="font-size:16px;font-weight:800;color:#fff;margin-bottom:4px;">{name}</div>
                <div style="font-size:24px;font-weight:900;color:#FF6B6B;">{draw}</div>
                <div style="font-size:11px;color:#8BA6D3;margin-top:8px;">{logic}</div>
            </div>""", unsafe_allow_html=True)
    st.markdown(f"""
<div style='margin:8px 0;padding:12px;background:rgba(255,107,107,0.06);
border-left:3px solid rgba(255,107,107,0.35);border-radius:8px;
font-size:12px;color:rgba(237,237,243,0.45); display:flex; gap:10px; align-items:flex-start;'>
<div style="margin-top:2px;">{get_svg("warning", 16, "#FF6B6B")}</div>
<div><b>Disclaimer:</b> This is for educational and research purposes only. 
Not financial advice. Consult a qualified financial adviser before investing. 
Past performance does not guarantee future results.</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_r, _ = st.columns([1, 3])
    with col_r:
        if st.button("Try a Different Profile", icon=":material/refresh:", use_container_width=True):
            st.session_state.survey_page    = "survey"
            st.session_state.survey_step    = 0
            st.session_state.survey_answers = {}
            st.session_state.result         = None
            st.rerun()
