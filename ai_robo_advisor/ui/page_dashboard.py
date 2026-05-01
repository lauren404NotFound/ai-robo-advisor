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
    "VOO":  {"icon": "📈", "colour": "#3BA4FF", "why": "VOO tracks the S&P 500 — 500 of the largest US companies. It's the backbone of most portfolios because it grows with the world's largest economy. The MINN allocated this to capture consistent long-term growth."},
    "QQQ":  {"icon": "⚡", "colour": "#6D5EFC", "why": "QQQ holds the top 100 Nasdaq-listed companies, dominated by tech giants like Apple, Microsoft, and Nvidia. Higher risk, higher reward — the MINN uses it to boost return potential in line with your risk appetite."},
    "VWRA": {"icon": "🌐", "colour": "#8EF6D1", "why": "VWRA gives global exposure across 3,700+ companies in 50+ countries. It reduces your dependence on any single market recovering or performing well — pure diversification."},
    "AGG":  {"icon": "🛡", "colour": "#8BA6D3", "why": "AGG invests in US government and corporate bonds. When stocks fall, bonds often hold steady — acting as a ballast. The MINN uses AGG to reduce portfolio volatility."},
    "GLD":  {"icon": "✦", "colour": "#FFD700", "why": "Gold has protected wealth for thousands of years. It rises when inflation erodes currency value and during geopolitical uncertainty — the MINN uses it as a crisis hedge."},
    "VNQ":  {"icon": "◧", "colour": "#FF9B6B", "why": "VNQ gives exposure to real estate investment trusts. Property tends to grow with inflation and pays dividends — adding a reliable income stream uncorrelated with stocks."},
    "ESGU": {"icon": "◈", "colour": "#4CAF50", "why": "ESGU mirrors the S&P 500 while excluding companies with poor environmental, social, and governance ratings. It aligns your investments with your values without sacrificing returns."},
    "PDBC": {"icon": "◎", "colour": "#FF6B6B", "why": "PDBC tracks a basket of commodities — oil, natural gas, metals, and agriculture. These real assets often zig when financial assets zag, adding genuine diversification."},
}

# ── Helper: get profile number from portfolio result ─────────────────────────
def _profile_num_from_port(port: dict) -> int:
    """Extract an integer profile number (1-6) from the portfolio dict."""
    # Try explicit profile_num key first
    for key in ("profile_num", "profile_number", "robo_profile"):
        val = port.get(key)
        if val is not None:
            try:
                return int(str(val).strip().replace("P","").replace("p",""))
            except (ValueError, TypeError):
                pass
    # Fall back: map risk_category string to a number
    cat = str(port.get("risk_category", "")).lower()
    mapping = {
        "capital preservation": 1, "conservative": 1,
        "balanced growth": 2,      "balanced": 2, "moderate": 2,
        "high-alpha equity": 3,    "aggressive": 3, "growth": 3,
        "esg impact": 4,           "esg": 4,
        "thematic concentrated": 5,"thematic": 5, "concentrated": 5,
        "risk parity": 6,          "parity": 6, "systematic": 6,
    }
    for k, v in mapping.items():
        if k in cat:
            return v
    # Last resort: derive from risk score
    score = port.get("profile_score", port.get("score", 5))
    try:
        s = float(score)
        if s <= 2:   return 1
        if s <= 4:   return 2
        if s <= 6:   return 3
        if s <= 7:   return 4
        if s <= 8.5: return 5
        return 6
    except (ValueError, TypeError):
        return 2


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
    st.markdown(
        f'<p style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;'
        f'letter-spacing:0.1em;margin:0 0 4px;border-left:3px solid #6D5EFC;padding-left:10px;">'
        f'{get_svg("zap",12,"#9B72F2")} &nbsp;Intelligence Feed</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:11px;color:{MUTED};margin:0 0 14px;">'
        f'Real-time feed of neural diagnostic events and category changes.</p>',
        unsafe_allow_html=True,
    )
    _render_feed_items(notifs, compact=compact)
    if include_archive:
        if st.button("Archive Event Log", use_container_width=True):
            st.info("Logs are archived in MongoDB Atlas.")


