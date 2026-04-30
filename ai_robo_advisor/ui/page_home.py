"""
ui/page_home.py
===============
Landing page renderer.
"""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
import numpy as np

from ui.styles import ACCENT, ACCENT2, MUTED, get_svg
from ui.auth import _do_logout

def page_home():
    st.markdown("""
    <style>
      
      .hero-section {
        display: flex; align-items: center; justify-content: space-between;
        margin-top: 100px; margin-bottom: 140px; gap: 80px;
      }
      .hero-left { flex: 0.9; min-width: 40%; }
      .hero-right { flex: 1.1; }
      .hero-headline {
        font-size: 4.8rem; font-weight: 900; letter-spacing: -0.04em; color: #ffffff;
        line-height: 1.05; margin-bottom: 24px;
      }
      .hero-subhead {
        font-size: 1.25rem; color: #8BA6D3; line-height: 1.6; margin-bottom: 40px;
        max-width: 95%;
      }

      #hero-btn-marker + div [data-testid="stButton"] > button {
          background: linear-gradient(135deg, #6D5EFC 0%, #3BA4FF 100%) !important;
          color: white !important;
          padding: 24px 20px !important;
          border-radius: 50px !important;
          border: none !important;
          box-shadow: 0 12px 36px rgba(109, 94, 252, 0.4) !important;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
      }
      #hero-btn-marker + div [data-testid="stButton"] > button:hover {
          transform: translateY(-4px) scale(1.02) !important;
          box-shadow: 0 16px 40px rgba(109, 94, 252, 0.6) !important;
          background: linear-gradient(135deg, #7A6CFD 0%, #55B4FF 100%) !important;
          color: white !important;
      }
      #hero-btn-marker + div [data-testid="stButton"] p {
          font-size: 22px !important;
          font-weight: 800 !important;
      }
      
      .hero-right { flex: 1; }
      .glass-card-hero {
        background: rgba(255,255,255,0.02); backdrop-filter: blur(24px);
        border: 1px solid rgba(255,255,255,0.06); border-radius: 20px;
        padding: 30px; box-shadow: 0 24px 60px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1);
        position: relative; overflow: hidden;
      }
      .glass-card-hero::before {
        content: ""; position: absolute; top: -50px; right: -50px;
        width: 150px; height: 150px; background: radial-gradient(circle, rgba(142,246,209,0.2) 0%, transparent 70%);
        border-radius: 50%; pointer-events: none;
      }
      
      .hero-metric-grid { display: grid; grid-template-columns: 1.5fr 1fr; gap: 16px; margin-bottom: 16px; }
      .hero-metric { background: rgba(0,0,0,0.2); border-radius: 12px; padding: 16px; border: 1px solid rgba(255,255,255,0.03); }
      .hm-title { font-size: 11px; color: #8BA6D3; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
      .hm-val { font-size: 24px; font-weight: 800; color: #ffffff; }
      .hm-trend { font-size: 12px; color: #8EF6D1; margin-left: 8px; }
      
      /* Features */
      
      .feature-section { margin-top: 140px; }
      .feature-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 40px; margin-top: 50px; }
      .feature-card {
        background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
        border-radius: 20px; padding: 40px; transition: all 0.3s ease;
        backdrop-filter: blur(12px); position: relative; overflow: hidden;
      }

      .feature-card:hover {
        background: rgba(255,255,255,0.04); border-color: rgba(109, 94, 252, 0.4);
        transform: translateY(-4px); box-shadow: 0 16px 40px rgba(0,0,0,0.3);
      }
      .feature-icon {
        width: 48px; height: 48px; border-radius: 12px; margin-bottom: 20px;
        background: linear-gradient(135deg, rgba(109,94,252,0.2), rgba(59,164,255,0.1));
        display: flex; align-items: center; justify-content: center; font-size: 24px;
        border: 1px solid rgba(109,94,252,0.2);
      }
      .feature-title { font-size: 18px; font-weight: 700; color: #ffffff; margin-bottom: 10px; }
      .feature-desc { font-size: 14px; color: #8BA6D3; line-height: 1.6; }
      
      /* Explainer */
      .explain-section { margin-top: 100px; margin-bottom: 60px; text-align: center; }
      .explain-title { font-size: 32px; font-weight: 800; color: #ffffff; margin-bottom: 16px; }
      .chat-box {
        background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05);
        border-radius: 20px; padding: 30px; text-align: left; max-width: 800px; margin: 0 auto;
        border-left: 4px solid #3BA4FF; box-shadow: 0 20px 50px rgba(0,0,0,0.3);
      }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.1, 1], gap="large")
    
    with col1:
        # Build the welcome string based on login state
        user_name = st.session_state.get("user_name", "")
        if user_name:
            first_name = user_name.strip().split()[0]
            welcome_line2 = f"Welcome, {first_name}"
        else:
            welcome_line2 = "Welcome"

        st.markdown(f"""
        <style>
        /* Frame 1: visible 0→42%, fade out 42→48%, hidden 48→92%, fade in 92→100% */
        @keyframes heroShow {{
          0%   {{ opacity: 1; transform: translateY(0); }}
          42%  {{ opacity: 1; transform: translateY(0); }}
          48%  {{ opacity: 0; transform: translateY(-10px); }}
          92%  {{ opacity: 0; transform: translateY(10px); }}
          100% {{ opacity: 1; transform: translateY(0); }}
        }}
        /* Frame 2: hidden 0→42%, fade in 48→54%, visible 54→92%, fade out 92→100% */
        @keyframes heroHide {{
          0%   {{ opacity: 0; transform: translateY(10px); }}
          42%  {{ opacity: 0; transform: translateY(10px); }}
          48%  {{ opacity: 0; transform: translateY(10px); }}
          54%  {{ opacity: 1; transform: translateY(0); }}
          92%  {{ opacity: 1; transform: translateY(0); }}
          100% {{ opacity: 0; transform: translateY(-10px); }}
        }}
        .hero-slot {{
          position: relative;
          height: 300px;
          overflow: hidden;
        }}
        .hero-frame {{
          position: absolute; top: 0; left: 0; width: 100%;
          animation-duration: 7s;
          animation-timing-function: ease-in-out;
          animation-iteration-count: infinite;
          will-change: opacity, transform;
        }}
        .hero-frame-1 {{ animation-name: heroShow; }}
        .hero-frame-2 {{ animation-name: heroHide; }}
        </style>
        <div style="margin-top:20px;">
          <div class="hero-slot">
            <div class="hero-frame hero-frame-1">
              <div class="hero-headline">AI-Powered <br>
                <span style="background: linear-gradient(90deg, #6D5EFC, #3BA4FF);
                             -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                  Portfolio Intelligence
                </span>
              </div>
            </div>
            <div class="hero-frame hero-frame-2">
              <div class="hero-headline">
                <span style="background: linear-gradient(90deg, #6D5EFC, #3BA4FF);
                             -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                  {welcome_line2}
                </span>
              </div>
            </div>
          </div>
          <div class="hero-subhead" style="max-width:90%; margin-top:12px;">
            Personalised portfolio construction using neural inference, regime detection,
            and risk-aware optimisation directly mapped to your unique financial DNA.
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        # ── Premium Streamlit button custom-scaled using CSS
        st.markdown('<div id="hero-btn-marker"></div>', unsafe_allow_html=True)
        btn_col, btn_col2 = st.columns([1, 1])
        is_auth = st.session_state.get("authenticated", False)
        with btn_col:
            btn_label = "Start Assessment →" if is_auth else "Login to Start Assessment →"
            if st.button(btn_label, key="hero_start", use_container_width=True):
                if not is_auth:
                    st.session_state.show_auth = True
                    st.toast("Verification Required: Please sign in to start.", icon="🔒")
                else:
                    st.session_state.nav_page = "dashboard"
                    st.session_state.survey_page = "survey"
                    st.session_state.survey_step = 0
                    st.session_state.survey_answers = {}
                st.rerun()
        
        with btn_col2:
            if not is_auth:
                if st.button("Sign In / Join Now", key="hero_join", use_container_width=True):
                    st.session_state.show_auth = True
                    st.session_state.auth_mode = "login"
                    st.rerun()
            else:
                if st.button("Log Out", key="hero_logout", use_container_width=True):
                    _do_logout()
                    st.rerun()
        
        if not is_auth:
            st.markdown('<div style="font-size:11px; color:#8BA6D3; text-align:center; margin-top:8px; opacity:0.8;">✦ Identity verification required before Neural IQ analysis</div>', unsafe_allow_html=True)
            
    # ── Final Page Logic: Results & Interpretation ──
    # Ensure consistency between Hero and Bottom sections
    res_final = st.session_state.get("result")
    auth_final = st.session_state.get("authenticated", False)

    with col2:
        if auth_final and res_final:
            port   = res_final.get("portfolio", {})
            stats  = port.get("stats", {})
            alloc  = port.get("allocation_pct", {})
            score  = res_final.get("score", 5)
            cat    = port.get("risk_category", "Balanced")
            exp_r  = stats.get("expected_annual_return", 0)
            vol    = stats.get("expected_volatility", 0)
            sharpe = stats.get("sharpe_ratio", 0)
            conf   = int(min(99, max(60, sharpe * 30 + 60)))
            trend_sign = "▲" if exp_r >= 0 else "▼"
            trend_color = "#8EF6D1" if exp_r >= 0 else "#FF6B6B"

            top3 = sorted(alloc.items(), key=lambda x: x[1], reverse=True)[:3]
            bars_html = ""
            bar_colors = ["#6D5EFC", "#3BA4FF", "#8EF6D1"]
            for i, (asset, pct) in enumerate(top3):
                short = asset.split()[0]
                bars_html += f'<div style="margin-bottom:8px;"><div style="display:flex;justify-content:space-between;font-size:11px;color:#8BA6D3;margin-bottom:3px;"><span>{short}</span><span>{pct:.0f}%</span></div><div style="background:rgba(255,255,255,0.06);border-radius:4px;height:6px;"><div style="width:{pct}%;background:{bar_colors[i]};border-radius:4px;height:6px;transition:width 1s ease;"></div></div></div>'

            guest_badge_html = '<div style="background:rgba(255,255,255,0.05); color:#fff; padding:4px 10px; border-radius:12px; font-size:10px; border:1px solid rgba(255,255,255,0.1);">Demo</div>'
            st.markdown(f"""
            <div class="glass-card-hero">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px;">
                <div style="font-size:14px; color:#ffffff; font-weight:700;">Your Strategic Portfolio</div>
                <div style="display:flex; gap:8px;">
                   {guest_badge_html}
                   <div style="background:rgba(142,246,209,0.12); color:#8EF6D1; padding:4px 12px;
                                border-radius:20px; font-size:11px; font-weight:700;">
                     Profile: {cat}
                   </div>
                </div>
              </div>
              <div class="hero-metric-grid">
                <div class="hero-metric">
                  <div class="hm-title">Expected Growth</div>
                  <div class="hm-val">{trend_sign} {exp_r:.1f}% <span style="font-size:12px; color:{trend_color};">p.a.</span></div>
                </div>
                <div class="hero-metric">
                  <div class="hm-title">Neural Assurance</div>
                  <div class="hm-val" style="color:#6D5EFC;">{conf}<span style="font-size:14px;">/100</span></div>
                </div>
              </div>
              <div class="hero-metric" style="margin-top:14px; padding-bottom:10px;">
                <div class="hm-title" style="margin-bottom:12px;">Core Strategic Holdings</div>
                {bars_html}
              </div>
              <div style="display:flex; gap:16px; margin-top:14px;">
                <div style="flex:1; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); border-radius:12px; padding:12px; text-align:center;">
                  <div style="font-size:10px; color:#8BA6D3; margin-bottom:4px; text-transform:uppercase;">Volatility</div>
                  <div style="font-size:18px; font-weight:800; color:#FF9B6B;">{vol:.1f}%</div>
                </div>
                <div style="flex:1; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); border-radius:12px; padding:12px; text-align:center;">
                  <div style="font-size:10px; color:#8BA6D3; margin-bottom:4px; text-transform:uppercase;">Sharpe Ratio</div>
                  <div style="font-size:18px; font-weight:800; color:#8EF6D1;">{sharpe:.2f}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="glass-card-hero">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <div style="font-size:14px; color:#ffffff; font-weight:700;">Live Dashboard</div>
                <div style="background:rgba(109,94,252,0.15); color:#6D5EFC; padding:4px 10px;
                            border-radius:20px; font-size:11px; font-weight:700;">● Awaiting Profile</div>
              </div>
              <div style="padding:20px 0;">
                <div style="font-size:11px; color:#8BA6D3; margin-bottom:10px;">PORTFOLIO PREVIEW CONTENT</div>
                <div style="height:12px; background:rgba(255,255,255,0.05); border-radius:6px; margin-bottom:8px; width:100%;"></div>
                <div style="height:12px; background:rgba(255,255,255,0.05); border-radius:6px; margin-bottom:8px; width:80%;"></div>
                <div style="height:12px; background:rgba(255,255,255,0.05); border-radius:6px; margin-bottom:20px; width:60%;"></div>
              </div>
              <div style="text-align:center; font-size:12px; color:#6D5EFC; font-weight:600; padding:10px; background:rgba(109,94,252,0.05); border-radius:10px;">
                ✦ Complete your assessment to unlock
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Section 2: AI Strategic Analysis ──
    if auth_final and res_final:
        summary = res_final.get("ai_summary", "")
        paragraphs = [p.strip() for p in summary.split("\n\n") if p.strip()]
        verdict_para = paragraphs[0] if paragraphs else "Analysis complete."
        details_text = "\n\n".join(paragraphs[1:]) if len(paragraphs) > 1 else "Strategic weighting confirmed."
        import re
        details_html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', details_text).replace("\n\n", "<br><br>").replace("\n", "<br>")

        key_drivers = [
            {"icon": "◷", "title": "Time Horizon", "desc": "Portfolio tuned for your optimal duration."},
            {"icon": "◈", "title": "Risk Profile", "desc": "Calibrated to your volatility tolerance."},
            {"icon": "△", "title": "Growth Focus", "desc": "Prioritising capital appreciation."},
        ]
        drivers_html = "".join([
            f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(109,94,252,0.15);padding:20px 16px;border-radius:15px;text-align:center;">'
            f'<div style="font-size:26px;font-weight:200;color:#6D5EFC;margin-bottom:8px;line-height:1;">{d["icon"]}</div>'
            f'<div style="font-weight:700;color:#fff;font-size:13px;margin-bottom:4px;">{d["title"]}</div>'
            f'<div style="font-size:11px;color:#8BA6D3;line-height:1.4;">{d["desc"]}</div></div>'
            for d in key_drivers
        ])

        # Generate Claude AI insight for this section
        _insight_key = f"home_ai_insight_{port.get('risk_category','')}"
        if _insight_key not in st.session_state:
            try:
                import anthropic as _anthropic
                _ant_key = (
                    st.secrets.get("anthropic_api_key")
                    or st.secrets.get("ANTHROPIC_API_KEY")
                    or st.secrets.get("anthropic", {}).get("api_key")
                )
                port = res_final.get("portfolio", {})
                stats = port.get("stats", {})
                ans = st.session_state.get("survey_answers", {})
                cat = port.get("risk_category", "Balanced")

                if _ant_key:
                    _client = _anthropic.Anthropic(api_key=_ant_key)
                    _prompt = f"""You are DeepAtomicIQ, an expert AI investment strategist for LEM StratIQ.

A user has been assigned the following portfolio:
- Risk category: {cat}
- Expected annual return: {stats.get('expected_annual_return', 0):.1f}%
- Expected volatility: {stats.get('expected_volatility', 0):.1f}%
- Sharpe ratio: {stats.get('sharpe_ratio', 0):.2f}
- Asset allocation: {port.get('allocation_pct', {})}

Their survey answers: {ans}

Write a concise, personalised 3-paragraph explanation of why this portfolio suits them.
Paragraph 1: What their answers reveal about them as an investor.
Paragraph 2: Why this specific allocation matches their profile.
Paragraph 3: What they can realistically expect and one actionable tip.
Tone: confident, warm, professional. UK English. No emojis. Under 300 words."""
                    _msg = _client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=500,
                        messages=[{"role": "user", "content": _prompt}],
                    )
                    st.session_state[_insight_key] = _msg.content[0].text.strip()
                else:
                    st.session_state[_insight_key] = details_html
            except Exception:
                st.session_state[_insight_key] = details_html

        insight_text = st.session_state.get(_insight_key, details_html)
        import re as _re
        insight_html = _re.sub(r'\*\*(.+?)\*\*', r'<b style="color:#fff;">\1</b>', insight_text).replace("\n\n", "<br><br>").replace("\n", "<br>")

        st.markdown(f"""
<div class="explain-section" style="margin-top:20px;text-align:left;">
<h2 style="font-size:32px;font-weight:800;color:#ffffff;margin-bottom:30px;text-align:center;">Why This Portfolio Fits You</h2>
<div style="border-left:4px solid #6D5EFC;background:rgba(109,94,252,0.04);border-radius:24px;padding:40px;border:1px solid rgba(255,255,255,0.06);">
<div style="display:flex;align-items:center;margin-bottom:30px;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:20px;">
<div style="background:linear-gradient(135deg,#6D5EFC,#3BA4FF);width:44px;height:44px;border-radius:10px;display:flex;align-items:center;justify-content:center;margin-right:16px;font-size:20px;font-weight:200;color:#fff;">&#x2726;</div>
<div>
  <div style="font-weight:800;color:#fff;font-size:18px;letter-spacing:-0.01em;">Strategic Investment Verdict</div>
  <div style="font-size:11px;color:#6D5EFC;text-transform:uppercase;letter-spacing:0.08em;font-weight:700;margin-top:3px;">Claude AI · DeepAtomicIQ Interpretation</div>
</div></div>
<div style="background:rgba(255,255,255,0.03);padding:24px;border-radius:18px;border:1px solid rgba(109,94,252,0.12);margin-bottom:28px;">
<div style="font-size:10px;font-weight:800;color:#6D5EFC;margin-bottom:14px;text-transform:uppercase;letter-spacing:0.1em;">Core Decision Drivers</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;">{drivers_html}</div></div>
<div style="font-size:10px;font-weight:800;color:#6D5EFC;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.1em;">AI Strategy Analysis</div>
<div style="color:#C5D3EC;line-height:1.85;font-size:14px;background:rgba(0,0,0,0.15);padding:24px;border-radius:18px;border:1px solid rgba(255,255,255,0.04);">{insight_html}</div>
</div></div>
""", unsafe_allow_html=True)

    # ── Section 3: Feature Grid ──
    st.markdown(f"""
<div class="feature-section" style="margin-top:80px;text-align:center;">
<h2 style="font-size:32px;font-weight:800;color:#ffffff;margin-bottom:10px;">Platform Capabilities</h2>
<p style="color:#8BA6D3;margin-bottom:40px;">DeepAtomicIQ uses state-of-the-art neural architectures to protect and grow your capital.</p>
<div class="feature-grid">
<div class="feature-card"><div class="feature-icon">{get_svg("brain", 32, "#6D5EFC")}</div><div class="feature-title">Neural Optimisation</div><div class="feature-desc">Markowitz-Informed Neural Networks maximize Sharpe Ratios in real-time.</div></div>
<div class="feature-card"><div class="feature-icon">{get_svg("shield", 32, "#3BA4FF")}</div><div class="feature-title">Regime Detection</div><div class="feature-desc">AI protects capital during extreme co-movement events dynamically.</div></div>
<div class="feature-card"><div class="feature-icon">{get_svg("layers", 32, "#8EF6D1")}</div><div class="feature-title">Explainable AI</div><div class="feature-desc">No black boxes. We expose parameters that explain the model's logic.</div></div>
<div class="feature-card"><div class="feature-icon">{get_svg("chart", 32, "#FBBF24")}</div><div class="feature-title">Correlation Intel</div><div class="feature-desc">IQ-based bounds outperform historical averages via nonlinear ties.</div></div>
<div class="feature-card"><div class="feature-icon">{get_svg("settings", 32, "#FF9B6B")}</div><div class="feature-title">Risk Engine</div><div class="feature-desc">Deep Monte Carlo simulations based on manifold structures.</div></div>
<div class="feature-card"><div class="feature-icon">{get_svg("zap", 32, "#6D5EFC")}</div><div class="feature-title">Adaptive Allocation</div><div class="feature-desc">Real-time balancing informed by instantaneous macroeconomic shifts.</div></div>
</div></div>
""", unsafe_allow_html=True)

    # ── "3 Simple Steps" Section (inspired by Moneyfarm) ──────────────────────
    st.markdown("""
<style>
.steps-section { margin: 80px 0; text-align: center; }
.steps-grid { display: flex; justify-content: center; gap: 48px; margin-top: 50px; flex-wrap: wrap; }
.step-item { display: flex; flex-direction: column; align-items: center; max-width: 220px; }
.step-circle {
    width: 90px; height: 90px; border-radius: 50%;
    border: 3px solid transparent;
    background: linear-gradient(rgba(8,10,26,1), rgba(8,10,26,1)) padding-box,
                linear-gradient(135deg, #6D5EFC, #3BA4FF) border-box;
    display: flex; align-items: center; justify-content: center;
    font-size: 36px; font-weight: 900; color: #fff;
    box-shadow: 0 0 40px rgba(109,94,252,0.3);
    margin-bottom: 22px; position: relative;
}
.step-circle::after {
    content: ''; position: absolute; inset: -8px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(109,94,252,0.15), transparent 70%);
}
.step-title { font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 8px; }
.step-desc { font-size: 13px; color: #8BA6D3; line-height: 1.6; }
</style>
<div class="steps-section">
  <div style="font-size:11px;font-weight:800;color:#6D5EFC;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px;">How It Works</div>
  <h2 style="font-size:34px;font-weight:900;color:#fff;letter-spacing:-0.03em;">Get started in 3 simple steps.</h2>
  <div class="steps-grid">
    <div class="step-item">
      <div class="step-circle">1</div>
      <div class="step-title">Tell us about yourself</div>
      <div class="step-desc">Answer 10 questions about your goals, timeline, and how you feel about risk.</div>
    </div>
    <div class="step-item">
      <div class="step-circle">2</div>
      <div class="step-title">Get your AI portfolio</div>
      <div class="step-desc">Our neural network instantly maps your profile to the optimal ETF allocation.</div>
    </div>
    <div class="step-item">
      <div class="step-circle">3</div>
      <div class="step-title">Watch your wealth grow</div>
      <div class="step-desc">Track real-time performance, stress tests, and AI insights — all in one place.</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div id='steps-btn-marker'></div>", unsafe_allow_html=True)
    st.markdown("""<style>
#steps-btn-marker + div [data-testid="stButton"] > button {
    background: linear-gradient(135deg, #6D5EFC 0%, #3BA4FF 100%) !important;
    color: white !important; padding: 18px 40px !important;
    border-radius: 50px !important; border: none !important;
    font-size: 16px !important; font-weight: 700 !important;
    box-shadow: 0 12px 36px rgba(109,94,252,0.35) !important;
    display: block; margin: 0 auto;
}
</style>""", unsafe_allow_html=True)
    _, ctr, _ = st.columns([1, 1, 1])
    with ctr:
        if st.button("Start Your Neural Assessment", use_container_width=True, key="home_steps_cta"):
            st.session_state.nav_page = "dashboard"
            st.rerun()

    # ── Savings vs Investing Comparison (inspired by InvestEngine) ───────────
    st.markdown("""
<div style="margin:80px 0 20px; text-align:center;">
  <div style="font-size:11px;font-weight:800;color:#6D5EFC;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px;">The Power of Investing</div>
  <h2 style="font-size:34px;font-weight:900;color:#fff;letter-spacing:-0.03em;">Cash savings vs. AI Portfolio</h2>
  <p style="color:#8BA6D3;font-size:15px;margin-top:8px;">See what a £10,000 investment looks like over 20 years.</p>
</div>
""", unsafe_allow_html=True)
    years = list(range(0, 21))
    savings = [10000 * (1.045 ** y) for y in years]         # 4.5% savings rate
    minn    = [10000 * (1.092 ** y) for y in years]         # ~9.2% MINN expected
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years, y=savings, name="Cash Savings (4.5% p.a.)",
        line=dict(color="#8BA6D3", width=2, dash="dot"),
        fill="tozeroy", fillcolor="rgba(139,166,211,0.05)"
    ))
    fig.add_trace(go.Scatter(
        x=years, y=minn, name="DeepAtomicIQ MINN (9.2% p.a.)",
        line=dict(color="#6D5EFC", width=3),
        fill="tozeroy", fillcolor="rgba(109,94,252,0.1)"
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=340, margin=dict(t=20, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center",
                    font=dict(color="#8BA6D3", size=12), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(title="Years", color="#8BA6D3", gridcolor="rgba(255,255,255,0.04)", ticksuffix="yr"),
        yaxis=dict(title="Portfolio Value (£)", color="#8BA6D3", gridcolor="rgba(255,255,255,0.04)",
                   tickprefix="£", tickformat=",.0f"),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    # Stat callouts below chart
    ca, cb, cc = st.columns(3)
    with ca:
        st.markdown('<div style="text-align:center;padding:20px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);border-radius:16px;"><div style="font-size:11px;color:#8BA6D3;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Savings after 20yr</div><div style="font-size:26px;font-weight:900;color:#8BA6D3;">£24,117</div></div>', unsafe_allow_html=True)
    with cb:
        st.markdown('<div style="text-align:center;padding:20px;background:rgba(109,94,252,0.08);border:1px solid rgba(109,94,252,0.25);border-radius:16px;"><div style="font-size:11px;color:#6D5EFC;font-weight:700;text-transform:uppercase;margin-bottom:6px;">MINN Portfolio after 20yr</div><div style="font-size:26px;font-weight:900;color:#fff;">£59,470</div></div>', unsafe_allow_html=True)
    with cc:
        st.markdown('<div style="text-align:center;padding:20px;background:rgba(142,246,209,0.05);border:1px solid rgba(142,246,209,0.2);border-radius:16px;"><div style="font-size:11px;color:#8EF6D1;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Extra Gain</div><div style="font-size:26px;font-weight:900;color:#8EF6D1;">+£35,353</div></div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center;font-size:11px;color:rgba(139,166,211,0.5);margin-top:12px;">For illustrative purposes only. Past performance does not guarantee future results. Figures assume no fees.</p>', unsafe_allow_html=True)