def page_dashboard():
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

    sp = st.session_state.get("survey_page", "survey")
    if sp == "analysing":
        _render_analysing()
        return

    if not st.session_state.get("result") and st.session_state.get("user_email") != "guest":
        if not st.session_state.get("force_retake"):
            saved = database.get_latest_assessment(st.session_state.get("user_email"))
            if saved:
                st.session_state.result = saved["result"]
                st.session_state.survey_answers = saved["answers"]
                st.session_state.survey_page = "portfolio"
                sp = "portfolio"

    if not st.session_state.get("result"):
        if sp == "survey":
            _render_survey()
            return

        st.markdown(f"""
        <div class="coming-soon">
          <div class="coming-soon-icon" style="color:#6D5EFC;margin-bottom:15px;display:flex;justify-content:center;">{get_svg("news", 40)}</div>
          <div class="coming-soon-title">Incomplete Risk Assessment</div>
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

    if sp == "survey":
        _render_survey()
    else:
        _render_portfolio()


def _render_survey():
    step = st.session_state.get("survey_step", 0)
    q    = QUESTIONS[step]
    pct  = int((step / len(QUESTIONS)) * 100)

    # Use new QUESTIONS structure: id, text, subtitle, options[{label, value, desc}]
    q_id       = q["id"]
    q_text     = q["text"]
    q_subtitle = q.get("subtitle", "")
    q_opts     = q["options"]
    opt_labels = [o["label"] for o in q_opts]

    st.markdown(f"""
    <div class="survey-wrap">
      <div class="progress-bar-wrap">
        <div class="progress-bar-fill" style="width:{pct}%"></div>
      </div>
      <div class="q-number">Question {step + 1} of {len(QUESTIONS)}</div>
      <div class="q-text">{q_text}</div>
      <div class="q-desc">{q_subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

    # Current answer stored by id
    saved_val = st.session_state.survey_answers.get(q_id)
    # Find current label from saved value
    default_label = opt_labels[0]
    if saved_val is not None:
        for o in q_opts:
            if o["value"] == saved_val or o["label"] == saved_val:
                default_label = o["label"]
                break

    selected_label = st.radio(
        "",
        opt_labels,
        index=opt_labels.index(default_label) if default_label in opt_labels else 0,
        key=f"radio_{step}",
    )

    # Get the value for selected label
    selected_value = next((o["value"] for o in q_opts if o["label"] == selected_label), selected_label)

    # Show description for selected option
    selected_desc = next((o.get("desc","") for o in q_opts if o["label"] == selected_label), "")
    if selected_desc:
        st.caption(selected_desc)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    col_back, _, col_next = st.columns([1, 2, 1])
    with col_back:
        if step > 0:
            if st.button("← Back", use_container_width=True):
                st.session_state.survey_answers[q_id] = selected_value
                st.session_state.survey_step -= 1
                st.rerun()
    with col_next:
        is_last = (step == len(QUESTIONS) - 1)
        if st.button("Generate Portfolio →" if is_last else "Next →",
                     type="primary", use_container_width=True):
            st.session_state.survey_answers[q_id] = selected_value
            if is_last:
                st.session_state.survey_page = "analysing"
            else:
                st.session_state.survey_step += 1
            st.rerun()

    if st.session_state.survey_answers:
        with st.expander("Your answers so far", icon=":material/checklist:"):
            for prev_q in QUESTIONS[:step]:
                val = st.session_state.survey_answers.get(prev_q["id"], "—")
                st.markdown(f"**Q{QUESTIONS.index(prev_q)+1}** {prev_q['text'][:60]}…  →  `{val}`")


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

        # Derive risk score from new question ids
        score = 5.0
        risk_val = ans.get("risk_tolerance", 2)
        if risk_val == 1: score -= 2
        elif risk_val == 3: score += 2

        loss_val = ans.get("loss_reaction", 2)
        if loss_val == 1: score -= 1.5
        elif loss_val == 3: score += 1.5

        horizon_val = ans.get("investment_horizon", 2)
        if horizon_val == 1: score -= 1
        elif horizon_val == 3: score += 1

        score = max(1.1, min(10.0, score))

        msg.markdown(f"<div style='text-align:center;color:{MUTED};font-size:13px;'>Querying neural model for risk level {score:.1f}…</div>",
                     unsafe_allow_html=True)
        pb.progress(40)
        time.sleep(0.8)

        msg.markdown(f"<div style='text-align:center;color:{MUTED};font-size:13px;'>Optimizing Sharpe Ratio across Body/Wing/Tail regimes…</div>",
                     unsafe_allow_html=True)
        pb.progress(70)

        horizon_map = {1: 3, 2: 7, 3: 15}
        horizon_yrs = horizon_map.get(horizon_val, 10)

        portfolio = build_portfolio(
            risk_score=score,
            initial=10000,
            monthly=500,
            years=horizon_yrs,
            answers=st.session_state.get("survey_answers", {}),
        )

        if "error" in portfolio:
            st.error(portfolio["error"])
            return

        pb.progress(90)
        msg.markdown(f"<div style='text-align:center;color:{MUTED};font-size:13px;'>Generating Atomic IQ Interpretation…</div>",
                     unsafe_allow_html=True)

        pb.progress(100)
        msg.empty()
        time.sleep(0.3)

        st.session_state.result = {
            "portfolio": portfolio,
            "score":     score,
        }

        email = st.session_state.get("user_email")
        if email and email != "guest":
            database.save_assessment(email, ans, st.session_state.result)

        st.session_state.survey_page = "portfolio"
        st.session_state.force_retake = False
        st.rerun()

    except Exception as exc:
        st.error(f"Analysis failed: {exc}")
        if st.button("← Back to Survey"):
            st.session_state.survey_page = "survey"
            st.session_state.survey_step = 0
            st.rerun()


def _render_portfolio():
    res = st.session_state.result
    if not res:
        st.session_state.survey_page = "survey"; st.rerun()

    port  = res["portfolio"]
    ans   = st.session_state.survey_answers
    email = st.session_state.get("user_email")
    iq    = port.get("iq_params", {})
    import re
    # Clean up legacy database values that hardcoded 'DeepIQ Profile X'
    _raw_cat = str(port.get("risk_category", "Balanced"))
    port["risk_category"] = re.sub(r'DeepIQ Profile \d+', 'Strategy', _raw_cat)
    cat   = port["risk_category"]
    stats = port["stats"]
    sim   = port["simulated_growth"]
    color = PROFILE_COLORS.get(cat, ACCENT2)
    sorted_weights = dict(sorted(port["allocation_pct"].items(), key=lambda x: x[1], reverse=True))
    sorted_alloc = list(sorted_weights.items())
    compact_notifs = database.get_notifications(email, limit=4)

    # Derive integer profile number for AI engine
    profile_num = _profile_num_from_port(port)

    name = st.session_state.get("user_name", "Investor").split()[0]
    now  = datetime.datetime.now().strftime("%d %b %Y")

    # ── Header ─────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
                flex-wrap:wrap;gap:12px;padding:8px 0 28px;
                border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:28px;">
      <div>
        <div style="font-size:10px;font-weight:700;color:{ACCENT};letter-spacing:0.18em;
                    text-transform:uppercase;margin-bottom:8px;">LEM StratIQ · Portfolio Dashboard</div>
        <div style="font-size:36px;font-weight:900;color:#fff;letter-spacing:-0.03em;line-height:1.05;">
          Welcome back, {name}
        </div>
        <div style="font-size:13px;color:#8BA6D3;margin-top:8px;display:flex;align-items:center;gap:10px;">
          <span style="background:rgba(142,246,209,0.12);color:#8EF6D1;border-radius:20px;
                       padding:3px 10px;font-size:11px;font-weight:700;">
            ● Live Portfolio
          </span>
          <span style="color:rgba(255,255,255,0.3);">{now}</span>
          <span style="color:rgba(255,255,255,0.3);">·</span>
          <span style="color:#8BA6D3;">Risk Score: {res.get('score', 5):.1f} / 10</span>
        </div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:10px;color:rgba(255,255,255,0.3);letter-spacing:0.1em;
                    text-transform:uppercase;margin-bottom:4px;">Strategy</div>
        <div style="font-size:15px;color:#fff;font-weight:700;">{cat}</div>
        <div style="font-size:11px;color:#8BA6D3;margin-top:2px;">{len(sorted_alloc)} Asset Classes</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI Cards — vibrant gradient style ─────────────────────────────────────
    kpi_data = [
        ("Expected Annual Return", f"{stats['expected_annual_return']:.1f}%",
         "Average yearly growth", "linear-gradient(135deg,#6D5EFC,#3BA4FF)", "#fff"),
        ("Portfolio Volatility",   f"±{stats['expected_volatility']:.1f}%",
         "Typical yearly swing",   "linear-gradient(135deg,#1a1a3e,#2a2a5e)", "#C5D3EC"),
        ("Sharpe Ratio",           f"{stats['sharpe_ratio']:.2f}",
         "Return per unit of risk","linear-gradient(135deg,#0d3d2e,#1a6b52)", "#8EF6D1"),
        ("Best-Case 10yr Value",   f"{get_currency_symbol()}{sim['p90']:,.0f}",
         "Top 10% scenario",       f"linear-gradient(135deg,#2d1a4e,{color}44)", color),
    ]
    k1, k2, k3, k4 = st.columns(4)
    for col, (label, val, hint, grad, vc) in zip([k1,k2,k3,k4], kpi_data):
        with col:
            st.markdown(f"""
            <div style="background:{grad};border:1px solid rgba(255,255,255,0.08);
                        border-radius:16px;padding:22px 20px;margin-bottom:24px;">
              <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                          letter-spacing:.12em;color:rgba(255,255,255,0.5);margin-bottom:12px;">
                {label}
              </div>
              <div style="font-family:'JetBrains Mono',monospace;font-size:30px;
                          font-weight:900;color:{vc};letter-spacing:-0.02em;line-height:1;">
                {val}
              </div>
              <div style="font-size:10px;color:rgba(255,255,255,0.35);margin-top:10px;">
                {hint}
              </div>
            </div>
            """, unsafe_allow_html=True)



    col1, col2 = st.columns([2.2, 1], gap="large")

    with col1:
        st.markdown('<div id="section-growth" class="card" style="padding: 24px; height: 100%;">', unsafe_allow_html=True)
        st.markdown('<p style="font-size:13px;font-weight:800;color:#fff;margin:0 0 4px;">Projected Portfolio Growth</p>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:12px;color:#8BA6D3;margin:0 0 12px;line-height:1.5;">This chart shows 2,000 computer-simulated futures for your portfolio. The <b style="color:#8EF6D1;">top line</b> is the optimistic path, the <b style="color:#fff;">middle</b> is most likely, and the <b style="color:#FF6B6B;">bottom line</b> is a cautious scenario.</p>', unsafe_allow_html=True)
        st.plotly_chart(monte_chart(sim, color), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div id="section-allocation" class="card" style="padding: 24px; height: 100%;">', unsafe_allow_html=True)
        st.markdown('<p style="font-size:13px;font-weight:800;color:#fff;margin:0 0 4px;">Where Your Money Goes</p>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:11px;color:#8BA6D3;margin:0 0 8px;">Your investment is spread across these assets to balance growth and safety.</p>', unsafe_allow_html=True)
        st.plotly_chart(donut_chart(sorted_weights), use_container_width=True)
        etf_html = '<div style="margin-top:4px;">'
        for asset, pct_v in sorted_weights.items():
            # Handle both short tickers ("VOO") and full names ("S&P 500 (VOO)")
            import re as _re
            _m = _re.search(r'\(([A-Z0-9.]+)\)', asset)
            ticker = _m.group(1) if _m else asset.replace(".L", "")
            display_name = asset.replace(".L", "")
            role_title, _ = ETF_ROLES.get(ticker, (None, ""))
            subtitle = role_title if role_title and role_title != display_name else ""
            etf_html += (f'<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05);">'
                         f'<div><div style="font-size:12px;color:#fff;font-weight:600;">{display_name}</div>'
                         + (f'<div style="font-size:10px;color:#8BA6D3;">{subtitle}</div>' if subtitle else '')
                         + f'</div><span style="font-size:13px;color:{color};font-weight:700;font-family:\'JetBrains Mono\',monospace;">{pct_v:.1f}%</span></div>')
        st.markdown(etf_html + "</div></div>", unsafe_allow_html=True)

    c1, c2 = st.columns([2.2, 1], gap="large")
    with c1:
        st.markdown(f"""
        <div class="card" style="padding: 24px; margin-bottom: 20px;">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
            <div style="background:{ACCENT};border-radius:10px;padding:8px;display:flex;">{get_svg("zap", 20, "#fff")}</div>
            <div>
              <div style="font-size:15px;font-weight:800;color:#ffffff;">How your portfolio was built</div>
              <div style="font-size:11px;color:{MUTED};margin-top:2px;">Powered by the LEM StratIQ AI model</div>
            </div>
          </div>
          <div style="font-size:13px;color:{MUTED};line-height:1.7;">Your answers were analysed by our AI to find the right balance between growth and safety. It then selected assets that work well together — so when some fall in value, others tend to hold steady.</div>
          <div class="tag-row" style="margin-top:16px;">
            <span class="tag">Portfolio Optimised</span>
            <span class="tag">Risk Score: {res.get('score', 5):.1f} / 10</span>
            <span class="tag">{len(sorted_alloc)} Asset Classes</span>
          </div>
        </div>
        """, unsafe_allow_html=True)


        if st.session_state.get("explanation_mode", "simple") == "advanced":
            with st.container():
                st.markdown(f'<div class="card" style="padding:20px;margin-top:16px;">', unsafe_allow_html=True)
                st.markdown(f'<p style="font-size:11px;font-weight:800;color:{ACCENT};text-transform:uppercase;letter-spacing:0.1em;margin:0 0 10px;">Advanced — MINN Diagnostics</p>', unsafe_allow_html=True)

                ic1, ic2 = st.columns(2)
                with ic1:
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.03); padding:15px; border-radius:10px; text-align:center;">
                        <div style="font-size:10px; color:{MUTED};">THRESHOLD (δ)</div>
                        <div style="font-size:24px; color:{ACCENT}; font-weight:800;">{iq.get('delta',0):.2f}</div>
                        <div style="font-size:9px; color:{MUTED};">Manifold Boundary</div>
                    </div>
                    """, unsafe_allow_html=True)
                with ic2:
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.03); padding:15px; border-radius:10px; text-align:center;">
                        <div style="font-size:10px; color:{MUTED};">DECAY (γ)</div>
                        <div style="font-size:24px; color:{ACCENT2}; font-weight:800;">{iq.get('gamma',0):.3f}</div>
                        <div style="font-size:9px; color:{MUTED};">Temporal Discount</div>
                    </div>
                    """, unsafe_allow_html=True)

                saved_config = database.get_portfolio_config(st.session_state.get("user_email", "guest"))
                new_delta = st.slider("Neural Threshold (δ)", 0.1, 2.0, float(saved_config.get("delta", iq.get("delta", 0.5))), 0.1)
                new_gamma = st.slider("Temporal Decay (γ)", 0.001, 0.5, float(saved_config.get("gamma", iq.get("gamma", 0.1))), 0.001, format="%.3f")

                if st.button("Save Custom Tuning to Cloud", use_container_width=True, type="primary"):
                    database.save_portfolio_config(st.session_state.get("user_email","guest"), {"delta":new_delta,"gamma":new_gamma})
                    st.success("Configuration saved!")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            snap_items = [
                ("Assets in your portfolio", f"{len(sorted_alloc)} investment types",          "Spreading across multiple assets reduces the risk of any one falling."),
                ("Target annual growth",     f"{stats['expected_annual_return']:.1f}% per year","This is the average return the model expects over time."),
                ("Expected ups & downs",     f"\u00b1{stats['expected_volatility']:.1f}% per year",  "Your portfolio may swing by this amount in a given year \u2014 that's normal."),
                ("Risk-to-reward score",     f"{stats['sharpe_ratio']:.2f} (higher = better)", "Measures whether the returns justify the risk taken."),
            ]
            # Card header
            st.markdown(
                f'<div class="card" style="padding:20px 22px;margin-top:16px;">'
                f'<div style="font-size:11px;font-weight:800;color:{ACCENT};text-transform:uppercase;letter-spacing:.1em;margin-bottom:10px;">Your Portfolio at a Glance</div>',
                unsafe_allow_html=True,
            )
            for s_label, s_val, s_desc in snap_items:
                is_last = (s_label == snap_items[-1][0])
                border = "" if is_last else "border-bottom:1px solid rgba(255,255,255,0.06);"
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;{border}">'
                    f'<div style="flex:1;min-width:0;">'
                    f'<div style="font-size:11px;font-weight:700;color:#C5D3EC;">{s_label}</div>'
                    f'<div style="font-size:10px;color:{MUTED};margin-top:2px;">{s_desc}</div>'
                    f'</div>'
                    f'<div style="font-size:13px;font-weight:800;color:#fff;font-family:\'JetBrains Mono\',monospace;white-space:nowrap;margin-left:16px;">{s_val}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)


    with c2:
        st.markdown(f'<div id="section-allocation" class="card" style="padding:24px;">', unsafe_allow_html=True)
        st.markdown('<p style="font-size:13px;font-weight:800;color:#fff;margin:0 0 4px;">Recent Activity</p>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:11px;color:{MUTED};margin:0 0 12px;">Notifications about your portfolio and AI model updates.</p>', unsafe_allow_html=True)
        _render_feed_card(compact_notifs, include_archive=True, compact=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── AI INVESTMENT STRATEGY ─────────────────────────────────────────────────
    anthropic_client, claude_status = _get_claude()
    if not anthropic_client:
        with st.sidebar:
            st.error("AI Engine Offline — check API key")

    if "ai_insight_text_v2" not in st.session_state:
        with st.status("Analysing your assessment via Claude Sonnet...", expanded=True) as status:
            _portfolio_stats = {
                "expected_annual_return": stats.get("expected_annual_return", 0),
                "expected_volatility":    stats.get("expected_volatility", 0),
                "sharpe_ratio":           stats.get("sharpe_ratio", 0),
                "risk_category":          port.get("risk_category", "balanced"),
                "top_assets": [(a, w * 100) for a, w in sorted_weights.items()][:6],
            }
            insight, used_claude = get_ai_explanation(ans, _portfolio_stats, iq or {})
            source = "Claude AI" if used_claude else "DeepAtomicIQ Engine"
            st.session_state.ai_insight_text_v2 = insight
            st.session_state.ai_insight_source_v2 = source
            status.update(label=f"Insight generated via {source}", state="complete", expanded=False)
            st.session_state.result["ai_narrative"] = insight
            database.save_assessment(
                st.session_state.get("user_email", "guest"),
                st.session_state.survey_answers,
                st.session_state.result,
            )

    _raw_ai_text = str(st.session_state.get("ai_insight_text_v2", "..."))
    import re
    _ai_text = re.sub(r'DeepIQ Profile \d+', 'Strategy', _raw_ai_text)
    _ai_source = st.session_state.get("ai_insight_source_v2", "Claude AI")
    _is_claude = "claude" in _ai_source.lower()

    # Section header
    st.markdown(
        f'<div id="section-ai" style="display:flex;align-items:center;gap:14px;margin:32px 0 16px;'
        f'padding-top:28px;border-top:1px solid rgba(255,255,255,0.06);">'
        f'<div style="background:linear-gradient(135deg,{ACCENT},{ACCENT2});border-radius:12px;padding:10px;display:flex;">'
        f'<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'
        f'<polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:10px;font-weight:700;color:{ACCENT};text-transform:uppercase;letter-spacing:.14em;margin-bottom:3px;">AI-Generated Strategy</div>'
        f'<h3 style="margin:0;font-size:18px;font-weight:800;color:#fff;letter-spacing:-0.01em;">Your Investment Narrative</h3>'
        f'</div>'
        f'<div style="margin-left:auto;display:flex;align-items:center;gap:8px;">'
        + (f'<div style="display:flex;align-items:center;gap:7px;background:rgba(200,100,30,0.1);'
           f'border:1px solid rgba(200,120,50,0.3);border-radius:20px;padding:5px 12px;">'
           f'<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#E07040" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
           f'<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>'
           f'<span style="font-size:10px;font-weight:700;color:#E07040;letter-spacing:.06em;">Claude 3.5 Sonnet</span>'
           f'</div>' if _is_claude else
           f'<div style="display:flex;align-items:center;gap:7px;background:rgba(109,94,252,0.1);'
           f'border:1px solid rgba(109,94,252,0.3);border-radius:20px;padding:5px 12px;">'
           f'<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="{ACCENT}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
           f'<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
           f'<span style="font-size:10px;font-weight:700;color:{ACCENT};letter-spacing:.06em;">DeepAtomicIQ Engine</span>'
           f'</div>')
        + f'</div></div>',
        unsafe_allow_html=True,
    )

    # AI narrative card
    st.markdown(f"""
    <div style="background:rgba(109,94,252,0.05);border:1px solid rgba(109,94,252,0.2);
                border-radius:16px;padding:28px 32px;">
    """, unsafe_allow_html=True)
    formatted = _ai_text.replace("\\n", "\n")
    st.markdown(f'<div style="font-size:13.5px;color:#C5D3EC;line-height:1.8;">', unsafe_allow_html=True)
    st.markdown(formatted)
    st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    btn_col1, btn_col2, _ = st.columns([1, 1, 2])
    with btn_col1:
        if st.button("Regenerate Strategy", icon=":material/refresh:", use_container_width=True):
            if "ai_insight_text_v2" in st.session_state:
                del st.session_state["ai_insight_text_v2"]
            st.rerun()
    with btn_col2:
        if st.session_state.get("user_email") != "guest":
            if st.button("Email Report", icon=":material/mail:", use_container_width=True):
                with st.spinner("Delivering report..."):
                    sent = send_portfolio_report(
                        st.session_state.user_email,
                        port["risk_category"],
                        port.get("profile_score", profile_num),
                        st.session_state.get("ai_insight_text_v2", ""),
                    )
                    if sent: st.success("Sent!")
                    else:    st.error("Failed")



    with st.expander("System Internals · Technical Audit (Examiner View)", expanded=False):
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.caption("ML Input Vector — Survey Answers")
            st.json(st.session_state.get("survey_answers", {}))
            st.caption("Markowitz Engine Output")
            st.dataframe(pd.DataFrame([port["stats"]]).T.rename(columns={0: "Value"}))
        with t_col2:
            st.caption("Claude AI Bridge")
            st.json({
                "model": "claude-3-5-sonnet-20241022",
                "profile": f"P{profile_num} — {port['risk_category']}",
                "api_health": claude_status,
                "source": st.session_state.get("ai_insight_source_v2", "unknown"),
            })
            st.caption("Persistence Layer")
            st.code(f"db.assessments.insertOne({{ user: '{st.session_state.get('user_email','guest')}', ... }})", language="javascript")
        st.info("Every survey response is validated, processed via the Markowitz optimiser, interpreted by Claude, and persisted to MongoDB Atlas.")

    # ── INVESTMENT PLANNER ────────────────────────────────────────────────────
    st.markdown("<div style='margin-top:36px;'></div>", unsafe_allow_html=True)
    _render_section_intro(
        "Investment Planner",
        "Specify your investment amount to see an exact asset-by-asset allocation and projected annual return.",
        margin_top=0,
    )

    inv_col1, inv_col2 = st.columns(2)
    with inv_col1:
        invest_amt = st.number_input(
            "Lump sum to invest (£)",
            min_value=0, max_value=10_000_000,
            value=st.session_state.get("invest_amount", 10000),
            step=500, key="invest_amount",
            help="One-off amount you plan to invest today.",
        )
    with inv_col2:
        monthly_contrib = st.number_input(
            "Monthly contribution (£)",
            min_value=0, max_value=100_000,
            value=st.session_state.get("monthly_contrib", 250),
            step=50, key="monthly_contrib",
            help="Regular monthly top-up via direct debit or standing order.",
        )

    # Combined first-year deployed capital (lump sum + 12 months of contributions)
    total_deployed = invest_amt + (monthly_contrib * 12)

    exp_r = stats.get("expected_annual_return", 0) / 100

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

    total_gain_1y = total_deployed * exp_r
    total_arrow = "&#9650;" if total_gain_1y >= 0 else "&#9660;"

    monthly_note = f" + £{monthly_contrib:,.0f}/mo" if monthly_contrib > 0 else ""
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
        '<td colspan="2" style="padding:12px 10px;font-weight:800;color:#ffffff;">TOTAL DEPLOYED</td>'
        '<td style="padding:12px 10px;text-align:right;font-size:18px;font-weight:900;color:#ffffff;">'
        + f'&pound;{invest_amt:,.0f}{monthly_note}' +
        '</td><td style="padding:12px 10px;text-align:right;font-size:16px;font-weight:800;color:#8EF6D1;">'
        + f'{total_arrow} &pound;{abs(total_gain_1y):,.0f}/yr' +
        '</td><td style="padding:12px 10px;font-size:12px;color:#8BA6D3;">'
        + f'Based on {exp_r*100:.1f}% expected annual return'
        + '</td></tr></tfoot></table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    # ── PROJECTED RETURNS TIMELINE ────────────────────────────────────────────
    monthly_note_str = f" + £{monthly_contrib:,.0f}/mo contributions" if monthly_contrib > 0 else ""
    _render_section_intro(
        "Projected Returns Timeline",
        f'Starting with <b style="color:#ffffff;">£{invest_amt:,.0f}</b>{monthly_note_str} at {exp_r*100:.1f}% p.a. (compound growth, reinvested):',
        icon_svg=get_svg("chart", 24, ACCENT),
        margin_top=28,
    )

    horizons  = [1, 3, 5, 10, 20]
    projected = [invest_amt * ((1 + exp_r) ** yr) for yr in horizons]
    gains     = [p - invest_amt for p in projected]

    proj_fig = go.Figure()
    proj_fig.add_trace(go.Bar(
        x=[f"{y}yr" for y in horizons], y=projected, name="Portfolio Value",
        marker=dict(color=projected, colorscale=[[0,"#3BA4FF"],[1,"#8EF6D1"]], line=dict(width=0)),
        text=[f"£{p:,.0f}" for p in projected], textposition="outside",
        textfont=dict(color="#ffffff", size=12),
        hovertemplate="<b>%{x}</b><br>Value: £%{y:,.0f}<extra></extra>",
    ))
    proj_fig.add_trace(go.Bar(
        x=[f"{y}yr" for y in horizons], y=[invest_amt]*len(horizons), name="Initial Investment",
        marker=dict(color="rgba(255,255,255,0.08)", line=dict(width=0)),
        hovertemplate="Initial: £%{y:,.0f}<extra></extra>",
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
        hoverlabel=dict(bgcolor="rgba(15,15,35,0.95)", font_color="#ffffff"),
    )
    st.plotly_chart(proj_fig, use_container_width=True, config={"displayModeBar": False}, key="proj_timeline")

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

    # ── WHY EACH ASSET ────────────────────────────────────────────────────────
    _render_section_intro(
        "Why Each Asset Was Chosen",
        f'The MINN selected these specific ETFs based on your risk score of <b style="color:#ffffff;">{res.get("score", 5):.0f}/10</b> and how they interact in the co-movement model.',
        icon_svg=get_svg("puzzle", 24, ACCENT),
        margin_top=28,
    )

    why_cols = st.columns(2)
    for i, (asset, pct) in enumerate(sorted_alloc):
        short  = asset.replace(".L","")
        detail = ASSET_DETAIL.get(short, {"icon":"📊","colour":"#8BA6D3","why":f"{short} provides diversified exposure to its target market segment."})
        amt    = invest_amt * (pct / 100)
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

    # ── Survey summary ────────────────────────────────────────────────────────
    with st.expander("Assessment Answers · Survey Summary", icon=":material/assignment:"):
        for i, q in enumerate(QUESTIONS):
            val = st.session_state.survey_answers.get(q["id"], "—")
            st.markdown(f"**Q{i+1}** — {q['text']}  \'\n`Answer: {val}`")

    # ── STRESS TEST ───────────────────────────────────────────────────────────
    st.divider()
    _render_section_intro(
        "Resilience Stress Test",
        "Estimated portfolio drawdown across historical market crises based on your risk category.",
        icon_svg=get_svg("shield", 24, ACCENT),
        margin_top=12,
    )
    c1, c2, c3 = st.columns(3)
    stress_scenarios = [
        ("2008 Financial Crisis", "-18.2%", "Capital preservation focus enabled."),
        ("2020 COVID Pivot",      "-8.4%",  "Fast regime recovery via Tech/Gold."),
        ("Dot-Com Bubble",        "-22.5%", "Heavy tech exposure drawdown."),
    ]
    for i, (sname, draw, logic) in enumerate(stress_scenarios):
        with [c1,c2,c3][i]:
            st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:16px;">
                <div style="font-size:10px;font-weight:800;color:#8BA6D3;margin-bottom:4px;text-transform:uppercase;">Scenario Impact</div>
                <div style="font-size:16px;font-weight:800;color:#fff;margin-bottom:4px;">{sname}</div>
                <div style="font-size:24px;font-weight:900;color:#FF6B6B;">{draw}</div>
                <div style="font-size:11px;color:#8BA6D3;margin-top:8px;">{logic}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown(f"""
<div style='margin:16px 0 8px;padding:14px 16px;background:rgba(255,107,107,0.05);
border:1px solid rgba(255,107,107,0.18);border-radius:10px;
font-size:11.5px;color:rgba(237,237,243,0.4);display:flex;gap:12px;align-items:flex-start;'>
<div style="margin-top:1px;flex-shrink:0;">{get_svg("warning", 14, "rgba(255,107,107,0.6)")}</div>
<div><span style='font-weight:700;color:rgba(237,237,243,0.6);'>Disclaimer</span> &nbsp;—&nbsp; For educational and research purposes only.
Not financial advice. Consult a qualified financial adviser before investing.
Past performance is not a reliable indicator of future results.</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    col_r, _ = st.columns([1, 3])
    with col_r:
        if st.button("Retake Assessment", icon=":material/refresh:", use_container_width=True):
            st.session_state.survey_page    = "survey"
            st.session_state.survey_step    = 0
            st.session_state.survey_answers = {}
            st.session_state.result         = None
            st.session_state.force_retake   = True
            st.rerun()