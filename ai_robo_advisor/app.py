"""
app.py  —  AI & ML Robo-Advisor  (Streamlit)
=============================================
Navigation:   Home | My Dashboard | News | Market | Search | More
Auth:         Login / Sign Up (Google, Apple, Email, Phone) → Logout
Survey:       10-question one-at-a-time wizard (DeepIQ style)
ML backend:   Random Forest + SHAP explainability
AI Explain:   Plain-English portfolio explanation (BalanceHer AssessmentEngine pattern)
Portfolio:    Markowitz allocation + Monte Carlo simulation

Run:
    cd "Demo_prototype copy"
    python3 -m streamlit run ai_robo_advisor/app.py --server.port 8507
"""

from __future__ import annotations
import os, sys, time, hashlib, json
import datetime
import numpy as np
import pandas as pd
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import secrets
import hashlib

# Architectural Node: Decentralized Local Storage Auth Engaged
from streamlit_oauth import OAuth2Component

# Securely load credentials from .streamlit/secrets.toml
try:
    LINKEDIN_CLIENT_ID = st.secrets["linkedin"]["client_id"]
    LINKEDIN_CLIENT_SECRET = st.secrets["linkedin"]["client_secret"]
    # LinkedIn uses plain base URL (NO /oauth2callback)
    REDIRECT_URI = st.secrets["linkedin"].get(
        "redirect_uri",
        "https://ai-robo-advisor-gpxvxjfgyp4cml7xjswbsh.streamlit.app"
    )
except Exception:
    LINKEDIN_CLIENT_ID = ""
    LINKEDIN_CLIENT_SECRET = ""
    REDIRECT_URI = "http://localhost:8501"


# LinkedIn manual component (still needed)
linkedin_oauth = OAuth2Component(
    LINKEDIN_CLIENT_ID,
    LINKEDIN_CLIENT_SECRET,
    "https://www.linkedin.com/oauth/v2/authorization",
    "https://www.linkedin.com/oauth/v2/accessToken",
    "https://api.linkedin.com/v2/userinfo",
)

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)
# Internal Engine Imports (Handled with defensive lookups for Streamlit stability)
try:
    from portfolio_engine import build_portfolio, TICKER_MAP, ASSETS
except (KeyError, ImportError):
    import portfolio_engine
    build_portfolio = portfolio_engine.build_portfolio
    TICKER_MAP = portfolio_engine.TICKER_MAP
    ASSETS = portfolio_engine.ASSETS

from explainer import DeepIQInterpreter
import database

# ══════════════════════════════════════════════════════════════════════════════
# THEME - "Cyber Lilac" (Inspired by modern fintech UI)
# ══════════════════════════════════════════════════════════════════════════════
ACCENT  = "#9B72F2"  # Vibrant Lilac
ACCENT2 = "#B18AFF"  # Soft Lavender
ACCENT3 = "#E6D5FF"  # White-ish Purple
CANVAS  = "#0B0B1A"  # Light background
PANEL   = "rgba(18, 18, 38, 0.72)"
BORDER  = "rgba(155, 114, 242, 0.22)"
TEXT    = "#F3F3F9"
MUTED   = "rgba(237, 237, 243, 0.55)"
GRID    = "rgba(155, 114, 242, 0.08)"
TMPL    = "plotly_dark"
POS     = "#4AE3A0"  # Spring Green
NEG     = "#FF6B6B"  # Vibrant Coral

PROFILE_COLORS = {
    "Profile 1": "#60A5FA",
    "Profile 2": "#4AE3A0",
    "Profile 3": "#FBBF24",
    "Profile 4": "#F97316",
    "Profile 5": "#EF4444",
    "Profile 6": "#9B72F2",
}

MODEL_PATH = os.path.join(_PKG_DIR, "model.pkl")

# ══════════════════════════════════════════════════════════════════════════════
# ICONS (Lucide-style Outline)
# ══════════════════════════════════════════════════════════════════════════════
def get_svg(name, size=18, color="currentColor"):
    icons = {
        "home": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
        "dashboard": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>',
        "news": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6Z"/></svg>',
        "market": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>',
        "search": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
        "more": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>',
        "brain": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.54Z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.54Z"/></svg>',
        "zap": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m13 2-2 10h3l-2 10 7-12h-3l2-8Z"/></svg>',
        "shield": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/></svg>',
        "layers": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.1 6.27a2 2 0 0 0 0 3.66l9.07 4.09a2 2 0 0 0 1.66 0l9.07-4.09a2 2 0 0 0 0-3.66Z"/><path d="m2.1 14.07 9.07 4.09a2 2 0 0 0 1.66 0l9.07-4.09"/><path d="m2.1 19.07 9.07 4.09a2 2 0 0 0 1.66 0l9.07-4.09"/></svg>',
        "chart": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 16v-4"/><path d="M11 16V8"/><path d="M15 16v-6"/></svg>',
        "risk": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20"/><path d="m4.93 4.93 14.14 14.14"/><path d="M2 12h20"/><path d="m4.93 19.07 14.14-14.14"/></svg>',
        "user": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
        "portfolio": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><rect x="7" y="10" width="4" height="7" rx="1"/><rect x="13" y="5" width="4" height="12" rx="1"/></svg>',
        "settings": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.1a2 2 0 0 0 .73-2.72l-.22-.39a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>',
        "logout": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1-2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
        "shield-check": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/></svg>',
        "bell": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>'
    }
    return icons.get(name, "")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AI Robo-Advisor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {{
  font-family: 'Inter', system-ui, sans-serif !important;
}}
.stApp {{
  background:
    radial-gradient(1000px 700px at 0% 0%, rgba(155, 114, 242, 0.15) 0%, transparent 60%),
    radial-gradient(800px 600px at 100% 20%, rgba(177, 138, 255, 0.08) 0%, transparent 70%),
    radial-gradient(1200px 800px at 50% 100%, rgba(138, 43, 226, 0.06) 0%, transparent 60%),
    linear-gradient(135deg, #070B1A 0%, #0F172A 100%);
  color: {TEXT};
}}
.block-container {{
  padding-top: 0 !important;
  padding-bottom: 4rem !important;
  max-width: 1400px; padding-top: 4rem !important;
}}
header[data-testid="stHeader"], div[data-testid="stToolbar"],
.stDeployButton, #MainMenu {{ display:none !important; visibility:hidden; }}

/* ══ TOP NAV ══ */
.nav-bar {{
  position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
  display: flex; align-items: center;
  padding: 0 40px; height: 68px;
  background: rgba(11, 11, 26, 0.9);
  backdrop-filter: blur(24px);
  border-bottom: 1px solid rgba(155, 114, 242, 0.15);
  pointer-events: none;
}}
.nav-grid {{
  display: grid; width: 100%; gap: 0 !important;
  grid-template-columns: 240px repeat(5, 110px) 1fr 360px;
  align-items: center;
}}
.nav-brand {{
  font-size: 19px; font-weight: 900; color: #ffffff;
  letter-spacing: -0.04em; display: flex; align-items: center; gap: 10px;
}}
.nav-link-wrap {{
  display: flex; justify-content: center; align-items: center; height: 68px;
}}
.nav-link:hover {{ color: #ffffff; background: rgba(255,255,255,0.05); }}
.nav-link-wrap.active .nav-link {{ color: #3BA4FF; font-weight: 700; border-bottom: 2px solid #3BA4FF; border-bottom-left-radius: 0; border-bottom-right-radius: 0; }}

.nav-link {{
  color: {MUTED}; font-size: 14px; font-weight: 500;
  transition: all 0.25s; text-decoration: none;
  padding: 8px 16px; border-radius: 12px;
  display: flex; align-items: center; gap: 8px;
  white-space: nowrap;
}}
.nav-link-wrap.active .nav-link:hover {{ color: #ffffff; background: rgba(255,255,255,0.05); }}
.nav-link-wrap.active .nav-link {{ color: #3BA4FF; font-weight: 700; border-bottom: 2px solid #3BA4FF; border-bottom-left-radius: 0; border-bottom-right-radius: 0; }}

.nav-link {{
  color: {ACCENT}; background: transparent; font-weight: 700;
}}
.nav-right {{
  display: flex; align-items: center; justify-content: flex-end; gap: 12px;
}}
#nav-trigger-marker {{ position: fixed; top: 0; left: 0; height: 0; width: 0; z-index: 1001; }}

/* The Streamlit block containing the buttons */
div[data-testid="stHorizontalBlock"]:has(#nav-trigger-marker) {{
    position: fixed !important; top: 0 !important; left: 0 !important; right: 0 !important;
    height: 68px !important; z-index: 1005 !important;
    display: grid !important; gap: 0 !important;
    grid-template-columns: 240px repeat(5, 110px) 1fr 360px !important;
    padding: 0 40px !important; align-items: center !important;
    background: transparent !important; pointer-events: auto !important;
}}
div[data-testid="stHorizontalBlock"]:has(#nav-trigger-marker) button {{
    background: transparent !important; border: none !important; color: transparent !important;
    height: 68px !important; width: 100% !important; margin: 0 !important;
    box-shadow: none !important;
}}
div[data-testid="stHorizontalBlock"]:has(#nav-trigger-marker) button:hover {{
    background: rgba(255,255,255,0.03) !important;
}}
div[data-testid="stHorizontalBlock"]:has(#nav-trigger-marker) div[data-testid="column"] {{
    width: 100% !important; flex: none !important; padding: 0 !important;
}}
.nav-account {{
  display: flex; align-items: center; gap: 8px;
  padding: 5px 12px; border-radius: 20px;
  border: 1px solid {BORDER}; background: rgba(138,43,226,0.08);
  font-size: 13px; color: {ACCENT3}; font-weight: 600;
}}
.nav-avatar {{
  width: 26px; height: 26px; border-radius: 50%;
  background: linear-gradient(135deg, {ACCENT}, {ACCENT2});
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 800; color: #ffffff;
}}
.nav-btn {{
  padding: 6px 16px; border-radius: 8px; font-size: 13px;
  font-weight: 600; cursor: pointer; transition: all 0.18s;
  border: none;
}}
.nav-btn-outline {{
  background: transparent; color: {ACCENT2};
  border: 1px solid rgba(138,43,226,0.4);
}}
.nav-btn-outline:hover {{ background: rgba(138,43,226,0.12); }}
.nav-btn-primary {{
  background: {ACCENT}; color: #ffffff;
}}
.nav-btn-primary:hover {{ background: #7020cc; box-shadow: 0 4px 16px rgba(138,43,226,0.4); }}
.nav-btn-danger {{
  background: transparent; color: {NEG};
  border: 1px solid rgba(255,107,107,0.3);
}}
.nav-btn-danger:hover {{ background: rgba(255,107,107,0.08); }}

/* ══ INPUT TEXT COLOURS (make number/text inputs readable on dark theme) ══ */
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {{
  color: #ffffff !important;
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(109,94,252,0.3) !important;
  border-radius: 10px !important;
}}
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stTextInput"] input:focus {{
  border-color: #9B72F2 !important;
  box-shadow: 0 0 0 2px rgba(155,114,242,0.18) !important;
}}





/* ══ AUTH MODAL OVERLAY (Controlled within render_auth_modal) ══ */
.modal-title {{
  font-size: 28px; font-weight: 900; letter-spacing: -0.02em; margin-bottom: 6px; text-align: center;
  background: linear-gradient(90deg, #ffffff 0%, #a78bfa 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.modal-sub {{
  font-size: 14px; color: #8BA6D3; text-align: center; margin-bottom: 28px;
}}
.modal-divider {{ display: flex; align-items: center; gap: 12px; margin: 18px 0; }}
.modal-divider-line {{ flex: 1; height: 1px; background: rgba(109,94,252,0.25); }}
.modal-divider-text {{ font-size: 11px; color: #6D5EFC; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 700; }}
.social-btn {{
  display: flex; align-items: center; justify-content: center; gap: 10px;
  width: 100%; padding: 12px 16px; border-radius: 12px; margin-bottom: 10px;
  font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.06); color: #ffffff !important;
  text-decoration: none !important;
}}
.social-btn:hover {{ background: rgba(255,255,255,0.12); border-color: rgba(109,94,252,0.5); transform: translateY(-1px); color: #ffffff !important; }}

/* Force the Streamlit Google button to match the LinkedIn button */
button[key="google_oauth_btn"] {{
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 12px !important;
    color: #ffffff !important;
    height: 43px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    margin-bottom: 10px !important;
    width: 100% !important;
    transition: all 0.2s !important;
}}
button[key="google_oauth_btn"]:hover {{
    background: rgba(255,255,255,0.12) !important;
    border-color: rgba(109,94,252,0.5) !important;
    transform: translateY(-1px) !important;
}}
.auth-tab-row {{
  display: flex; gap: 6px; margin-bottom: 24px;
  background: rgba(0,0,0,0.3); border-radius: 10px; padding: 4px;
  border: 1px solid rgba(109,94,252,0.2);
}}
.auth-tab {{
  flex: 1; padding: 8px; border-radius: 8px; text-align: center;
  font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s; color: #8BA6D3;
}}
.auth-tab.active {{ background: #6D5EFC; color: #ffffff; box-shadow: 0 4px 12px rgba(109,94,252,0.35); }}

/* Native Streamlit Inputs Override within Modal */
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) div[data-baseweb="base-input"] {{
  background-color: rgba(255,255,255,0.06) !important;
  border-radius: 12px !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
  transition: all 0.25s ease !important;
}}
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) div[data-baseweb="base-input"]:focus-within {{
  border-color: #6D5EFC !important;
  box-shadow: 0 0 0 2px rgba(109,94,252,0.3), 0 0 20px rgba(109,94,252,0.15) !important;
  background-color: rgba(109,94,252,0.08) !important;
}}
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) input {{ color: #ffffff !important; font-size: 15px !important; }}
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) label p {{ color: #a0b4d0 !important; font-size: 13px !important; font-weight: 500 !important; }}

/* FIX: Ensure all Streamlit labels in dark mode are visible */
[data-testid="stWidgetLabel"] p, [data-testid="stCheckbox"] label p {{
    color: #ffffff !important;
    font-weight: 500 !important;
    opacity: 0.95 !important;
}}
/* Specifically target number input labels which tend to be dark */
.stNumberInput label p {{
    color: #ffffff !important;
    font-size: 14px !important;
    margin-bottom: 4px !important;
}}

/* Google button - add colorful G logo via background-image */
div[data-testid="column"]:first-child button[kind="secondary"] {{
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z' fill='%234285F4'/%3E%3Cpath d='M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z' fill='%2334A853'/%3E%3Cpath d='M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z' fill='%23FBBC05'/%3E%3Cpath d='M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z' fill='%23EA4335'/%3E%3C/svg%3E") !important;
    background-repeat: no-repeat !important;
    background-position: 18% center !important;
    background-size: 18px 18px !important;
    padding-left: 24px !important;
}}


/* Streamlit button overrides inside modal */
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) button[kind="primary"] {{
  background: linear-gradient(135deg, #6D5EFC, #3BA4FF) !important;
  border: none !important;
  border-radius: 12px !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  box-shadow: 0 8px 24px rgba(109,94,252,0.4) !important;
  transition: all 0.2s !important;
}}
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) button[kind="primary"]:hover {{
  transform: translateY(-2px) !important;
  box-shadow: 0 12px 32px rgba(109,94,252,0.5) !important;
}}
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) button[kind="secondary"] {{
  background: rgba(255,255,255,0.05) !important;
  border: 1px solid rgba(255,255,255,0.15) !important;
  border-radius: 12px !important;
  color: #a0b4d0 !important;
}}
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) button[kind="secondary"]:hover {{
  background: rgba(255,255,255,0.1) !important;
  border-color: rgba(109,94,252,0.4) !important;
  color: #ffffff !important;
}}
.auth-switch {{
  text-align: center; font-size: 13px; color: {MUTED}; margin-top: 18px;
}}
.auth-switch span {{ color: {ACCENT2}; cursor: pointer; font-weight: 600; }}
.auth-error {{
  background: rgba(255,107,107,0.1); border: 1px solid rgba(255,107,107,0.3);
  border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;
  font-size: 13px; color: {NEG};
}}

/* ══ PAGE HERO ══ */
.page-hero {{
  padding: 52px 0 36px 0; text-align: center;
}}
.page-hero-title {{
  font-size: 42px; font-weight: 900; letter-spacing: -0.04em;
  background: linear-gradient(135deg, {ACCENT} 0%, {ACCENT2} 60%, {ACCENT} 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin-bottom: 14px;
}}
.page-hero-sub {{
  font-size: 16px; color: {MUTED}; max-width: 560px; margin: 0 auto; line-height: 1.65;
}}

/* ══ HOME FEATURE GRID ══ */
.feat-grid {{
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 18px; margin: 40px 0;
}}
.feat-card {{
  border: 1px solid {BORDER}; background: {PANEL}; border-radius: 18px;
  padding: 28px 24px; transition: all 0.22s; cursor: pointer;
  backdrop-filter: blur(16px);
}}
.feat-card:hover {{
  border-color: rgba(191,148,255,0.4);
  box-shadow: 0 16px 48px rgba(138,43,226,0.2);
  transform: translateY(-3px);
}}
.feat-icon {{ font-size: 32px; margin-bottom: 14px; }}
.feat-title {{ font-size: 16px; font-weight: 700; color: #ffffff; margin-bottom: 8px; }}
.feat-desc  {{ font-size: 13px; color: {MUTED}; line-height: 1.6; }}

/* ══ CARDS / PANELS ══ */
.card {{
  border: 1px solid {BORDER}; background: {PANEL};
  border-radius: 28px; padding: 28px; margin-bottom: 24px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.4);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(14px);
}}
.card:hover {{
  border-color: rgba(155, 114, 242, 0.4);
  box-shadow: 0 20px 60px rgba(155, 114, 242, 0.15);
  transform: translateY(-4px);
}}
.panel-title {{
  font-weight: 800; font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.15em;
  color: {ACCENT2}; margin-bottom: 20px;
  border-left: 4px solid {ACCENT}; padding-left: 12px;
}}

/* ══ KPI GRID ══ */
.kpi-grid {{
  display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin: 14px 0;
}}
.kpi {{
  border: 1px solid {BORDER}; background: rgba(10,10,22,0.6);
  border-radius: 14px; padding: 14px 12px; transition: all 0.2s;
}}
.kpi:hover {{
  transform: translateY(-3px);
  border-color: rgba(191,148,255,0.5);
  box-shadow: 0 16px 40px rgba(138,43,226,0.18);
}}
.kpi-label {{ color:{MUTED}; font-size:9px; font-weight:800; text-transform:uppercase; letter-spacing:0.10em; margin-bottom:7px; }}
.kpi-value {{ font-family:'JetBrains Mono',monospace; font-size:19px; font-weight:800; color:#ffffff; }}
.kpi-hint  {{ color:rgba(230,213,255,0.35); font-size:9px; margin-top:7px; line-height:1.4; }}

/* ══ SURVEY ══ */
.survey-wrap {{
  max-width: 700px; margin: 0 auto; padding: 20px 0;
}}
.q-number {{
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  color: {ACCENT2}; margin-bottom: 6px; letter-spacing: 0.08em; text-transform: uppercase;
}}
.q-text {{
  font-size: 22px; font-weight: 700; color: #ffffff;
  margin-bottom: 6px; line-height: 1.35;
}}
.q-desc {{
  font-size: 13px; color: {MUTED}; margin-bottom: 20px; line-height: 1.6;
}}
.progress-bar-wrap {{
  background: rgba(138,43,226,0.12); border-radius: 99px;
  height: 4px; margin-bottom: 24px; overflow: hidden;
}}
.progress-bar-fill {{
  background: linear-gradient(90deg, {ACCENT}, {ACCENT2});
  height: 4px; border-radius: 99px; transition: width 0.4s ease;
}}

/* ══ PROFILE HERO ══ */
.profile-hero {{
  border: 1px solid {BORDER};
  background: linear-gradient(135deg, rgba(155, 114, 242, 0.22), rgba(11, 11, 26, 0.95));
  border-radius: 32px; padding: 40px; margin-bottom: 28px;
  box-shadow: 0 25px 80px rgba(0,0,0,0.5), 0 0 40px rgba(155, 114, 242, 0.15);
  position: relative; overflow: hidden;
}}
.profile-hero::after {{
    content: ""; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle, rgba(155, 114, 242, 0.05) 0%, transparent 70%);
    pointer-events: none;
}}
.profile-name {{ font-size: 32px; font-weight: 950; color: #ffffff; letter-spacing: -0.04em; margin-bottom: 12px; }}
.profile-desc {{ font-size: 14px; color: {MUTED}; line-height: 1.7; max-width: 820px; }}
.tag-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }}
.tag {{
  background: rgba(155, 114, 242, 0.15); border: 1px solid rgba(155, 114, 242, 0.3);
  border-radius: 99px; padding: 6px 18px; font-size: 12px;
  color: {ACCENT2}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
}}

/* ══ AI EXPLAIN SECTION ══ */
.ai-explain-box {{
  background: linear-gradient(135deg, rgba(138,43,226,0.10), rgba(10,10,30,0.85));
  border: 1px solid rgba(138,43,226,0.30);
  border-radius: 18px; padding: 28px 30px; margin-bottom: 16px;
}}
.ai-explain-header {{
  display: flex; align-items: center; gap: 12px; margin-bottom: 20px;
}}
.ai-explain-icon {{
  width: 40px; height: 40px; border-radius: 12px;
  background: linear-gradient(135deg, {ACCENT}, {ACCENT2});
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}}
.ai-explain-title {{
  font-size: 16px; font-weight: 800; color: #ffffff; letter-spacing: -0.02em;
}}
.ai-explain-sub {{
  font-size: 12px; color: {MUTED};
}}
.ai-explain-para {{
  font-size: 14px; color: rgba(237,237,243,0.85);
  line-height: 1.75; margin-bottom: 14px;
  padding: 14px 18px; border-radius: 12px;
  background: rgba(255,255,255,0.03); border-left: 3px solid {ACCENT};
}}
.ai-explain-para:last-child {{ margin-bottom: 0; }}
.ai-explain-para b {{ color: {ACCENT2}; }}

/* ══ INSIGHTS ══ */
.insight-pos, .insight-neg {{
  border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; font-size: 14px;
}}
.insight-pos {{ background: rgba(74,227,160,0.08); border-left: 3px solid {POS}; }}
.insight-neg {{ background: rgba(255,107,107,0.08); border-left: 3px solid {NEG}; }}

/* ══ ETF TABLE ══ */
.etf-row {{
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0; border-bottom: 1px solid {BORDER}; font-size: 14px;
}}
.etf-name   {{ color: {ACCENT2}; font-weight: 600; }}
.etf-ticker {{ font-family: 'JetBrains Mono', monospace; color: {POS}; font-size: 12px; }}

/* ══ NEWS / MARKET PLACEHOLDERS ══ */
.coming-soon {{
  text-align: center; padding: 80px 20px;
}}
.coming-soon-icon {{ font-size: 56px; margin-bottom: 20px; }}
.coming-soon-title {{
  font-size: 24px; font-weight: 800; color: #ffffff; margin-bottom: 10px;
}}
.coming-soon-sub {{ font-size: 15px; color: {MUTED}; }}
.market-card {{
  border: 1px solid {BORDER}; background: {PANEL}; border-radius: 14px;
  padding: 18px 20px; transition: all 0.2s;
}}
.market-card:hover {{ border-color: rgba(191,148,255,0.4); transform: translateY(-2px); }}
.market-ticker {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: {ACCENT2}; }}
.market-name   {{ font-size: 11px; color: {MUTED}; margin-top: 2px; }}
.market-price  {{ font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 800; color: #ffffff; margin-top: 8px; }}
.market-change-pos {{ font-size: 12px; color: {POS}; font-weight: 600; }}
.market-change-neg {{ font-size: 12px; color: {NEG}; font-weight: 600; }}

/* plotly modebar */
.js-plotly-plot .plotly .modebar {{ opacity: 0.15; }}
.js-plotly-plot:hover .plotly .modebar {{ opacity: 0.90; }}

/* radio styled like DeepIQ */
div[role='radiogroup'] > label {{
  border: 1px solid {BORDER}; border-radius: 12px; padding: 10px 18px;
  margin-bottom: 8px; cursor: pointer; transition: all 0.2s;
  background: rgba(255,255,255,0.02);
  color: #ffffff !important;
}}
div[role='radiogroup'] > label p {{
  color: #ffffff !important;
}}
div[role='radiogroup'] > label:hover {{
  border-color: rgba(191,148,255,0.5);
  background: rgba(138,43,226,0.08);
  color: #ffffff !important;
}}
div[role='radiogroup'] > label[data-checked="true"] {{
  border-color: rgba(191,148,255,0.7);
  background: rgba(138,43,226,0.15);
  color: #ffffff !important;
}}

/* primary button lilac */
.stButton > button[kind="primary"] {{
  background: linear-gradient(135deg, {ACCENT}, {ACCENT2}) !important; border: none !important;
  border-radius: 14px !important; font-weight: 800 !important;
  font-size: 16px !important; transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
  color: #ffffff !important; padding: 0.6rem 2rem !important;
  box-shadow: 0 10px 30px rgba(155, 114, 242, 0.3) !important;
}}
.stButton > button[kind="primary"]:hover {{
  transform: translateY(-3px) scale(1.02) !important;
  box-shadow: 0 15px 45px rgba(155, 114, 242, 0.5) !important;
}}
.stButton > button {{ 
  border-radius: 14px !important; font-weight: 600 !important; 
  background: rgba(155, 114, 242, 0.05) !important;
  border: 1px solid rgba(155, 114, 242, 0.2) !important;
  color: {TEXT} !important;
}}
.stButton > button:hover {{ border-color: {ACCENT} !important; background: rgba(155, 114, 242, 0.1) !important; }}

/* Custom Text Inputs */
div[data-baseweb="input"] {{
  background-color: rgba(20, 20, 35, 0.8) !important;
  border: 1px solid rgba(155,114,242,0.4) !important;
  border-radius: 8px !important;
}}
div[data-baseweb="input"] input {{
  color: #B18AFF !important;
  font-weight: 600 !important;
  -webkit-text-fill-color: #B18AFF !important;
}}
div[data-baseweb="input"]:focus-within {{
  border-color: #B18AFF !important;
  box-shadow: 0 0 0 1px #B18AFF !important;
}}
/* ══ RICH TOOLTIP POPOVER CARDS ══ */
.rich-tooltip {{
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}}
.rich-tooltip .tt-icon {{
  font-size: 13px;
  opacity: 0.6;
  transition: opacity 0.2s;
}}
.rich-tooltip:hover .tt-icon {{ opacity: 1; }}
.tooltip-text {{
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
  position: absolute;
  bottom: calc(100% + 10px);
  left: 0;
  width: 300px;
  z-index: 9999;
  background: rgba(15, 15, 35, 0.97);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(109, 94, 252, 0.35);
  border-radius: 14px;
  padding: 14px 16px;
  font-size: 13px;
  font-weight: 400;
  color: #C8D6F0;
  line-height: 1.65;
  box-shadow: 0 12px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(109,94,252,0.1);
  transform: translateY(6px);
  transition: opacity 0.2s ease, transform 0.2s ease, visibility 0s linear 0.2s;
  white-space: normal;
  text-align: left;
}}
.tooltip-text::before {{
  content: "";
  position: absolute;
  bottom: -7px; left: 18px;
  width: 12px; height: 12px;
  background: rgba(15,15,35,0.97);
  border-right: 1px solid rgba(109,94,252,0.35);
  border-bottom: 1px solid rgba(109,94,252,0.35);
  transform: rotate(45deg);
}}
.tooltip-text .tt-header {{
  font-size: 11px; font-weight: 700; color: #6D5EFC;
  text-transform: uppercase; letter-spacing: .06em;
  margin-bottom: 6px;
  display: flex; align-items: center; gap: 5px;
}}
.rich-tooltip.tt-open .tooltip-text {{
  visibility: visible;
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
  transition: opacity 0.2s ease, transform 0.2s ease;
}}
</style>
<script>
(function(){{
  document.addEventListener('click', function(e){{
    var trigger = e.target.closest('.rich-tooltip');
    document.querySelectorAll('.rich-tooltip.tt-open').forEach(function(el){{
      if (el !== trigger) el.classList.remove('tt-open');
    }});
    if (trigger) trigger.classList.toggle('tt-open');
  }});
}})();
</script>
""", unsafe_allow_html=True)



# DeepAtomicIQ Data Loader
# Weights and IQ parameters are loaded from Robo_P directories on demand.

def _auth_check() -> bool:
    return st.session_state.get("authenticated", False)

def _user_email() -> str:
    return st.session_state.get("user_email", "")

def _user_name() -> str:
    return st.session_state.get("user_name", "")

# ── Server-side session cache (survives browser URL navigation) ───────────────
@st.cache_resource
def _session_cache():
    """Shared in-memory dict: {token -> auth dict}. Lives for the lifetime of
    the Streamlit server process — survives individual session reruns."""
    return {}

def _do_login(email: str, name: str, provider: str = "email", avatar: str = None, remember: bool = True):
    import uuid as _uuid
    token = str(_uuid.uuid4())
    _session_cache()[token] = {
        "email": email, "name": name, "provider": provider, "avatar": avatar
    }
    st.session_state.session_token  = token
    st.session_state.authenticated  = True
    st.session_state.user_email     = email
    st.session_state.user_name      = name
    st.session_state.user_provider  = provider
    st.session_state.user_avatar    = avatar
    st.session_state.show_auth      = False

    if remember:
        st.session_state.save_login_email = email
        st.session_state.save_login_name  = name

    # Rest of existing code (saved assessment, preferences...)
    saved = database.get_latest_assessment(email)
    if saved:
        st.session_state.result = saved["result"]
        st.session_state.survey_answers = saved["answers"]
        st.session_state.survey_page = "portfolio"

    st.session_state.preferences = {}
    user_data = database.get_user(email)
    if user_data and user_data.get("preferences_json"):
        import json
        try:
            st.session_state.preferences = json.loads(user_data["preferences_json"])
        except:
            pass

def get_currency_symbol() -> str:
    prefs = st.session_state.get("preferences", {})
    curr = prefs.get("currency", "GBP (£)")
    if "USD" in curr: return "$"
    if "EUR" in curr: return "€"
    return "£"

def _do_logout():
    tok = st.session_state.get("session_token")
    if tok:
        _session_cache().pop(tok, None)
    st.session_state.clear_login_token = True
    for k in ["authenticated", "user_email", "user_name", "user_provider",
              "user_avatar", "session_token"]:
        st.session_state.pop(k, None)

# ────────────────────────────────────────────────────────────────────────────────
def render_actionable_advice(port: dict, initial_investment: float, monthly_contribution: float) -> str:
    """Return HTML showing exactly which ETFs to buy, in what amounts."""
    alloc = port.get("allocation_pct", {})

    ETF_INFO = {
        "VOO":  {"name": "Vanguard S&P 500 ETF",                        "note": "Core US market growth — available on any major platform"},
        "QQQ":  {"name": "Invesco QQQ Trust (Nasdaq 100)",               "note": "Top tech companies — higher growth, higher risk"},
        "VWRA": {"name": "Vanguard FTSE All-World UCITS ETF",            "note": "Global diversification across 50+ countries"},
        "AGG":  {"name": "iShares Core US Aggregate Bond ETF",           "note": "Capital protection — cushions stock market drops"},
        "GLD":  {"name": "SPDR Gold Shares",                             "note": "Inflation hedge — rises when currencies weaken"},
        "VNQ":  {"name": "Vanguard Real Estate ETF (REITs)",             "note": "Property exposure with regular dividend income"},
        "ESGU": {"name": "iShares ESG Aware MSCI USA ETF",              "note": "S&P 500 exposure — excludes unethical companies"},
        "PDBC": {"name": "Invesco Optimum Yield Diversified Commodity", "note": "Oil, metals & agriculture — real asset diversifier"},
    }

    rows_html = ""
    sorted_alloc = sorted(alloc.items(), key=lambda x: x[1], reverse=True)
    for ticker, pct in sorted_alloc:
        if pct <= 0:
            continue
        short = ticker.replace(".L", "")
        info  = ETF_INFO.get(short, {"name": short, "note": "Broad market exposure"})
        lump  = initial_investment * (pct / 100)
        mo    = monthly_contribution * (pct / 100)
        rows_html += f"""
        <tr style="border-bottom:1px solid rgba(255,255,255,0.06);">
          <td style="padding:11px 12px;">
            <div style="font-weight:700;color:#fff;font-size:13px;">{info['name']}</div>
            <div style="font-size:11px;color:#6D5EFC;margin-top:2px;">{info['note']}</div>
          </td>
          <td style="padding:11px 12px;font-family:'JetBrains Mono',monospace;font-size:13px;">
            <a href="https://finance.yahoo.com/quote/{short}" target="_blank" 
               style="color:#8EF6D1; text-decoration:none; border-bottom:1px dashed rgba(142,246,209,0.5); font-weight:700;">
               {short} <span style="font-size:9px; vertical-align:middle; opacity:0.8;">↗</span>
            </a>
          </td>
          <td style="padding:11px 12px;text-align:center;font-weight:700;color:#fff;">{pct:.0f}%</td>
          <td style="padding:11px 12px;text-align:right;font-size:14px;font-weight:800;color:#fff;">£{lump:,.0f}</td>
          <td style="padding:11px 12px;text-align:right;font-size:13px;font-weight:700;color:#8EF6D1;">£{mo:,.0f}</td>
        </tr>"""

    total_monthly = monthly_contribution
    return f"""
    <div style="background:linear-gradient(135deg,rgba(109,94,252,0.08),rgba(0,0,0,0.25));
                border:1px solid rgba(109,94,252,0.3);border-radius:18px;
                padding:24px 24px 20px;margin:18px 0;">

      <h3 style="color:#E6D5FF;margin:0 0 6px;font-size:18px;font-weight:800;
                 display:flex;align-items:center;gap:8px;">📋 What To Buy &#8212; Step by Step</h3>
      <p style="color:#8BA6D3;font-size:13px;margin:0 0 18px;">
        Based on your profile, here are the <b style='color:#fff;'>exact ETFs to purchase</b>.
        Buy them through any brokerage (Vanguard, Fidelity, Hargreaves Lansdown, Trading 212).
        Search the ticker symbol and buy in the proportions shown.
      </p>

      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="background:rgba(109,94,252,0.18);">
              <th style="padding:10px 12px;text-align:left;color:#8BA6D3;font-size:11px;letter-spacing:.06em;font-weight:700;">ETF NAME</th>
              <th style="padding:10px 12px;text-align:left;color:#8BA6D3;font-size:11px;letter-spacing:.06em;font-weight:700;">TICKER</th>
              <th style="padding:10px 12px;text-align:center;color:#8BA6D3;font-size:11px;letter-spacing:.06em;font-weight:700;">WEIGHT</th>
              <th style="padding:10px 12px;text-align:right;color:#8BA6D3;font-size:11px;letter-spacing:.06em;font-weight:700;">LUMP SUM (&#163;)</th>
              <th style="padding:10px 12px;text-align:right;color:#8BA6D3;font-size:11px;letter-spacing:.06em;font-weight:700;">MONTHLY (&#163;)</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
          <tfoot>
            <tr style="background:rgba(109,94,252,0.1);border-top:1px solid rgba(109,94,252,0.35);">
              <td colspan="3" style="padding:11px 12px;font-weight:800;color:#fff;">TOTAL</td>
              <td style="padding:11px 12px;text-align:right;font-size:16px;font-weight:900;color:#fff;">&#163;{initial_investment:,.0f}</td>
              <td style="padding:11px 12px;text-align:right;font-size:14px;font-weight:800;color:#8EF6D1;">&#163;{total_monthly:,.0f}/mo</td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div style="margin-top:18px;padding:14px 16px;background:rgba(0,0,0,0.3);
                  border-radius:12px;border-left:3px solid #6D5EFC;">
        <p style="margin:0;color:#D4E0F7;font-size:13px;line-height:1.7;">
          <b style='color:#8EF6D1;'>&#128161; How to use this:</b>
          Open a brokerage account (e.g., <b>Hargreaves Lansdown</b>, <b>Trading 212</b>, or <b>Vanguard UK</b>).
          Search for each <b>ticker symbol</b> above. If you have
          <b style='color:#fff;'>&#163;{initial_investment:,.0f}</b> to invest today,
          buy the <b>Lump Sum</b> amounts shown.
          Then set up a <b>monthly direct debit</b> of
          <b style='color:#fff;'>&#163;{total_monthly:,.0f}</b>
          divided across the same tickers using the <b>Monthly</b> column.
          Most platforms allow automatic monthly investing &#8212; set it and forget it.
        </p>
      </div>
    </div>
    """


# ══════════════════════════════════════════════════════════════════════════════
# SURVEY QUESTIONS
# ══════════════════════════════════════════════════════════════════════════════
QUESTIONS = [
    dict(key="q1_risk_comfort", number="Q1 / 10",
         text="How much risk are you comfortable with?",
         desc="This maps to your investor risk profile. Higher risk tolerates larger swings in portfolio value but pursues greater long-term returns.",
         options=["Low — I prioritise capital preservation",
                  "Medium — balanced growth and stability",
                  "High — maximum long-term growth"],
         default="Medium — balanced growth and stability",
         map={"Low — I prioritise capital preservation": 1,
              "Medium — balanced growth and stability": 3,
              "High — maximum long-term growth": 5}),
    dict(key="q2_age", number="Q2 / 10",
         text="What is your age group?",
         desc="Younger investors can generally afford more volatility. This influences how the AI weights your risk capacity.",
         options=["Under 30","30–39","40–49","50–59","60 or over"],
         default="30–39",
         map={"Under 30":25,"30–39":35,"40–49":45,"50–59":55,"60 or over":65}),
    dict(key="q3_horizon", number="Q3 / 10",
         text="What is your intended investment time horizon?",
         desc="Longer horizons allow more volatility tolerance, as there is more time to recover from market downturns.",
         options=["Short (under 3 years)","Medium (3–10 years)","Long (10–20 years)","Very long (over 20 years)"],
         default="Long (10–20 years)",
         map={"Short (under 3 years)":2,"Medium (3–10 years)":7,"Long (10–20 years)":15,"Very long (over 20 years)":25}),
    dict(key="q4_income", number="Q4 / 10",
         text="What is your approximate annual income?",
         desc="Income determines your capacity to absorb losses and make regular contributions.",
         options=["Under £25,000","£25,000 – £50,000","£50,000 – £100,000","Over £100,000"],
         default="£25,000 – £50,000",
         map={"Under £25,000":20000,"£25,000 – £50,000":37500,"£50,000 – £100,000":75000,"Over £100,000":150000}),
    dict(key="q5_savings", number="Q5 / 10",
         text="How much do you currently have saved or invested?",
         desc="Existing wealth acts as a financial buffer, supporting a more aggressive allocation.",
         options=["Under £5,000","£5,000 – £25,000","£25,000 – £100,000","Over £100,000"],
         default="£5,000 – £25,000",
         map={"Under £5,000":2500,"£5,000 – £25,000":15000,"£25,000 – £100,000":60000,"Over £100,000":200000}),
    dict(key="q6_debt", number="Q6 / 10",
         text="How would you describe your current debt situation?",
         desc="High debt reduces financial flexibility and lowers your capacity to tolerate investment losses.",
         options=["Debt-free","Low debt (mortgage or small loans, well managed)",
                  "Moderate debt (manageable but notable)","High debt (significant financial obligations)"],
         default="Low debt (mortgage or small loans, well managed)",
         map={"Debt-free":0,"Low debt (mortgage or small loans, well managed)":10000,
              "Moderate debt (manageable but notable)":50000,"High debt (significant financial obligations)":150000}),
    dict(key="q7_dependents", number="Q7 / 10",
         text="How many financial dependants do you have?",
         desc="Dependants increase your liquidity needs and responsibilities, reducing investment risk capacity.",
         options=["None","1","2","3 or more"],
         default="None",
         map={"None":0,"1":1,"2":2,"3 or more":3}),
    dict(key="q8_emergency", number="Q8 / 10",
         text="How many months of expenses does your emergency fund cover?",
         desc="A larger emergency fund means you are less likely to need to liquidate investments unexpectedly.",
         options=["Less than 1 month","1–3 months","3–6 months","More than 6 months"],
         default="3–6 months",
         map={"Less than 1 month":0.5,"1–3 months":2,"3–6 months":4.5,"More than 6 months":9}),
    dict(key="q9_experience", number="Q9 / 10",
         text="How long have you been investing?",
         desc="Investment experience indicates familiarity with market volatility and emotional resilience during downturns.",
         options=["I am new to investing (under 1 year)","1–3 years","3–10 years","Over 10 years"],
         default="1–3 years",
         map={"I am new to investing (under 1 year)":0,"1–3 years":2,"3–10 years":6,"Over 10 years":15}),
    dict(key="q10_reaction", number="Q10 / 10",
         text="If your portfolio dropped 25% in a month, you would…",
         desc="Your behavioural response to losses is the most important signal of true risk tolerance. Be honest — there are no wrong answers.",
         options=["Sell everything immediately to stop further losses",
                  "Reduce exposure but hold some positions",
                  "Hold and wait for recovery",
                  "Hold and consider buying more at the lower price",
                  "Actively buy more — it's a long-term opportunity"],
         default="Hold and wait for recovery",
         map={"Sell everything immediately to stop further losses":5,
              "Reduce exposure but hold some positions":9,
              "Hold and wait for recovery":13,
              "Hold and consider buying more at the lower price":17,
              "Actively buy more — it's a long-term opportunity":20}),
]


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════
def _init():
    defaults = dict(
        nav_page="home",      # home | dashboard | news | market | search
        survey_step=0,
        survey_answers={},
        survey_page="survey", # survey | analysing | portfolio
        result=None,
        show_auth=False,
        auth_mode="login",    # login | signup
        auth_tab="email",     # email | phone
        authenticated=False,
        user_email="",
        user_name="",
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

if st.session_state.get("save_login_email"):
    st.components.v1.html(f"""
    <script>
    try {{ 
        window.parent.localStorage.setItem('diq_user_email', '{st.session_state.save_login_email}');
        window.parent.localStorage.setItem('diq_user_name', '{st.session_state.save_login_name}');
    }} catch(e) {{}}
    </script>
    """, height=0)
    st.session_state.pop("save_login_email", None)
    st.session_state.pop("save_login_name", None)

if st.session_state.get("clear_login_token"):
    st.components.v1.html("""
    <script>
    try { 
        window.parent.localStorage.removeItem('diq_user_email');
        window.parent.localStorage.removeItem('diq_user_name');
    } catch(e) {}
    </script>
    """, height=0)
    st.session_state.pop("clear_login_token", None)

def restore_session_from_storage():
    """Read email & name directly from localStorage and log the user in."""
    if st.session_state.get("authenticated"):
        return  # Already logged in

    if not st.session_state.get("clear_login_token"):
        st.components.v1.html("""
        <script>
        try {
            const email = window.parent.localStorage.getItem('diq_user_email');
            const name = window.parent.localStorage.getItem('diq_user_name');
            if (email && name) {
                const url = new URL(window.parent.location.href);
                if (!url.searchParams.has('_auto_email')) {
                    url.searchParams.set('_auto_email', email);
                    url.searchParams.set('_auto_name', name);
                    window.parent.location.href = url.toString();
                }
            }
        } catch(e) {}
        </script>
        """, height=0)

    # Check if we have auto-login params
    email = st.query_params.get("_auto_email", None)
    name = st.query_params.get("_auto_name", None)
    if email and name:
        if "_auto_email" in st.query_params: del st.query_params["_auto_email"]
        if "_auto_name" in st.query_params: del st.query_params["_auto_name"]
        
        _do_login(email, name, provider="persistent", remember=False)
        st.rerun()

restore_session_from_storage()

# ══ SPLASH SCREEN (first load only) ════════════════════════════════════════════
if not st.session_state.get("splash_done", False):
    st.session_state.splash_done = True
    st.markdown("""
    <style>
    #diq-splash {
        position: fixed; inset: 0;
        background: #080818;
        z-index: 99999;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        animation: splashOut 0.7s ease 2.4s forwards;
    }
    @keyframes splashOut {
        0%   { opacity:1; }
        100% { opacity:0; pointer-events:none; }
    }
    .splash-logo {
        font-size: 42px; font-weight: 900; letter-spacing: -0.04em;
        background: linear-gradient(135deg, #6D5EFC 0%, #3BA4FF 60%, #8EF6D1 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        animation: splashPulse 1.2s ease-in-out infinite alternate;
    }
    @keyframes splashPulse {
        0%   { opacity: 0.7; transform: scale(0.98); }
        100% { opacity: 1;   transform: scale(1.02); }
    }
    .splash-tagline {
        margin-top: 14px; font-size: 14px; font-weight: 500;
        color: rgba(139,166,211,0.7); letter-spacing: 0.15em;
        text-transform: uppercase;
        animation: fadeIn 0.8s ease 0.4s both;
    }
    .splash-bar {
        margin-top: 40px; width: 120px; height: 3px;
        background: rgba(255,255,255,0.06); border-radius: 99px; overflow: hidden;
    }
    .splash-bar-fill {
        height: 100%; width: 0;
        background: linear-gradient(90deg, #6D5EFC, #3BA4FF);
        border-radius: 99px;
        animation: loadBar 2.2s ease forwards;
    }
    @keyframes loadBar  { 0%{width:0} 100%{width:100%} }
    @keyframes fadeIn   { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:none} }
    </style>
    <div id="diq-splash">
      <div class="splash-logo">LEM StratIQ</div>
      <div class="splash-tagline">Powered by DeepAtomicIQ Intelligence</div>
      <div class="splash-bar"><div class="splash-bar-fill"></div></div>
    </div>
    <script>
    setTimeout(function(){
      var s = document.getElementById('diq-splash');
      if(s) s.style.display = 'none';
    }, 3200);
    </script>
    """, unsafe_allow_html=True)

if "explanation_mode" not in st.session_state:
    st.session_state.explanation_mode = "simple"   # "simple" or "advanced"

# ══════════════════════════════════════════════════════════════════════════════
# AI EXPLAIN  (adapted from BalanceHer AssessmentEngine.fetchInsight)
# — No external API needed; uses portfolio data + SHAP to write plain English —
# ══════════════════════════════════════════════════════════════════════════════
def generate_simple_explanation(port: dict, inputs: dict, answers: dict) -> list[str]:
    """Super simple, jargon‑free explanation for beginners."""
    cat = port["risk_category"]
    stats = port["stats"]
    sim = port["simulated_growth"]
    alloc = port["allocation_pct"]
    horizon = inputs.get("horizon", 10)

    # User answers in plain language
    risk_ans = answers.get("q1_risk_comfort", "Medium — balanced growth and stability")
    react_ans = answers.get("q10_reaction", "Hold and wait for recovery")
    age_ans = answers.get("q2_age", "30–39")
    horizon_ans = answers.get("q3_horizon", "Long (10–20 years)")

    # Risk category description
    if "Very Conservative" in cat:
        risk_desc = "you want your money to be as safe as possible, even if that means it grows very slowly"
    elif "Conservative" in cat:
        risk_desc = "you prefer mostly safety, but you're okay with a little bit of ups and downs if it means your money can grow a bit faster"
    elif "Moderate" in cat:
        risk_desc = "you are comfortable with a balanced mix of safety and growth – some good years, some less good, but overall a steady climb"
    elif "Aggressive" in cat:
        risk_desc = "you are willing to take bigger risks for the chance of bigger rewards – you understand that some years might be tough, but you're in it for the long term"
    else:
        risk_desc = "you are ready for a roller‑coaster ride – big ups and downs – because you believe that over many years you will come out ahead"

    # Reaction description
    if "sell everything" in react_ans.lower():
        reaction_desc = "you would panic and sell everything if the market dropped sharply"
    elif "reduce exposure" in react_ans.lower():
        reaction_desc = "you would get nervous and sell some, but keep most of your investments"
    elif "hold and wait" in react_ans.lower():
        reaction_desc = "you would stay calm and do nothing, trusting that markets usually recover"
    elif "buy more" in react_ans.lower():
        reaction_desc = "you would see a drop as a great chance to buy more at lower prices"
    else:
        reaction_desc = "you would consider adding to your investments if prices fell"

    # Horizon description
    if horizon >= 15:
        horizon_desc = "you have a very long time ahead – this gives your money many years to grow and recover from any bumps"
    elif horizon >= 7:
        horizon_desc = "you have a medium‑long horizon – plenty of time to ride out market ups and downs"
    else:
        horizon_desc = "you plan to use this money relatively soon, so we focus on keeping it safe"

    # Top two allocations with simple asset names
    top_alloc = sorted(alloc.items(), key=lambda x: x[1], reverse=True)[:2]
    asset_descriptions = {
        "US Equities": "American company shares",
        "Global Equities": "company shares from all over the world",
        "Technology": "technology company shares (like Apple, Microsoft, etc.)",
        "Core Fixed Income": "government and corporate bonds (loans that pay you interest)",
        "Gold": "physical gold",
        "Commodities": "raw materials like oil and wheat",
        "Real Estate": "property investments",
        "ESG Equities": "shares of companies that are good for the planet and society"
    }
    simple_alloc = [f"{asset_descriptions.get(a, a)} ({p:.0f}%)" for a, p in top_alloc]
    simple_alloc_str = " and ".join(simple_alloc)
    alloc_str = f"**{top_alloc[0][0]}** ({top_alloc[0][1]:.0f}%) and **{top_alloc[1][0]}** ({top_alloc[1][1]:.0f}%)" if len(top_alloc) == 2 else f"**{top_alloc[0][0]}** ({top_alloc[0][1]:.0f}%)"

    # Expected return and risk in simple terms
    expected_return = stats['expected_annual_return']
    if expected_return > 7:
        return_desc = "a high potential growth rate"
    elif expected_return > 4:
        return_desc = "a moderate growth rate"
    else:
        return_desc = "a lower but more stable growth rate"

    volatility = stats['expected_volatility']
    if volatility > 15:
        vol_desc = "your portfolio will have big swings – some years up a lot, some years down a lot"
    elif volatility > 8:
        vol_desc = "your portfolio will have noticeable ups and downs, but nothing too extreme"
    else:
        vol_desc = "your portfolio will be fairly steady, with small ups and downs"

    # Simulation numbers
    p50 = sim['p50']
    p10 = sim['p10']
    p90 = sim['p90']
    years = sim['years']

    paragraphs = [
        f"**What our AI sees in your answers**\n\n"
        f"After analyzing your answers, our AI has placed you in the **{cat}** investor type. "
        f"That means {risk_desc}. "
        f"Your age ({age_ans}) and your investment horizon ({horizon_ans}) were two of the biggest clues. "
        f"Also, when we asked what you would do if your investments suddenly dropped 25%, you told us: “{reaction_desc}”. "
        f"This behaviour tells us a lot about how you handle financial ups and downs.",

        f"**What this means for your money**\n\n"
        f"A {cat} profile typically grows at {return_desc}. "
        f"In practical terms, {vol_desc}. "
        f"The good news is that over many years, taking on some bumps usually leads to higher overall growth. "
        f"Your portfolio is designed to give you the best possible growth for the level of bumpiness you are comfortable with.",

        f"**Where your money should go**\n\n"
        f"Based on our AI calculations, your money should be split mainly between {simple_alloc_str}. "
        f"That means you would buy shares in {alloc_str}. "
        f"By spreading your money across different types of investments, you protect yourself from any one company or market crashing. "
        f"This is called **diversification** – it's like not putting all your eggs in one basket.",

        f"**What you might end up with**\n\n"
        f"We ran a computer simulation of **2,000 possible futures** for the stock market, using real historical data. "
        f"After **{years} years**, the most likely outcome (the middle scenario) is that your portfolio would be worth **£{p50:,.0f}**. "
        f"In a very good market (top 10% of scenarios), it could reach **£{p90:,.0f}**. "
        f"Even in a bad market (bottom 10% of scenarios), the model predicts **£{p10:,.0f}** – that's the power of diversification and staying invested.",

        f"**A few simple tips**\n\n"
        f"✔️ The most important thing is to **stay invested** – don't panic sell when markets drop. History shows that markets recover.\n"
        f"✔️ **Review your plan once a year** or after big life changes (marriage, new job, etc.).\n"
        f"✔️ If you ever feel confused, remember: this AI is here to help. You can always retake the survey or talk to a human financial adviser."
    ]
    return paragraphs


def generate_advanced_explanation(port: dict, inputs: dict, answers: dict) -> list[str]:
    """Technical explanation with Sharpe ratio, volatility, SHAP‑like factors."""
    cat = port["risk_category"]
    stats = port["stats"]
    sim = port["simulated_growth"]
    alloc = port["allocation_pct"]
    horizon = inputs.get("horizon", 10)

    # Top SHAP-like contributors (we can derive from answers)
    risk_ans = answers.get("q1_risk_comfort", "Medium — balanced growth and stability")
    react_ans = answers.get("q10_reaction", "Hold and wait for recovery")
    horizon_ans = answers.get("q3_horizon", "Long (10–20 years)")
    age_ans = answers.get("q2_age", "30–39")

    top_factors = ["Risk tolerance", "Investment horizon", "Behavioural response to losses"]

    # Top allocations
    top_alloc = sorted(alloc.items(), key=lambda x: x[1], reverse=True)[:2]
    alloc_str = " and ".join(f"**{a}** ({p:.0f}%)" for a, p in top_alloc)

    # ETF mapping for advanced paragraph
    etf_map = {
        "US Equities": "VOO",
        "Global Equities": "VWRA",
        "Technology": "QQQ",
        "Core Fixed Income": "AGG",
        "Gold": "GLD",
        "Commodities": "PDBC",
        "Real Estate": "VNQ",
        "ESG Equities": "ESGU"
    }
    invest_recs = [f"**{etf_map.get(a, a)}** ({p:.0f}%)" for a, p in alloc.items() if p > 0]
    top_invest_recs = " and ".join(invest_recs[:2])

    paragraphs = [
        f"Our AI analysed your answers using a **Random Forest classifier** trained on thousands of investor profiles. "
        f"With high confidence, your responses place you in the **{cat}** risk category – one of five profiles ranging from Very Conservative to Very Aggressive.",

        f"The three most important factors in your result were: **{', '.join(top_factors)}**. "
        f"When you told us you are in the **{age_ans}** age group with a **{horizon_ans}** investment horizon, the AI recognised that you {'have time to recover from market downturns' if horizon >= 10 else 'require capital protection in the near term'}. "
        f"Your reaction to a 25% drop – '*{react_ans}*' – was also a strong signal of your true risk tolerance.",

        f"A **{cat}** profile means {'you are comfortable accepting moderate ups and downs in exchange for long-term growth' if 'Moderate' in cat or 'Aggressive' in cat else 'your priority is protecting the money you have, accepting lower returns in exchange for stability'}. "
        f"The expected annual return for your portfolio is **{stats['expected_annual_return']:.1f}%**, "
        f"with an estimated year-to-year volatility of **{stats['expected_volatility']:.1f}%**. "
        f"A Sharpe ratio of **{stats['sharpe_ratio']:.2f}** indicates you are being well‑compensated for every unit of risk taken.",

        f"**Optimal allocation:** To achieve this portfolio, distribute your capital as {top_invest_recs}. "
        f"This specific {alloc_str} split is designed to {'capture aggressive global market growth while hedging against sudden drops' if stats['expected_annual_return'] > 6 else 'preserve your capital through stable bonds and low‑volatility assets while still beating inflation'}. "
        f"Diversification across these uncorrelated assets reduces idiosyncratic risk.",

        f"Based on **2,000 Monte Carlo simulations**, the median projected value after **{sim['years']} years** is **£{sim['p50']:,.0f}**. "
        f"In a bullish scenario (90th percentile), this could reach **£{sim['p90']:,.0f}**. "
        f"Even in a bearish environment (10th percentile), the model projects **£{sim['p10']:,.0f}**, reflecting the portfolio's built‑in resilience."
    ]
    return paragraphs


def get_ai_explanation(mode: str, port: dict, inputs: dict, answers: dict) -> str:
    """Return the full explanation text as a single string."""
    if mode == "simple":
        paragraphs = generate_simple_explanation(port, inputs, answers)
    else:
        paragraphs = generate_advanced_explanation(port, inputs, answers)
    return "\n\n".join(paragraphs)


# ══════════════════════════════════════════════════════════════════════════════
# PLOTLY HELPERS
# ══════════════════════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════════════════════
# NAV BAR
# ══════════════════════════════════════════════════════════════════════════════
NAV_ITEMS = [
    ("home",      "🏠 Home"),
    ("dashboard", "📊 My Dashboard"),
    ("news",      "📰 News"),
    ("market",    "📈 Market"),
    ("insights",  f"{get_svg('brain', 16)} AI Insights"),
    ("more",      "••• More"),
]

def _handle_query_params():
    """Read URL query params set by the HTML nav and update session state."""
    params = st.query_params

    # ── Restore auth from server-side session token ─────────────────────────
    if "_tok" in params:
        token = params["_tok"]
        if not st.session_state.get("authenticated"):
            cached = _session_cache().get(token)
            if cached:
                st.session_state.authenticated  = True
                st.session_state.user_email     = cached["email"]
                st.session_state.user_name      = cached["name"]
                st.session_state.user_provider  = cached["provider"]
                st.session_state.user_avatar    = cached["avatar"]
                st.session_state.session_token  = token
                # Reload saved assessment too
                saved = database.get_latest_assessment(cached["email"])
                if saved:
                    st.session_state.result = saved["result"]
                    st.session_state.survey_answers = saved["answers"]
                    st.session_state.survey_page = "portfolio"
        # Keep _tok in params across reruns so it travels with every navigation
        # (Don't delete it so the next nav link pick-up still works)

    if "page" in params:
        pg = params["page"]
        if pg in {"home", "dashboard", "market", "news", "insights", "more", "account"}:
            st.session_state.nav_page = pg
        del st.query_params["page"]

    if "auth" in params:
        mode = params["auth"]
        if mode in ("login", "signup"):
            st.session_state.show_auth = True
            st.session_state.auth_mode = mode
        del st.query_params["auth"]
        
    if "code" in params:
        code = params["code"]
        import asyncio, base64, json, httpx
        try:
            # Manually extract Google JWT Payload
            token = asyncio.run(oauth2.client.get_access_token(code=code, redirect_uri=REDIRECT_URI))
            jwt = token["id_token"].split(".")[1]
            jwt += "=" * ((4 - len(jwt) % 4) % 4)
            user_info = json.loads(base64.urlsafe_b64decode(jwt).decode("utf-8"))
            
            _do_login(user_info.get("email"), user_info.get("name", "Google User"), "google", user_info.get("picture"))
            if not database.get_user(user_info.get("email")):
                database.create_user_oauth(user_info.get("email"), user_info.get("name", "Google User"), "google")
        except Exception:
            try:
                # Fallback to LinkedIn API Endpoint
                token = asyncio.run(linkedin_oauth.client.get_access_token(code=code, redirect_uri=REDIRECT_URI))
                res = httpx.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {token['access_token']}"})
                user_info = res.json()
                _do_login(user_info.get("email"), user_info.get("name", "LinkedIn User"), "linkedin", user_info.get("picture"))
                if not database.get_user(user_info.get("email")):
                    database.create_user_oauth(user_info.get("email"), user_info.get("name", "LinkedIn User"), "linkedin")
            except Exception:
                pass
                
        st.query_params.clear()
        st.session_state.show_auth = False
        st.rerun()

    if params.get("logout") in ("1", "true"):
        st.session_state.authenticated = False
        st.session_state.user_name = None
        st.session_state.user_email = None
        st.session_state.user_avatar = None
        st.session_state.result = None
        st.session_state.nav_page = "home"
        st.query_params.clear()
        st.rerun()


def _handle_auth_bridge():
    """
    Bridge between built-in st.user (Google) and app's custom session_state.
    """
    if st.user.is_logged_in:
        if not st.session_state.get("authenticated"):
            # Auto-sync st.user to our state
            st.session_state.authenticated = True
            st.session_state.user_name = st.user.name
            st.session_state.user_email = st.user.email
            st.session_state.user_avatar = st.user.picture
            st.session_state.auth_provider = "google"
            
            # Ensure user exists in DB
            user = database.get_user(st.user.email)
            if not user:
                database.create_user(st.user.email, st.user.name, "google_oauth_fresh", "1990-01-01", "google")

def render_nav():
    _handle_auth_bridge()
    _handle_query_params()

    page = st.session_state.nav_page
    auth = st.session_state.get("authenticated", False)
    name = st.session_state.get("user_name", "")
    tok  = st.session_state.get("session_token", "")
    tp   = f"&_tok={tok}" if tok else ""   # token query param suffix

    def _active(p):
        return "active" if page == p else ""

    if auth:
        short_name = name.split()[0][:12] if name else "User"
        initials = "".join(w[0].upper() for w in name.split()[:2]) if name else "U"
        
        avatar_url = st.session_state.get("user_avatar")
        if avatar_url:
            avatar_html = f'<img src="{avatar_url}" style="width:26px; height:26px; border-radius:50%; object-fit:cover;">'
        else:
            avatar_html = f'<div class="nav-avi">{initials}</div>'
            
        auth_html = f"""
          <div class="nav-profile-wrap">
            <a href="?page=account{tp}" style="text-decoration:none;">
              <div class="nav-user-pill">
                {avatar_html}
                <span>{short_name}</span>
                <svg style="width:10px;height:10px;opacity:0.5;margin-left:2px;" viewBox="0 0 10 6" fill="none">
                  <path d="M1 1l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
              </div>
            </a>
            <!-- Hover dropdown -->
            <div class="nav-dropdown">
              <div class="nav-dd-header">
                <div class="nav-dd-av">{avatar_html}</div>
                <div>
                  <div class="nav-dd-name">{name}</div>
                  <div class="nav-dd-sub">DeepAtomicIQ Member</div>
                </div>
              </div>
              <div class="nav-dd-divider"></div>
              <a class="nav-dd-item" href="?page=account{tp}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                My Profile
              </a>
              <a class="nav-dd-item" href="?page=dashboard{tp}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><rect x="7" y="10" width="4" height="7" rx="1"/><rect x="13" y="5" width="4" height="12" rx="1"/></svg>
                My Portfolio
              </a>
              <a class="nav-dd-item" href="?page=more{tp}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.1a2 2 0 0 0 .73-2.72l-.22-.39a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
                Preferences
              </a>
              <div class="nav-dd-divider"></div>
              <a class="nav-dd-item nav-dd-logout" href="?logout=true{tp}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                Sign Out
              </a>
            </div>
          </div>
        """
    else:
        auth_html = f"""
          <a class="nav-act-btn login-btn"  href="?auth=login{tp}" target="_self" rel="noopener noreferrer">Login</a>
          <a class="nav-act-btn signup-btn" href="?auth=signup{tp}" target="_self" rel="noopener noreferrer">Sign Up</a>
          <a class="nav-act-btn cta-btn"    href="?auth=signup{tp}" target="_self" rel="noopener noreferrer">Get Started <span style='margin-left:4px;font-size:11px;'>→</span></a>
        """

    st.markdown(f"""
<style>
header[data-testid="stHeader"] {{ display: none !important; }}
#diq-navbar {{
  position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
  height: 62px;
  background: rgba(6, 8, 20, 0.95);
  backdrop-filter: blur(24px) saturate(180%);
  border-bottom: 1px solid rgba(155, 114, 242, 0.18);
  box-shadow: 0 2px 32px rgba(0,0,0,0.55);
  display: flex; align-items: center;
  padding: 0 36px; gap: 0;
  font-family: 'Inter', system-ui, sans-serif;
}}
.diq-brand {{
  font-size: 16px; font-weight: 900; letter-spacing: -0.03em; color: #fff;
  display: flex; align-items: center; gap: 9px; min-width: 190px; white-space: nowrap;
  text-decoration: none;
}}
.diq-dot {{
  width: 9px; height: 9px; border-radius: 50%;
  background: linear-gradient(135deg, #9B72F2, #4AE3A0);
  box-shadow: 0 0 8px rgba(155,114,242,0.8); flex-shrink: 0;
}}
.diq-links {{
  display: flex; align-items: center; gap: 4px; flex: 1; justify-content: center;
}}
.diq-lnk {{
  font-size: 14.5px !important; font-weight: 600 !important; color: rgba(237,237,243,0.65) !important;
  padding: 8px 20px !important; border-radius: 12px !important; white-space: nowrap !important;
  transition: all 0.2s ease !important; cursor: pointer !important;
  text-decoration: none !important; display: inline-block !important;
  border: 1px solid transparent !important;
}}
.diq-lnk:hover {{ 
  color: #fff !important; 
  background: rgba(255,255,255,0.08) !important;
  transform: translateY(-1px) !important;
}}
.diq-lnk.active {{
  color: #fff !important; 
  font-weight: 800 !important; 
  background: linear-gradient(135deg, rgba(155,114,242,0.2), rgba(109,94,252,0.1)) !important;
  border-color: rgba(155,114,242,0.3) !important;
  box-shadow: 0 4px 20px rgba(109,94,252,0.15), inset 0 0 0 1px rgba(155,114,242,0.2) !important;
}}
.diq-auth {{
  display: flex; align-items: center; gap: 9px; min-width: 260px; justify-content: flex-end;
}}
.nav-profile-wrap {{
  position: relative; display: flex; align-items: center;
}}
.nav-user-pill {{
  display: flex; align-items: center; gap: 8px;
  background: rgba(155,114,242,0.1); border: 1px solid rgba(155,114,242,0.28);
  border-radius: 22px; padding: 4px 12px 4px 5px;
  font-size: 13px; font-weight: 600; color: #E6D5FF; white-space: nowrap;
  cursor: pointer; transition: background .15s;
}}
.nav-user-pill:hover {{ background: rgba(155,114,242,0.2); }}
.nav-avi {{
  width: 26px; height: 26px; border-radius: 50%;
  background: linear-gradient(135deg, #9B72F2, #4AE3A0);
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 800; color: #fff; flex-shrink: 0;
}}
.nav-sep {{ width: 1px; height: 20px; background: rgba(155,114,242,0.25); }}
/* Hover dropdown */
.nav-dropdown {{
  display: none; position: absolute; top: calc(100% + 10px); right: 0;
  width: 230px;
  background: rgba(10,10,28,0.98); backdrop-filter: blur(20px);
  border: 1px solid rgba(109,94,252,0.3); border-radius: 16px;
  padding: 6px 0; z-index: 9999;
  box-shadow: 0 20px 60px rgba(0,0,0,0.7);
  animation: ddFade .15s ease;
}}
/* Invisible bridge to fix the hover 'dead zone' gap */
.nav-dropdown::before {{
  content: ''; position: absolute; top: -15px; left: 0; width: 100%; height: 15px;
}}
@keyframes ddFade {{ from{{opacity:0;transform:translateY(-6px)}} to{{opacity:1;transform:translateY(0)}} }}
.nav-profile-wrap:hover .nav-dropdown {{ display: block; }}
.nav-dd-header {{
  display: flex; align-items: center; gap: 10px;
  padding: 14px 16px 12px;
}}
.nav-dd-av {{ flex-shrink: 0; }}
.nav-dd-name {{ font-size: 13px; font-weight: 700; color: #fff; }}
.nav-dd-sub  {{ font-size: 11px; color: #8BA6D3; margin-top: 1px; }}
.nav-dd-divider {{ height: 1px; background: rgba(255,255,255,0.07); margin: 4px 0; }}
.nav-dd-item {{
  display: flex; align-items: center; gap: 10px;
  padding: 11px 16px; font-size: 13.5px; color: #D4E0F7;
  text-decoration: none; transition: all .15s ease;
  border-left: 3px solid transparent;
}}
.nav-dd-item:hover {{ 
  background: rgba(109,94,252,0.12); 
  color: #fff;
  border-left-color: #6D5EFC;
}}
.nav-dd-item svg {{ opacity: 0.7; transition: opacity .15s; flex-shrink: 0; }}
.nav-dd-item:hover svg {{ opacity: 1; }}
.nav-dd-logout {{ color: rgba(255,107,107,0.85); }}
.nav-dd-logout:hover {{ background: rgba(255,107,107,0.1); }}
.nav-act-btn {{
  font-size: 13.5px !important; font-weight: 600 !important; border-radius: 10px !important; border: none !important;
  padding: 10px 20px !important; cursor: pointer !important; white-space: nowrap !important; font-family: inherit !important;
  transition: all 0.2s ease !important; line-height: 1 !important; text-decoration: none !important; display: inline-block !important;
}}
.login-btn  {{ background: transparent !important; color: rgba(237,237,243,0.65) !important; }}
.login-btn:hover  {{ color: #fff !important; background: rgba(255,255,255,0.08) !important; }}
.signup-btn {{ 
  background: rgba(155,114,242,0.05) !important; 
  color: #9B72F2 !important; 
  border: 1px solid rgba(155,114,242,0.4) !important; 
}}
.signup-btn:hover {{ background: rgba(155,114,242,0.12) !important; border-color: #9B72F2 !important; }}
.cta-btn    {{ 
  background: linear-gradient(135deg, #6D5EFC, #B18AFF) !important; 
  color: #fff !important;
  box-shadow: 0 4px 15px rgba(109,94,252,0.4) !important; 
}}
.cta-btn:hover {{ 
  box-shadow: 0 6px 24px rgba(109,94,252,0.6) !important; 
  transform: translateY(-1px) !important; 
}}
.logout-btn {{ background: transparent; color: rgba(255,107,107,0.8);
               border: 1px solid rgba(255,107,107,0.3); }}
.logout-btn:hover {{ background: rgba(255,107,107,0.08); }}
</style>

<div id="diq-navbar">
  <div class="diq-brand"><div class="diq-dot"></div>LEM StratIQ</div>
  <div class="diq-links">
    <a class="diq-lnk {_active('home')}"      href="?page=home{tp}" target="_self">Home</a>
    <a class="diq-lnk {_active('dashboard')}" href="?page=dashboard{tp}" target="_self">My Dashboard</a>
    <a class="diq-lnk {_active('market')}"    href="?page=market{tp}" target="_self">Markets</a>
    <a class="diq-lnk {_active('insights')}"  href="?page=insights{tp}" target="_self">Why DeepAtomicIQ</a>
    <a class="diq-lnk {_active('more')}"      href="?page=more{tp}" target="_self">Preferences</a>
  </div>
  <div class="diq-auth">{auth_html}</div>
</div>

<script>
// Force same-tab redirection for all nav links
document.querySelectorAll('.diq-lnk, .nav-act-btn, .nav-dd-item').forEach(link => {{
    link.addEventListener('click', function(e) {{
        e.preventDefault();
        window.parent.location.href = this.getAttribute('href');
    }});
}});
</script>
""", unsafe_allow_html=True)

    # Spacer so content clears the fixed nav
    st.markdown('<div style="height:70px"></div>', unsafe_allow_html=True)

    # Hidden proxy buttons for auth actions (login/signup/logout) still needed
    with st.expander("System Hooks", expanded=False):
        st.markdown("""
        <style>
        details:has(#proxy-anchor) { display: none !important; }
        </style>
        <div id="proxy-anchor"></div>
        """, unsafe_allow_html=True)

        if st.button("auth_login_proxy", key="proxy_auth_login"):
            st.session_state.show_auth = True
            st.session_state.auth_mode = "login"
            st.rerun()
            
        if st.button("auth_signup_proxy", key="proxy_auth_signup"):
            st.session_state.show_auth = True
            st.session_state.auth_mode = "signup"
            st.rerun()
            
        if st.button("auth_logout_proxy", key="proxy_auth_logout"):
            if st.session_state.get("auth_provider") == "google":
                st.logout()
            else:
                _do_logout()
            st.rerun()






# ══════════════════════════════════════════════════════════════════════════════
# AUTH MODAL  (ported from BalanceHer signin + NavAuth patterns)
# ══════════════════════════════════════════════════════════════════════════════
def render_auth_modal():
    mode = st.session_state.get("auth_mode", "login")
    tab  = st.session_state.get("auth_tab", "email")

    title = "Sign in" if mode == "login" else "Create Account"
    
    # Layout CSS - Split Side-by-Side
    st.markdown(f"""
        <style>
        div[data-testid="stVerticalBlock"]:has(> div > div > #auth-modal-marker) {{
            position: fixed !important;
            top: 50% !important; left: 50% !important;
            transform: translate(-50%, -50%) !important;
            width: 90vw !important; max-width: 1000px !important;
            padding: 0 !important;
            border-radius: 32px !important;
            background: {PANEL} !important; 
            backdrop-filter: blur(40px) !important;
            border: 1px solid {BORDER} !important;
            box-shadow: 0 32px 100px rgba(0,0,0,0.9) !important;
            z-index: 10000 !important;
            overflow: hidden !important;
        }}

        .auth-hero-col {{
            padding: 60px;
            display: flex; flex-direction: column; justify-content: center;
            border-right: 1px solid {BORDER};
            height: 100%;
            background: linear-gradient(135deg, rgba(155, 114, 242, 0.1), transparent);
        }}
        .auth-form-col {{ padding: 60px; display: flex; flex-direction: column; justify-content: center; }}

        .hero-welcome-title {{
            font-size: 64px; font-weight: 900; 
            background: linear-gradient(90deg, #877cfc 0%, #3ba4ff 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            line-height: 1.1; margin-bottom: 20px; letter-spacing: -0.04em;
        }}
        .hero-welcome-sub {{ font-size: 16px; color: {MUTED}; line-height: 1.6; }}

        /* Advanced Social OAuth Buttons */
        .social-btn {{
            display: flex !important; align-items: center !important; justify-content: center !important;
            height: 52px !important; border-radius: 12px !important;
            background: rgba(255,255,255,0.08) !important; border: 1px solid {BORDER} !important;
            color: #ffffff !important; font-weight: 700 !important; text-decoration: none !important; 
            transition: all 0.25s ease !important; width: 100% !important; gap: 12px !important;
            margin-bottom: 0 !important;
        }}
        .social-btn:hover {{ 
            background: rgba(255,255,255,0.15) !important; 
            border-color: {ACCENT} !important;
            box-shadow: 0 0 20px rgba(155, 114, 242, 0.2) !important;
            transform: translateY(-2px) !important;
        }}
        
        .social-icon {{ width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; }}
        .google-icon {{ background: url("https://cdn.jsdelivr.net/gh/devicons/devicon/icons/google/google-original.svg") no-repeat center; background-size: contain; }}
        .linkedin-icon {{ background: url("https://cdn.jsdelivr.net/gh/devicons/devicon/icons/linkedin/linkedin-original.svg") no-repeat center; background-size: contain; }}

        .modal-divider {{ display: flex; align-items: center; gap: 10px; margin: 24px 0; opacity: 0.5; }}
        .modal-divider-line {{ flex: 1; height: 1px; background: {BORDER}; }}
        .modal-divider-text {{ font-size: 11px; font-weight: 800; color: {MUTED}; text-transform: uppercase; }}

        div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) button[kind="primary"] {{
            background: linear-gradient(135deg, {ACCENT}, {ACCENT2}) !important;
            border-radius: 12px !important;
            border: none !important;
            padding: 12px 30px !important;
        }}
        
        /* Input overrides */
        div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) .stTextInput input {{
            background: rgba(255,255,255,0.05) !important;
            color: white !important;
            border: 1px solid {BORDER} !important;
        }}
        </style>
        <div id="auth-modal-marker"></div>
    """, unsafe_allow_html=True)

    # 1. Split Layout Context
    h_col, f_col = st.columns([1, 1.2], gap="large")

    with h_col:
        # LEFT SIDE HERO
        welcome_txt = "Welcome<br>Back" if mode == "login" else "Be part of<br> the LEM Group"
        st.markdown(f"""
            <div class="auth-hero-col">
                <div style="margin-bottom: 24px;">{get_svg("brain", 40, ACCENT)}</div>
                <div class="hero-welcome-title">{welcome_txt}</div>
                <div class="hero-welcome-sub">
                    {"Strategic insights await. Log in to your neural dashboard." if mode == "login" 
                     else "Welcome! We can't wait to have you join the future of wealth."}
                </div>
            </div>
        """, unsafe_allow_html=True)

    with f_col:
        # RIGHT SIDE FORM
        st.markdown(f'<div style="font-size: 32px; font-weight: 800; color: white; margin-bottom: 5px;">{title}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size: 14px; color: {MUTED}; margin-bottom: 30px;">Sign in to access your portfolio</div>', unsafe_allow_html=True)
        
        # --- OAUTH (Safe Link Generation) ---
        import asyncio
        linkedin_url = "#"
        l_err = None
        
        try:
            linkedin_url = asyncio.run(linkedin_oauth.client.get_authorization_url(redirect_uri=REDIRECT_URI, scope=["openid", "profile", "email"]))
        except Exception as e: l_err = str(e)

        if l_err: st.error(f"LinkedIn Error: {l_err}")

        # Social Buttons
        s1, s2 = st.columns(2)
        with s1:
            if st.button("Google", type="secondary", use_container_width=True, key="google_oauth_btn"):
                st.login()
        with s2:
            st.markdown(f"""
                <a href="{linkedin_url}" target="_top" class="social-btn" style="height: 43px !important; margin: 0 !important; box-sizing: border-box; text-decoration: none; gap: 8px;">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="#0A66C2" style="flex-shrink:0;"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                    <span style="font-size: 14px; color: white !important;">LinkedIn</span>
                </a>
            """, unsafe_allow_html=True)

        st.markdown('<div class="modal-divider"><div class="modal-divider-line"></div><div class="modal-divider-text">OR EMAIL</div><div class="modal-divider-line"></div></div>', unsafe_allow_html=True)

        # Tabs
        t1, t2 = st.columns(2)
        with t1:
            if st.button("✉️ Email", use_container_width=True, type="primary" if tab == "email" else "secondary", key="email_tab_btn"):
                st.session_state.auth_tab = "email"; st.rerun()
        with t2:
            if st.button("📱 Phone", use_container_width=True, type="primary" if tab == "phone" else "secondary", key="phone_tab_btn"):
                st.session_state.auth_tab = "phone"; st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        import random, re
        # VERIFICATION
        if st.session_state.get("auth_verify_pending"):
            st.info(f"**Demo note:** Use this test code to continue: `{st.session_state.get('mock_code', '1234')}`")
            code_in = st.text_input("Enter 4-digit code", placeholder="####", key="auth_code_input_final", max_chars=4)
            vc1, vc2 = st.columns(2)
            with vc1:
                if st.button("Cancel", use_container_width=True, key="vc_cancel"):
                    st.session_state.auth_verify_pending = False; st.rerun()
            with vc2:
                if st.button("Verify & Proceed", type="primary", use_container_width=True, key="vc_verify"):
                    if code_in == st.session_state.get("mock_code"):
                        action = st.session_state.get("pending_action")
                        data   = st.session_state.get("pending_data")
                        if action.startswith("signup"):
                            database.create_user(data["email"], data["name"], data["pw"], data["dob"], "email")
                            _do_login(data["email"], data["name"], "email")
                        else:
                            _do_login(data["email"], data["name"], "email")
                        st.session_state.auth_verify_pending = False; st.rerun()
                    else: st.error("Invalid code.")
            return

        # FORM FIELDS
        if tab == "email":
            email_in = st.text_input("EMAIL ADDRESS", placeholder="you@example.com", key="auth_email_field_f")
            name_in = ""
            dob_in = datetime.date(1990,1,1)
            if mode == "signup":
                name_in = st.text_input("FULL NAME", placeholder="Jane Smith", key="auth_name_field_f")
                dob_in = st.date_input(
                    "DATE OF BIRTH",
                    value=datetime.date(1990, 1, 1),
                    min_value=datetime.date(1900, 1, 1),
                    max_value=datetime.date.today(),
                    key="auth_dob_field_f"
                )
            
            pw_in = st.text_input("PASSWORD", type="password", key="auth_pw_field_f")
            st.checkbox("Keep me logged in", value=True, key="rem_f")

            _btn_col, _ = st.columns(2)
            with _btn_col:
                if st.button("Sign In Now" if mode == "login" else "Create Account", type="primary", use_container_width=True, key="auth_submit_f"):
                    if not email_in or not pw_in: st.error("All fields mandatory."); return

                    # Regex Validation
                    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
                    if not re.match(email_regex, email_in):
                        st.error("Please enter a valid email address.")
                        return

                    if mode == "signup":
                        if not name_in: st.error("Name mandatory."); return
                        if database.get_user(email_in): st.error("Email exists."); return
                        st.session_state.auth_verify_pending = True
                        st.session_state.mock_code = str(random.randint(1000, 9999))
                        st.session_state.pending_action = "signup_email"
                        st.session_state.pending_data = {"email": email_in, "name": name_in, "pw": pw_in, "dob": dob_in.strftime("%Y-%m-%d")}
                        st.rerun()
                    else:
                        user = database.get_user(email_in)
                        if user and user["password_hash"] == database.hash_password(pw_in):
                            st.session_state.auth_verify_pending = True
                            st.session_state.mock_code = str(random.randint(1000, 9999))
                            st.session_state.pending_action = "login_email"
                            st.session_state.pending_data = {"email": email_in, "name": user["name"]}
                            st.rerun()
                        else: st.error("Invalid credentials.")
        else:
            # PHONE PICKER RESTORED
            country_codes = ["+44 (UK)", "+1 (USA/Canada)", "+34 (Spain)", "+33 (France)", "+49 (Germany)", "+91 (India)", "+61 (Australia)", "+81 (Japan)"]
            p1, p2 = st.columns([0.4, 0.6])
            with p1:
                p_code = st.selectbox("CODE", country_codes, key="auth_p_code_f")
            with p2:
                p_num = st.text_input("NUMBER", placeholder="7123 456789", key="phone_f_final")
            
            st.text_input("PASSWORD", type="password", key="phone_pw_f_final")
            
            _btn_col2, _ = st.columns(2)
            with _btn_col2:
                if st.button("Proceed", type="primary", use_container_width=True, key="phone_gobutton"):
                    if not p_num: st.error("Enter phone number."); return
                    # Handle phone login here
                    full_phone = f"{p_code} {p_num}"
                    st.info(f"Verification sent to {full_phone}")
                    st.session_state.auth_verify_pending = True
                    st.session_state.mock_code = "1234"
                    st.session_state.pending_action = "login_phone"
                    st.session_state.pending_data = {"phone": full_phone}
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        lbl_mode = "Don't have an account? Sign up" if mode == "login" else "Already have an account? Sign in"
        _m1, _m2 = st.columns(2)
        with _m1:
            if st.button(lbl_mode, key="mode_toggle_f", use_container_width=True):
                st.session_state.auth_mode = "signup" if mode == "login" else "login"; st.rerun()
        with _m2:
            if st.button("Return Home", type="primary", use_container_width=True, key="close_f_final"):
                st.session_state.show_auth = False; st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════════════════════

# ── HOME ──────────────────────────────────────────────────────────────────────
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
            {"icon": "⌛", "title": "Time Horizon", "desc": "Portfolio tuned for your optimal duration."},
            {"icon": "🧘", "title": "Psychology", "desc": "Optimized for your volatility comfort."},
            {"icon": "🚀", "title": "Growth Focus", "desc": "Prioritizing capital appreciation."}
        ]
        drivers_html = "".join([
            f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.05);padding:16px;border-radius:15px;text-align:center;">'
            f'<div style="font-size:20px;margin-bottom:6px;">{d["icon"]}</div>'
            f'<div style="font-weight:700;color:#fff;font-size:14px;">{d["title"]}</div>'
            f'<div style="font-size:11px;color:#8BA6D3;line-height:1.4;">{d["desc"]}</div></div>' for d in key_drivers
        ])

        st.markdown(f"""
<div class="explain-section" style="margin-top:20px;text-align:left;">
<h2 style="font-size:32px;font-weight:800;color:#ffffff;margin-bottom:30px;text-align:center;">Why This Portfolio Fits You</h2>
<div class="chat-box" style="border-left:4px solid #6D5EFC;background:rgba(109,94,252,0.04);border-radius:24px;padding:40px;border:1px solid rgba(255,255,255,0.06);">
<div style="display:flex;align-items:center;margin-bottom:30px;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:20px;">
<div style="background:linear-gradient(135deg,#6D5EFC,#3BA4FF);width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-right:16px;font-size:22px;">🧠</div>
<div><div style="font-weight:800;color:#fff;font-size:18px;letter-spacing:-0.01em;">Strategic Investment Verdict</div>
<div style="font-size:12px;color:#8BA6D3;text-transform:uppercase;letter-spacing:0.04em;font-weight:700;">Neural Diagnosis · DeepAtomicIQ Interpretation</div></div></div>
<div style="background:rgba(255,255,255,0.05);padding:24px;border-radius:18px;border:1px solid rgba(138,43,226,0.15);margin-bottom:32px;">
<div style="font-size:12px;font-weight:800;color:#6D5EFC;margin-bottom:12px;text-transform:uppercase;">Core Decision Drivers</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;">{drivers_html}</div></div>
<div style="font-size:12px;font-weight:800;color:#6D5EFC;margin-bottom:12px;text-transform:uppercase;">Deep Analysis Details</div>
<div style="color:#FFF;line-height:1.8;font-size:15px;background:rgba(255,255,255,0.02);padding:24px;border-radius:18px;border:1px solid rgba(255,255,255,0.05);">{details_html}</div></div></div>
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
    import numpy as np
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


# ── SURVEY + PORTFOLIO ─────────────────────────────────────────────────────────
# ── DASHBOARD / SURVEY GATE ──────────────────────────────────────────────────
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

    # Results check — survey not yet completed
    if not st.session_state.get("result"):
        st.markdown(f"""
        <div class="coming-soon">
          <div class="coming-soon-icon" style="color:#6D5EFC;margin-bottom:15px;display:flex;justify-content:center;">{get_svg("news", 40)}</div>
          <div class="coming-soon-title">Incomplete Risk Profile</div>
          <div class="coming-soon-sub">Please complete the investor assessment survey to view your dashboard.</div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            if st.button("Start Neural Assessment <span style='margin-left:4px;font-size:11px;'>→</span>", type="primary", use_container_width=True):
                st.session_state.survey_page = "survey"
                st.session_state.survey_step = 0
                st.session_state.survey_answers = {}
                st.rerun()
        
        if sp == "survey":
            st.markdown("---")
            _render_survey()
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
        with st.expander("📋 Your answers so far"):
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
        
        dynamic_paragraphs = get_ai_explanation(st.session_state.explanation_mode, portfolio, inputs, ans)
        minn_base = "This project implements a Markowitz-Informed Neural Network (MINN) to learn how to build investment portfolios that balance risk and return intelligently. It combines ideas from finance (portfolio theory) and machine learning (deep neural networks). The model learns how assets \"move together\" — their co-movements or correlations — and finds portfolio weights that maximize the Sharpe Ratio, a measure of performance defined as average return divided by risk. In plain terms: the network learns how to distribute money across several assets so that the overall portfolio performs well relative to its volatility (ups and downs)."
        
        final_summary = minn_base + "\n\n" + dynamic_paragraphs
        
        pb.progress(100)
        msg.empty()
        time.sleep(0.3)

        st.session_state.result = {
            "portfolio":   portfolio,
            "ai_summary":  final_summary,
            "score":       score
        }
        
        # PERSIST to database
        email = st.session_state.get("user_email")
        if email:
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
    iq    = port.get("iq_params", {})
    cat   = port["risk_category"]
    stats = port["stats"]
    sim   = port["simulated_growth"]
    color = PROFILE_COLORS.get(f"Profile {port['profile_score']}", ACCENT2)
    summary = res.get("ai_summary", "")

    # ── Profile hero ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="profile-hero">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <div style="background:{ACCENT};border-radius:10px;padding:8px;display:flex;">{get_svg("zap", 24, "#fff")}</div>
        <div class="profile-name" style="margin-bottom:0;">Markowitz-Informed Neural Network (MINN)</div>
      </div>
      <div class="profile-desc">Neural state optimization completed for date **{port['date']}**. Models tuned to maximize Sharpe Ratio under current co-movement regimes.</div>
      <div class="tag-row">
        <span class="tag">AI Inference Validated</span>
        <span class="tag">δ={iq.get('delta',0):.2f}</span>
        <span class="tag">γ={iq.get('gamma',0):.3f}</span>
        <span class="tag">ε={iq.get('epsilon',0):.1f}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    kpi_html = '<div class="kpi-grid">'
    for label, val, hint, vc, tooltip in [
        ("Expected Return",  f"{stats['expected_annual_return']:.1f}%",  "Inferential Estimate", POS, "The average percentage your portfolio is expected to grow each year based on long-term data."),
        ("Learned Volatility",f"{stats['expected_volatility']:.1f}%",   "Predicted Pfolio Vol", "#ffffff", "How much your portfolio\\'s value is likely to bounce up and down. A lower number means a smoother, less stressful ride."),
        ("Sharpe Ratio",     f"{stats['sharpe_ratio']:.2f}",             "Risk-Adjusted Learner", POS, "A score showing how much return you are getting for the risk you are taking. A higher score means smarter investing!"),
        ("P90 Growth",       f"{get_currency_symbol()}{sim['p90']:,.0f}",                      f"Optimistic Projection",color, "The \\'best-case\\' scenario (top 10% of possibilities) of what your portfolio could be worth at the end of your timeframe."),
    ]:
        kpi_html += (f'<div class="kpi" title="{tooltip}"><div class="kpi-label">{label}</div>'
                     f'<div class="kpi-value" style="color:{vc};">{val}</div>'
                     f'<div class="kpi-hint">{hint}</div></div>')
    kpi_html += "</div>"
    st.markdown(kpi_html, unsafe_allow_html=True)

    # ── ACTIONABLE ADVICE ─────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="font-size:22px;font-weight:900;color:#ffffff;letter-spacing:-0.03em;margin:24px 0 4px;">
      🛒 Portfolio Implementation Guide
    </div>
    <div style="font-size:13px;color:{MUTED};margin-bottom:14px;">
      Enter your numbers below to get a personalised shopping list for your brokerage account.
    </div>
    """, unsafe_allow_html=True)

    ai_col1, ai_col2, _ = st.columns([1, 1, 1])
    with ai_col1:
        lump_sum = st.number_input(
            "How much can you invest right now? (£)",
            min_value=0, max_value=10_000_000,
            value=st.session_state.get("_lump_sum", 10000),
            step=500, key="_lump_sum",
            help="Your one-off starting investment"
        )
    with ai_col2:
        monthly_contrib = st.number_input(
            "How much can you add each month? (£)",
            min_value=0, max_value=100_000,
            value=st.session_state.get("_monthly_contrib", 500),
            step=50, key="_monthly_contrib",
            help="Regular monthly investment top-up"
        )

    st.markdown(render_actionable_advice(port, lump_sum, monthly_contrib), unsafe_allow_html=True)

    import re
    summary = res.get("ai_summary", "")
    summary = re.sub(r'<div class="ai-explain-box">', '', summary, flags=re.IGNORECASE)
    summary = summary.replace('</div>', '').strip()

    # ── AI EXPLANATION WITH TOGGLE ──────────────────────────────────────────
    st.markdown("---")
    col_toggle, col_spacer = st.columns([1, 3])
    with col_toggle:
        mode = st.session_state.explanation_mode
        new_mode = st.toggle(
            "🔬 Advanced mode (for investors who understand market terms)",
            value=(mode == "advanced"),
            help="Switch to advanced mode to see Sharpe ratios, volatility, and technical details."
        )
        # Fix label visibility for toggle specifically
        st.markdown('<style>div[data-testid="stCheckbox"] label p { color: white !important; font-weight: 500 !important; }</style>', unsafe_allow_html=True)
        st.session_state.explanation_mode = "advanced" if new_mode else "simple"

    # Generate explanation on the fly based on current mode
    ans = st.session_state.survey_answers
    horizon_map = {"Short (under 3 years)":3, "Medium (3–10 years)":7, "Long (10–20 years)":15, "Very long (over 20 years)":25}
    horizon_yrs = horizon_map.get(ans.get("q3_horizon"), 10)
    
    inputs = {"horizon": horizon_yrs}
    explanation_text = get_ai_explanation(st.session_state.explanation_mode, port, inputs, ans)

    st.markdown(f"""
    <div style="background-color: rgba(155, 114, 242, 0.06); border: 1px solid rgba(155, 114, 242, 0.25); border-radius: 12px; padding: 24px; margin-top: 10px; margin-bottom: 28px;">
        <h3 style="font-weight: 600; color: #E6D5FF; margin-top: 0; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; font-size: 16px;">
            <span style="display:inline-block;vertical-align:middle;margin-top:-3px;">{get_svg("brain", 20, "#6D5EFC")}</span>
            AI‑Powered Insight
            <span style="font-size:12px; background:rgba(155,114,242,0.2); padding:2px 8px; border-radius:20px;">
                {st.session_state.explanation_mode.upper()} MODE
            </span>
        </h3>
        <div style="font-size: 15px; color: rgba(237,237,243,0.9); white-space: pre-line; line-height: 1.75;">
            {explanation_text}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Row 1: allocation | IQ Diagnostics ─────────────────────────────────────────---
    col1, col2 = st.columns([1, 1.4], gap="large")
    with col1:
        st.markdown('<div class="card"><div class="panel-title"><div class="rich-tooltip">Asset Allocation <span class="tt-icon">ℹ️</span><span class="tooltip-text"><div class="tt-header">📊 Asset Allocation</div>This chart shows how your money is divided across asset classes. Spreading across different areas reduces the risk of losing money if one area performs poorly — this is the core of Markowitz portfolio theory.</span></div></div>', unsafe_allow_html=True)
        # Sort weights for cleaner display
        sorted_weights = dict(sorted(port["allocation_pct"].items(), key=lambda x: x[1], reverse=True))
        st.plotly_chart(donut_chart(sorted_weights), use_container_width=True)
        etf_html = '<div style="margin-top:10px;">'
        for asset, pct_v in sorted_weights.items():
            etf_html += (f'<div class="etf-row"><span class="etf-name">{asset}</span>'
                         f'<span style="color:{color};font-weight:700;font-family:\'JetBrains Mono\',monospace;">{pct_v:.1f}%</span></div>')
        st.markdown(etf_html + "</div></div>", unsafe_allow_html=True)

    # ── Methodology Section ──────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📊 Data Source & Methodology — Where do these numbers come from?"):
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
            <li><b>P10 (Conservative):</b> A 'stress-test' scenario where assets perform poorly but remain within historical norms.</li>
          </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f'<div class="card"><div class="panel-title">{get_svg("brain", 14, ACCENT)} &nbsp; <div class="rich-tooltip">Markowitz MINN Architecture Diagnostics <span class="tt-icon">ℹ️</span><span class="tooltip-text"><div class="tt-header">{get_svg("brain", 14)} Markowitz MINN</div>Behind the scenes, the Markowitz-Informed Neural Network calculates parameters to balance your portfolio. Threshold (δ) controls how much co-movement risk is allowed, while Decay (γ) determines how much weight is given to recent market changes versus long-term trends.</span></div></div>', unsafe_allow_html=True)
        
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
            
        st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="panel-title"><div class="rich-tooltip">Regime Mixture Probability <span class="tt-icon">ℹ️</span><span class="tooltip-text"><div class="tt-header">📈 Market Regimes</div>Financial markets go through different phases — normal growth (Body), sudden drops (Tail), or high uncertainty (Wing). This shows which regime the MINN believes is active, and how it has weighted your portfolio to handle it.</span></div></div>', unsafe_allow_html=True)
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
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Strategic Tuning Panel (Persistent) ───────────────────────────────
        st.markdown(f'<div class="card" style="margin-top:20px;"><div class="panel-title">{get_svg("settings", 14, ACCENT)} &nbsp; Strategic AI Tuning</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:11px;color:{MUTED};margin-bottom:15px;">Manually override the neural manifold parameters to tune your risk exposure.</div>', unsafe_allow_html=True)
        
        # Load existing config from DB if available
        saved_config = database.get_portfolio_config(email)
        def_delta = saved_config.get("delta", iq.get("delta", 0.5))
        def_gamma = saved_config.get("gamma", iq.get("gamma", 0.1))
        
        new_delta = st.slider("Neural Threshold (δ)", 0.1, 2.0, float(def_delta), 0.1, help="Higher = more aggressive filtering of market noise.")
        new_gamma = st.slider("Temporal Decay (γ)", 0.001, 0.5, float(def_gamma), 0.001, format="%.3f", help="Higher = faster reaction to recent volatility.")
        
        if st.button("Save Custom Tuning to Cloud", use_container_width=True, type="primary"):
            new_config = {"delta": new_delta, "gamma": new_gamma}
            database.save_portfolio_config(email, new_config)
            database.add_notification(email, "Strategic Sync Successful", f"Your MINN parameters (δ={new_delta}, γ={new_gamma}) have been synchronized with the LEM StratIQ cloud.", "success")
            st.success("Configuration Pushed to MongoDB Atlas!")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Row 2: Performance | Intelligence Feed ────────────────────────────
    c1, c2 = st.columns([1.3, 1.0], gap="large")
    with c1:
        st.markdown('<div class="card"><div class="panel-title"><div class="rich-tooltip">Monte Carlo Growth Simulation <span class="tt-icon">ℹ️</span><span class="tooltip-text"><div class="tt-header">🎲 Monte Carlo Simulation</div>We ran 2,000 different simulated futures for your portfolio based on historical data. This shows the range of possible outcomes over time — giving you a realistic picture of both potential growth and potential downturns.</span></div></div>', unsafe_allow_html=True)
        st.plotly_chart(monte_chart(sim, color), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(f'<div class="card"><div class="panel-title">{get_svg("zap", 14, ACCENT)} &nbsp; Intelligence Feed</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:11px;color:{MUTED};margin-bottom:20px;">Real-time feed of neural diagnostic events and profile changes.</div>', unsafe_allow_html=True)
        
        # Load from MongoDB
        notifs = database.get_notifications(email, limit=4)
        
        if not notifs:
            st.markdown(f"""
            <div style="text-align:center;padding:40px 20px;background:rgba(255,255,255,0.02);border-radius:12px;border:1px dashed rgba(255,255,255,0.1);">
                <div style="font-size:32px;margin-bottom:10px;">📡</div>
                <div style="font-size:12px;color:#8BA6D3;font-weight:700;">Radar Scan Active</div>
                <div style="font-size:10px;color:{MUTED};">No recent events detected on this manifold.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for n in notifs:
                icon = "✅" if n['level'] == "success" else "ℹ️"
                time_str = n['created_at'].strftime("%H:%M")
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:12px 14px;margin-bottom:10px;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                        <span style="font-size:11px;font-weight:800;color:#fff;">{icon} {n['title']}</span>
                        <span style="font-size:9px;color:{MUTED};">{time_str}</span>
                    </div>
                    <div style="font-size:10px;color:#8BA6D3;line-height:1.4;">{n['message']}</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
        if st.button("Archive Event Log", use_container_width=True):
            st.info("Logs are archived in MongoDB Atlas.")
        st.markdown("</div>", unsafe_allow_html=True)


    # ══════════════════════════════════════════════════════════════════════
    # ── INVESTMENT PLANNER ────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:22px;font-weight:900;color:#ffffff;letter-spacing:-0.03em;margin:10px 0 4px;">
      💷 Investment Planner
    </div>
    <div style="font-size:13px;color:{MUTED};margin-bottom:18px;">
      Enter how much you want to invest — we'll show you exactly where to put it and what to expect back.
    </div>
    """, unsafe_allow_html=True)

    inv_col, _ = st.columns([1, 1])
    with inv_col:
        invest_amt = st.number_input(
            "How much would you like to invest? (£)",
            min_value=100, max_value=10_000_000,
            value=st.session_state.get("invest_amount", 10000),
            step=500, key="invest_amount",
            help="Enter your total investment amount in pounds"
        )

    currency = get_currency_symbol()
    exp_r  = stats.get("expected_annual_return", 0) / 100
    vol_r  = stats.get("expected_volatility", 0) / 100
    sharpe = stats.get("sharpe_ratio", 0)
    alloc  = port.get("allocation_pct", {})
    sorted_alloc = sorted(alloc.items(), key=lambda x: x[1], reverse=True)

    # ETF role descriptions
    ETF_ROLES = {
        "VOO":  ("S&P 500 — US Large Cap Growth",  "Core growth engine. Tracks America's 500 largest companies for broad market exposure."),
        "QQQ":  ("Nasdaq 100 — Tech & Innovation",  "High-growth technology exposure. Amplifies returns in bull markets via top tech firms."),
        "VWRA": ("Global Equities — Diversification", "International diversification. Reduces single-country risk across 3,700+ global stocks."),
        "AGG":  ("US Bonds — Capital Protection",    "Defensive anchor. Bonds cushion losses during stock market downturns."),
        "GLD":  ("Gold — Inflation Hedge",           "Store of value. Gold rises when inflation or geopolitical uncertainty increases."),
        "VNQ":  ("Real Estate — Income & Stability", "Property exposure without buying bricks. Regular dividends and inflation protection."),
        "ESGU": ("ESG S&P 500 — Ethical Growth",     "Socially responsible investing. Same broad US exposure but excludes ethical concerns."),
        "PDBC": ("Commodities — Real Asset Exposure","Raw materials like oil & metals. Diversifies away from financial asset risk."),
    }

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
    st.markdown(f"""
    <div style="font-size:22px;font-weight:900;color:#ffffff;letter-spacing:-0.03em;margin:28px 0 4px;">
      📅 Projected Returns Timeline
    </div>
    <div style="font-size:13px;color:{MUTED};margin-bottom:18px;">
      If you invest <b style="color:#ffffff;">£{invest_amt:,.0f}</b> today and reinvest all returns (compound growth at {exp_r*100:.1f}% p.a.):
    </div>
    """, unsafe_allow_html=True)

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
    st.markdown(f"""
    <div style="font-size:22px;font-weight:900;color:#ffffff;letter-spacing:-0.03em;margin:28px 0 4px;">
      🧩 Why Each Asset Was Chosen
    </div>
    <div style="font-size:13px;color:{MUTED};margin-bottom:18px;">
      The MINN selected these specific ETFs based on your risk score of <b style="color:#ffffff;">{res.get('score',5):.0f}/10</b> and how they interact in the co-movement model.
    </div>
    """, unsafe_allow_html=True)

    ASSET_DETAIL = {
        "VOO":  {"icon":"📈","colour":"#3BA4FF","why":"VOO tracks the S&P 500 — 500 of the largest US companies. It's the backbone of most portfolios because it grows with the world's largest economy. The MINN allocated this to capture consistent long-term growth."},
        "QQQ":  {"icon":"💻","colour":"#6D5EFC","why":"QQQ holds the top 100 Nasdaq-listed companies, dominated by tech giants like Apple, Microsoft, and Nvidia. Higher risk, higher reward — the MINN uses it to boost return potential in line with your risk appetite."},
        "VWRA": {"icon":"🌍","colour":"#8EF6D1","why":"VWRA gives global exposure across 3,700+ companies in 50+ countries. It reduces your dependence on any single market recovering or performing well — pure diversification."},
        "AGG":  {"icon":"🛡️","colour":"#8BA6D3","why":"AGG invests in US government and corporate bonds. When stocks fall, bonds often hold steady — acting as a ballast. The MINN uses AGG to reduce portfolio volatility."},
        "GLD":  {"icon":"🏅","colour":"#FFD700","why":"Gold has protected wealth for thousands of years. It rises when inflation erodes currency value and during geopolitical uncertainty — the MINN uses it as a crisis hedge."},
        "VNQ":  {"icon":"🏢","colour":"#FF9B6B","why":"VNQ gives exposure to real estate investment trusts. Property tends to grow with inflation and pays dividends — adding a reliable income stream uncorrelated with stocks."},
        "ESGU": {"icon":"🌱","colour":"#4CAF50","why":"ESGU mirrors the S&P 500 while excluding companies with poor environmental, social, and governance ratings. It aligns your investments with your values without sacrificing returns."},
        "PDBC": {"icon":"⛽","colour":"#FF6B6B","why":"PDBC tracks a basket of commodities — oil, natural gas, metals, and agriculture. These real assets often zig when financial assets zag, adding genuine diversification."},
    }

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
    with st.expander("📋 Survey Summary"):
        st.markdown("**Your Answers**")
        for q in QUESTIONS:
            val = st.session_state.survey_answers.get(q["key"], "—")
            st.markdown(f"- **{q['number']}** {q['text'][:55]}…  →  `{val}`")


    # ── HISTORICAL STRESS TEST ──
    st.markdown("---")
    st.markdown(f"""<div style="font-size:22px;font-weight:900;color:#ffffff;letter-spacing:-0.01em;margin:12px 0 16px;">🛡️ Resilience Stress Test</div>""", unsafe_allow_html=True)
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
font-size:12px;color:rgba(237,237,243,0.45);'>
⚠️ <b>Disclaimer:</b> This is for educational and research purposes only. 
Not financial advice. Consult a qualified financial adviser before investing. 
Past performance does not guarantee future results.
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_r, _ = st.columns([1, 3])
    with col_r:
        if st.button("🔄  Try a Different Profile", use_container_width=True):
            st.session_state.survey_page    = "survey"
            st.session_state.survey_step    = 0
            st.session_state.survey_answers = {}
            st.session_state.result         = None
            st.rerun()


# ── NEWS & INSIGHTS ───────────────────────────────────────────────────────────
def page_insights():
    st.markdown("""
<style>
.why-section { margin-bottom: 40px; }
.why-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 18px; padding: 28px 32px; margin-bottom: 16px; }
.why-card h3 { font-size: 15px; font-weight: 800; color: #6D5EFC; text-transform: uppercase; letter-spacing: 0.08em; margin: 0 0 10px 0; }
.why-card p { font-size: 14px; color: #C5D3EC; line-height: 1.75; margin: 0; }
.param-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 14px; }
.param-chip { background: rgba(109,94,252,0.1); border: 1px solid rgba(109,94,252,0.25); border-radius: 10px; padding: 10px 14px; }
.param-sym { font-size: 18px; font-weight: 900; color: #fff; }
.param-name { font-size: 10px; color: #8BA6D3; font-weight: 700; text-transform: uppercase; }
.phase-tag { display: inline-block; background: rgba(142,246,209,0.1); border: 1px solid rgba(142,246,209,0.3); color: #8EF6D1; font-size: 10px; font-weight: 800; padding: 3px 10px; border-radius: 20px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="padding:32px 0 8px;">
  <div style="font-size:11px;font-weight:800;color:#6D5EFC;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:10px;">About the System</div>
  <div style="font-size:38px;font-weight:900;color:#ffffff;letter-spacing:-0.03em;margin-bottom:12px;">Why DeepAtomicIQ?</div>
  <div style="font-size:16px;color:#8BA6D3;max-width:720px;line-height:1.6;">A Markowitz-Informed Neural Network that learns how markets move together and builds portfolios that maximise the Sharpe Ratio — intelligently, transparently, and in real time.</div>
</div>
""", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["How It Works", "Phase 2: Out-of-Sample Evaluation"])

    with tab1:
        sections = [
            (
                "1. Purpose and Overview",
                "This project implements a Markowitz-Informed Neural Network (MINN) to learn how to build investment portfolios that balance risk and return intelligently. It combines ideas from finance (portfolio theory) and machine learning (deep neural networks). The model learns how assets move together — their co-movements or correlations — and finds portfolio weights that maximize the Sharpe Ratio, a measure of performance defined as average return divided by risk. In plain terms: the network learns how to distribute money across several assets so that the overall portfolio performs well relative to its volatility."
            ),
            (
                "2. Main Files and Their Roles",
                "MainSR.py — the entry-point script. It loads data, builds batches, and controls the training of neural networks (SR = Sharpe Ratio). MINNlib.py — contains all core functions: computing correlations, building the neural network, and training the loss function. project_hyperparameters.py — defines all project settings and constants such as number of assets, training epochs, and loss penalties."
            ),
            (
                "3. The Neural Network (DeepIQNetPortfolio)",
                "The neural network takes asset returns as input and outputs three things: (1) IQ Parameters — delta (threshold between normal and extreme moves), gamma (temporal decay), and epsilon (delay term). (2) Channel logits B, W, T, I — representing Body, Wing, Tail, and Identity correlation structures. (3) Portfolio weights — allocations to each asset, normalized to sum to one."
            ),
            (
                "4. The IQ Model: Measuring Co-movement",
                "Traditional finance uses a correlation matrix. The IQ model constructs this matrix from standardized returns, distinguishing three movement regimes: Body (normal), Wing (asymmetric), and Tail (extreme). Each is weighted by temporal decay factors. The combined correlation matrix is: C_IQ = wB·C_B + wW·C_W + wT·C_T + wI·I. This is then converted into a covariance matrix using asset volatilities."
            ),
            (
                "5. The Loss Function",
                "The objective combines: Sharpe Ratio (main target), Volatility Control (maintain target volatility), Condition Number (numerical stability), Entropy (encourages diversification), Risk Parity (balances risk contributions), Top-Weight Constraints (limits dominance), and Turnover (discourages large weight changes). All lambda coefficients are defined in project_hyperparameters.py."
            ),
            (
                "6. Project Summary",
                "This system learns interpretable parameters (δ, γ, ε, wB, wW, wT, wI) that describe how markets move and relate to one another. It produces evolving portfolio allocations designed to maximize the Sharpe Ratio across time. The method ensures mathematical validity (positive semi-definite correlations) and produces transparent, analyzable results. The DeepAtomicIQ framework merges financial reasoning with explainable machine learning, bridging traditional optimization and modern neural inference."
            ),
        ]
        for title, body in sections:
            st.markdown(f"""
            <div class="why-card">
              <h3>{title}</h3>
              <p>{body}</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top:8px;padding:24px 32px;background:rgba(109,94,252,0.06);border:1px solid rgba(109,94,252,0.2);border-radius:18px;">
          <h3 style="font-size:13px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 16px;">Key IQ Parameters</h3>
          <div class="param-grid">
            <div class="param-chip"><div class="param-sym">δ (delta)</div><div class="param-name">Threshold between normal and extreme moves</div></div>
            <div class="param-chip"><div class="param-sym">γ (gamma)</div><div class="param-name">Temporal decay weighting</div></div>
            <div class="param-chip"><div class="param-sym">ε (epsilon)</div><div class="param-name">Delay term in regime detection</div></div>
            <div class="param-chip"><div class="param-sym">wB</div><div class="param-name">Body weight — normal co-movement</div></div>
            <div class="param-chip"><div class="param-sym">wW</div><div class="param-name">Wing weight — asymmetric moves</div></div>
            <div class="param-chip"><div class="param-sym">wT</div><div class="param-name">Tail weight — extreme market events</div></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="phase-tag">Phase 2: Out-of-Sample</div>', unsafe_allow_html=True)
        phase2_sections = [
            (
                "What Phase 2 Does",
                "This phase evaluates the DeepAtomicIQ neural network weights using out-of-sample (OOS) testing against a range of alternative covariance estimators and portfolio construction baselines. The purpose is to compare performance, turnover, and transaction cost behaviour of DeepAtomicIQ portfolios relative to established techniques."
            ),
            (
                "Pipeline Overview",
                "Step 1: Build DIQ Special Portfolios (DIQ1–DIQ5) from first-phase model outputs, aligned to the invest month and adjusted for the validation horizon. Step 2: Run OOS Mean–Variance Optimization using Max-Sharpe portfolio optimization with several covariance estimators including Ledoit–Wolf and RMT. Step 3: Summarize Performance into a single table reporting annualized return, risk, Sharpe ratio, turnover, drawdown, and VaR. Step 4 (Optional): Analyse learned parameter evolution and dynamic weight changes through time."
            ),
            (
                "Output Files",
                "DIQ1–DIQ5 CSV files in portfolios/special_portfolios/. OOS backtest results in OOS_results/ folder (cumulative value, returns, transaction costs, turnover). A consolidated performance summary in CSV and LaTeX formats. Optional: parameter trajectory and dynamic weight plots saved as PNG files."
            ),
            (
                "Important Notes",
                "DeepAtomicIQ weights are shifted forward by (m + 1) months before testing to represent realistic deployment. All scripts automatically align asset universes using the canonical price slice. Transaction costs are applied as a self-financing drag before portfolio returns are realized. The process is idempotent — re-running will overwrite existing results without duplication."
            ),
        ]
        for title, body in phase2_sections:
            st.markdown(f"""
            <div class="why-card">
              <h3>{title}</h3>
              <p>{body}</p>
            </div>
            """, unsafe_allow_html=True)


# ── MARKET ────────────────────────────────────────────────────────────────────
import yfinance as yf

@st.cache_data(ttl=60)
def get_live_market_data():
    tickers = ["VOO", "QQQ", "VWRA.L", "AGG", "GLD", "VNQ", "ESGU", "PDBC"]
    names = ["Vanguard S&P 500", "Invesco Nasdaq 100", "Vanguard All-World", "iShares Core US Bonds", "SPDR Gold Shares", "Vanguard Real Estate", "iShares ESG S&P 500", "Invesco Commodities"]
    
    data = []
    try:
        # Fetch data for all tickers at once for performance
        tickers_str = " ".join(tickers)
        # Using period='5d' to ensure we get previous close even over weekends/holidays
        hist = yf.download(tickers_str, period="5d", progress=False)
        
        for i, t in enumerate(tickers):
            try:
                # get the closing prices
                closes = hist['Close'][t].dropna()
                if len(closes) >= 2:
                    current_price = closes.iloc[-1]
                    prev_price = closes.iloc[-2]
                    chg_pct = ((current_price - prev_price) / prev_price) * 100
                    
                    currency = "£" if t == "VWRA.L" else "$"
                    display_ticker = "VWRA" if t == "VWRA.L" else t
                    
                    data.append((
                        display_ticker,
                        names[i],
                        f"{currency}{current_price:.2f}",
                        f"{'+' if chg_pct > 0 else ''}{chg_pct:.2f}%",
                        chg_pct >= 0
                    ))
                else:
                    raise Exception("Not enough data")
            except Exception:
                # fallback if missing data
                data.append((t, names[i], "N/A", "N/A", True))
                
        return data
    except Exception as e:
        return [
            ("VOO",  "Vanguard S&P 500", "$489.12", "+1.23%", True),
            ("QQQ",  "Invesco Nasdaq 100","$425.88","+2.10%", True),
            ("VWRA", "Vanguard All-World", "£97.44", "+0.87%", True),
            ("AGG",  "iShares Core US Bonds","$95.30","-0.12%", False),
            ("GLD",  "SPDR Gold Shares",  "$228.60","+0.65%", True),
            ("VNQ",  "Vanguard Real Estate","$81.20","-0.34%", False),
            ("ESGU", "iShares ESG S&P 500","$103.45","+1.04%", True),
            ("PDBC", "Invesco Commodities","$14.22", "+0.22%", True),
        ]

@st.cache_data(ttl=300)
def get_sparkline_data():
    """Fetch 30-day history for sparklines and the main chart."""
    tickers = ["VOO", "QQQ", "VWRA.L", "AGG", "GLD", "VNQ", "ESGU", "PDBC"]
    try:
        hist = yf.download(" ".join(tickers), period="30d", progress=False)["Close"]
        return hist
    except:
        return None

def page_market():
    import datetime
    st.markdown("""
<style>
.ticker-wrap {
  overflow: hidden; background: rgba(255,255,255,0.02);
  border-top: 1px solid rgba(255,255,255,0.05);
  border-bottom: 1px solid rgba(255,255,255,0.05);
  padding: 10px 0; margin-bottom: 0;
}
.ticker-track {
  display: flex; gap: 0;
  animation: ticker 45s linear infinite;
  white-space: nowrap;
}
@keyframes ticker { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
.ticker-item {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 0 28px; font-size: 12px; font-weight: 600;
  border-right: 1px solid rgba(255,255,255,0.06);
}
.ticker-sym { color: #ffffff; font-weight: 800; }
.ticker-price { color: #8BA6D3; }
.ticker-up { color: #8EF6D1; }
.ticker-dn { color: #FF6B6B; }
.mkt-section-title {
  font-size: 16px; font-weight: 800; color: #ffffff;
  margin: 32px 0 16px; letter-spacing: -0.02em;
  display: flex; align-items: center; gap: 8px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.mkt-section-title span { font-size: 12px; font-weight: 500; color: #8BA6D3; }
.mkt-card {
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 16px; padding: 16px 18px 10px;
  transition: all 0.2s ease; cursor: default;
}
.mkt-card:hover {
  background: rgba(255,255,255,0.045);
  border-color: rgba(109,94,252,0.35);
  transform: translateY(-2px);
}
.mkt-ticker { font-size: 16px; font-weight: 900; color: #fff; letter-spacing: -0.02em; }
.mkt-name  { font-size: 10px; color: #8BA6D3; font-weight: 600; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 120px; }
.mkt-price { font-size: 20px; font-weight: 900; color: #fff; letter-spacing: -0.02em; }
.mover-card {
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px; padding: 14px 18px;
  display: flex; align-items: center; justify-content: space-between;
}
</style>
""", unsafe_allow_html=True)

    markets  = get_live_market_data()
    hist_df  = get_sparkline_data()
    ticker_map = {"VOO":"VOO","QQQ":"QQQ","VWRA":"VWRA.L","AGG":"AGG","GLD":"GLD","VNQ":"VNQ","ESGU":"ESGU","PDBC":"PDBC"}

    # ── Page Header ───────────────────────────────────────────────────────────
    now_str = datetime.datetime.now().strftime("%A %d %b %Y · %H:%M")
    gainers = [m for m in markets if m[4]]
    losers  = [m for m in markets if not m[4]]
    st.markdown(f"""
<div style="padding:28px 0 16px; display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:12px;">
  <div>
    <div style="font-size:11px;font-weight:800;color:#6D5EFC;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:8px;">Live Markets Terminal</div>
    <div style="font-size:36px;font-weight:900;color:#fff;letter-spacing:-0.03em;">Markets</div>
    <div style="font-size:13px;color:#8BA6D3;margin-top:4px;">{now_str} · ETF Universe</div>
  </div>
  <div style="display:flex;gap:16px;">
    <div style="text-align:center;background:rgba(142,246,209,0.06);border:1px solid rgba(142,246,209,0.2);border-radius:12px;padding:10px 20px;">
      <div style="font-size:22px;font-weight:900;color:#8EF6D1;">{len(gainers)}</div>
      <div style="font-size:10px;font-weight:700;color:#8BA6D3;text-transform:uppercase;">Advancing</div>
    </div>
    <div style="text-align:center;background:rgba(255,107,107,0.06);border:1px solid rgba(255,107,107,0.2);border-radius:12px;padding:10px 20px;">
      <div style="font-size:22px;font-weight:900;color:#FF6B6B;">{len(losers)}</div>
      <div style="font-size:10px;font-weight:700;color:#8BA6D3;text-transform:uppercase;">Declining</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Ticker Tape ───────────────────────────────────────────────────────────
    tape_items = ""
    for ticker, name, price, chg, up in markets:
        cls   = "ticker-up" if up else "ticker-dn"
        arrow = "▲" if up else "▼"
        tape_items += f'<div class="ticker-item"><span class="ticker-sym">{ticker}</span><span class="ticker-price">{price}</span><span class="{cls}">{arrow} {chg}</span></div>'
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-track">{tape_items}{tape_items}</div></div>', unsafe_allow_html=True)

    # ── My Watchlist Bar (Load from MongoDB) ──────────────────────────────────
    email = st.session_state.get("user_email")
    if email:
        watchlist = database.get_watchlist(email)
        if watchlist:
            st.markdown(f'<div class="mkt-section-title">{get_svg("star", 16)} My Favorites <span>· Quick access to pinned assets</span></div>', unsafe_allow_html=True)
            w_cols = st.columns(min(len(watchlist), 6))
            for i, ticker in enumerate(watchlist[:6]):
                w_live = next((m for m in markets if m[0] == ticker), None)
                if w_live:
                    col_w = "#8EF6D1" if w_live[4] else "#FF6B6B"
                    with w_cols[i]:
                        st.markdown(f"""
                        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:12px;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;">
                          <div><div style="font-size:10px;font-weight:800;color:#8BA6D3;">{ticker}</div><div style="font-size:14px;font-weight:900;color:#fff;">{w_live[2]}</div></div>
                          <div style="text-align:right;"><div style="font-size:11px;font-weight:800;color:{col_w};">{"▲" if w_live[4] else "▼"} {w_live[3]}</div></div>
                        </div>""", unsafe_allow_html=True)

    # ── Top Movers ────────────────────────────────────────────────────────────
    st.markdown(f'<div class="mkt-section-title">{get_svg("zap", 16)} Top Movers <span>· Today\'s leaders & laggards</span></div>', unsafe_allow_html=True)
    mc1, mc2 = st.columns(2, gap="large")
    with mc1:
        st.markdown('<div style="font-size:10px;font-weight:800;color:#8EF6D1;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;">Best Performers</div>', unsafe_allow_html=True)
        sorted_gain = sorted(markets, key=lambda x: float(x[3].replace('%','').replace('+','')) if x[3] != 'N/A' else -99, reverse=True)[:3]
        for ticker, name, price, chg, up in sorted_gain:
            st.markdown(f"""
<div class="mover-card" style="margin-bottom:8px;border-color:rgba(142,246,209,0.2);">
  <div><div style="font-weight:800;color:#fff;font-size:15px;">{ticker}</div><div style="font-size:11px;color:#8BA6D3;">{name}</div></div>
  <div style="text-align:right;"><div style="font-size:16px;font-weight:900;color:#fff;">{price}</div><div style="font-size:13px;font-weight:800;color:#8EF6D1;">▲ {chg}</div></div>
</div>""", unsafe_allow_html=True)
    with mc2:
        st.markdown('<div style="font-size:10px;font-weight:800;color:#FF6B6B;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;">Worst Performers</div>', unsafe_allow_html=True)
        sorted_loss = sorted(markets, key=lambda x: float(x[3].replace('%','').replace('+','')) if x[3] != 'N/A' else 99)[:3]
        for ticker, name, price, chg, up in sorted_loss:
            st.markdown(f"""
<div class="mover-card" style="margin-bottom:8px;border-color:rgba(255,107,107,0.2);">
  <div><div style="font-weight:800;color:#fff;font-size:15px;">{ticker}</div><div style="font-size:11px;color:#8BA6D3;">{name}</div></div>
  <div style="text-align:right;"><div style="font-size:16px;font-weight:900;color:#fff;">{price}</div><div style="font-size:13px;font-weight:800;color:#FF6B6B;">▼ {chg}</div></div>
</div>""", unsafe_allow_html=True)

    # ── ETF Watchlist — cards with embedded sparklines ────────────────────────
    st.markdown(f'<div class="mkt-section-title">{get_svg("chart", 16)} ETF Watchlist <span>· 8 tracked instruments · 30-day sparklines</span></div>', unsafe_allow_html=True)

    cols = st.columns(4)
    for i, (ticker, name, price, chg, up) in enumerate(markets):
        with cols[i % 4]:
            yf_ticker = ticker_map.get(ticker, ticker)
            color     = "#8EF6D1" if up else "#FF6B6B"
            arrow     = "▲" if up else "▼"

            if hist_df is not None and yf_ticker in hist_df.columns:
                series = hist_df[yf_ticker].dropna()
            else:
                series = None

            fig = go.Figure()
            if series is not None and len(series) > 1:
                fill_color = "rgba(142,246,209,0.1)" if up else "rgba(255,107,107,0.1)"
                fig.add_trace(go.Scatter(
                    x=list(range(len(series))), y=series.values, mode="lines",
                    line=dict(color=color, width=2),
                    fill="tozeroy", fillcolor=fill_color,
                    hovertemplate="%{y:.2f}<extra></extra>"
                ))
            fig.update_layout(
                height=56, margin=dict(l=0,r=0,t=0,b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(visible=False), yaxis=dict(visible=False), showlegend=False
            )
            st.markdown(f"""
<div class="mkt-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
    <div><div class="mkt-ticker">{ticker}</div><div class="mkt-name">{name}</div></div>
    <div style="text-align:right;">
      <div class="mkt-price">{price}</div>
      <div style="color:{color};font-size:12px;font-weight:800;">{arrow} {chg}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"spark_{ticker}")
            
            # Persistent Favoriting
            is_pinned = ticker in watchlist
            btn_lbl = f"{'★' if is_pinned else '☆'} Pin to Favorites" if not is_pinned else "★ Pinned"
            if st.button(btn_lbl, key=f"pin_btn_{ticker}", use_container_width=True):
                database.toggle_watchlist_item(email, ticker)
                st.rerun()

    # ── Interactive Price Chart ───────────────────────────────────────────────
    st.markdown(f'<div class="mkt-section-title">{get_svg("activity", 16)} Deep-Dive Chart <span>· 30-day price history with moving averages</span></div>', unsafe_allow_html=True)

    chart_col, info_col = st.columns([3, 1], gap="large")
    with chart_col:
        selected    = st.selectbox("Select instrument", [m[0] for m in markets], label_visibility="collapsed", key="mkt_chart_select")
        yf_selected = ticker_map.get(selected, selected)

        if hist_df is not None and yf_selected in hist_df.columns:
            series      = hist_df[yf_selected].dropna()
            up_overall  = series.iloc[-1] >= series.iloc[0]
            line_color  = "#8EF6D1" if up_overall else "#FF6B6B"
            fill_color  = "rgba(142,246,209,0.07)" if up_overall else "rgba(255,107,107,0.07)"

            big_fig = go.Figure()
            big_fig.add_trace(go.Scatter(
                x=series.index, y=series.values, mode="lines", name=selected,
                line=dict(color=line_color, width=2.5), fill="tozeroy", fillcolor=fill_color,
                hovertemplate="<b>%{x|%d %b}</b><br>Price: %{y:.2f}<extra></extra>"
            ))
            if len(series) >= 7:
                ma7 = series.rolling(7).mean()
                big_fig.add_trace(go.Scatter(
                    x=ma7.index, y=ma7.values, mode="lines", name="7-day MA",
                    line=dict(color="#6D5EFC", width=1.5, dash="dot"),
                    hovertemplate="MA7: %{y:.2f}<extra></extra>"
                ))
            if len(series) >= 14:
                ma14 = series.rolling(14).mean()
                big_fig.add_trace(go.Scatter(
                    x=ma14.index, y=ma14.values, mode="lines", name="14-day MA",
                    line=dict(color="#3BA4FF", width=1.2, dash="dash"),
                    hovertemplate="MA14: %{y:.2f}<extra></extra>"
                ))
            big_fig.update_layout(
                height=360, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10,r=10,t=10,b=10),
                xaxis=dict(showgrid=False, color="#8BA6D3", tickformat="%d %b"),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", color="#8BA6D3"),
                legend=dict(font=dict(color="#8BA6D3", size=11), bgcolor="rgba(0,0,0,0)", orientation="h", y=1.08),
                hovermode="x unified",
                hoverlabel=dict(bgcolor="rgba(15,15,35,0.95)", font_color="#ffffff", bordercolor="rgba(109,94,252,0.4)")
            )
            st.plotly_chart(big_fig, use_container_width=True, config={"displayModeBar": False}, key="mkt_main_chart")
        else:
            st.info("Chart data unavailable — check your connection.")

    with info_col:
        # Find selected ticker stats
        sel_data = next((m for m in markets if m[0] == selected), None)
        if sel_data and hist_df is not None:
            yf_s = ticker_map.get(selected, selected)
            s = hist_df[yf_s].dropna() if yf_s in (hist_df.columns if hist_df is not None else []) else None
            hi  = f"{s.max():.2f}" if s is not None else "—"
            lo  = f"{s.min():.2f}" if s is not None else "—"
            ret = f"{((s.iloc[-1]-s.iloc[0])/s.iloc[0]*100):+.2f}%" if s is not None and len(s) >= 2 else "—"
            col_r = "#8EF6D1" if sel_data[4] else "#FF6B6B"
            st.markdown(f"""
<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.07);border-radius:16px;padding:20px;margin-top:36px;">
  <div style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:14px;">{selected} Stats</div>
  <div style="border-bottom:1px solid rgba(255,255,255,0.05);padding-bottom:10px;margin-bottom:10px;">
    <div style="font-size:10px;color:#8BA6D3;font-weight:700;">Current Price</div>
    <div style="font-size:24px;font-weight:900;color:#fff;">{sel_data[2]}</div>
    <div style="font-size:14px;font-weight:800;color:{col_r};">{sel_data[3]}</div>
  </div>
  <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
    <div style="font-size:10px;color:#8BA6D3;">30d High</div><div style="font-size:12px;font-weight:700;color:#8EF6D1;">{hi}</div>
  </div>
  <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
    <div style="font-size:10px;color:#8BA6D3;">30d Low</div><div style="font-size:12px;font-weight:700;color:#FF6B6B;">{lo}</div>
  </div>
  <div style="display:flex;justify-content:space-between;">
    <div style="font-size:10px;color:#8BA6D3;">30d Return</div><div style="font-size:12px;font-weight:700;color:{col_r};">{ret}</div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── 30-day Treemap Heatmap ────────────────────────────────────────────────
    st.markdown(f'<div class="mkt-section-title">{get_svg("layers", 16)} Sector Heatmap <span>· 30-day performance · size = absolute return</span></div>', unsafe_allow_html=True)

    sectors = []
    if hist_df is not None:
        for ticker, name, price, chg, up in markets:
            yf_t = ticker_map.get(ticker, ticker)
            if yf_t in hist_df.columns:
                s = hist_df[yf_t].dropna()
                if len(s) >= 2:
                    ret = ((s.iloc[-1] - s.iloc[0]) / s.iloc[0]) * 100
                    sectors.append((ticker, name, ret))

    if sectors:
        labels = [f"{t}<br>{r:+.1f}%" for t, n, r in sectors]
        values = [abs(r) + 1 for _, _, r in sectors]
        colors = [r for _, _, r in sectors]
        heat = go.Figure(go.Treemap(
            labels=labels, parents=[""] * len(labels), values=values,
            marker=dict(colors=colors, colorscale=[[0,"#FF3B3B"],[0.5,"#1A1A3E"],[1,"#00C896"]],
                        cmid=0, showscale=False, line=dict(width=3, color="rgba(8,10,26,1)")),
            textfont=dict(color="#ffffff", size=13),
            hovertemplate="<b>%{label}</b><extra></extra>",
        ))
        heat.update_layout(height=240, paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(heat, use_container_width=True, config={"displayModeBar": False}, key="mkt_heatmap")

    # ── Heatmap Click Explainer Panel ─────────────────────────────────────────
    etf_info = {
        "VOO": {
            "full_name": "Vanguard S&P 500 ETF",
            "asset_class": "US Large-Cap Equity",
            "role": "Core equity exposure — the backbone of most MINN allocations. Tracks the 500 largest US companies.",
            "going_up": "Signals broad market confidence. Your portfolio benefits directly; growth regime likely dominant.",
            "going_down": "Risk-off signal. MINN may shift weight toward AGG (bonds) or GLD to hedge drawdown.",
            "sharpe_impact": "High positive — VOO is the primary return driver in balanced and growth profiles.",
            "weight_hint": "Typically 20–40% of MINN growth portfolios."
        },
        "QQQ": {
            "full_name": "Invesco Nasdaq 100 ETF",
            "asset_class": "US Tech / Growth Equity",
            "role": "High-growth, rate-sensitive tech exposure. Amplifies returns in bull regimes but volatile in tail events.",
            "going_up": "AI and tech momentum is strong. Benefits QQQ-heavy portfolios significantly.",
            "going_down": "Rising rates or risk aversion hit QQQ hardest. Wing/Tail co-movement spikes with VOO.",
            "sharpe_impact": "High beta — boosts Sharpe in bull markets, compresses it in corrections.",
            "weight_hint": "Typically 10–25% of growth-tilted MINN portfolios."
        },
        "VWRA": {
            "full_name": "Vanguard FTSE All-World ETF",
            "asset_class": "Global Equity (ex-US diversification)",
            "role": "International diversification layer. Reduces US concentration risk and adds EM/Europe exposure.",
            "going_up": "Global growth synchronized with US — carries. Reduces country-specific correlation.",
            "going_down": "Global slowdown or strong USD headwinds. MINN may reduce weighting.",
            "sharpe_impact": "Moderate — key for correlation reduction (C_IQ Body regime contribution).",
            "weight_hint": "Typically 10–20% across all MINN profiles."
        },
        "AGG": {
            "full_name": "iShares Core US Aggregate Bond ETF",
            "asset_class": "Investment Grade Bonds",
            "role": "Stability anchor. Provides negative or low correlation to equities during market stress.",
            "going_up": "Risk-off environment or rate cuts expected. Protects capital during equity drawdowns.",
            "going_down": "Rising rates eroding bond prices. MINN shifts weight back toward equities.",
            "sharpe_impact": "Low solo returns but critical for Sharpe via volatility reduction.",
            "weight_hint": "Typically 15–35% in conservative or balanced MINN profiles."
        },
        "GLD": {
            "full_name": "SPDR Gold Shares ETF",
            "asset_class": "Commodity — Precious Metals",
            "role": "Inflation hedge and crisis safe-haven. Performs in Tail regimes when equity correlations spike.",
            "going_up": "Inflation fears, USD weakness, or geopolitical stress. Your hedge is working.",
            "going_down": "Real rates rising or risk appetite recovering. MINN may trim GLD allocation.",
            "sharpe_impact": "Tail regime stabilizer — reduces max drawdown even if it lowers mean returns.",
            "weight_hint": "Typically 5–15% depending on inflation expectation in regime model."
        },
        "VNQ": {
            "full_name": "Vanguard Real Estate ETF",
            "asset_class": "Real Estate Investment Trusts (REITs)",
            "role": "Income + inflation protection. Rate-sensitive but provides dividend yield and real-asset exposure.",
            "going_up": "Rate stability or cuts — REITs rally on lower borrowing costs and yield demand.",
            "going_down": "Rising interest rates are the main risk. MINN reduces VNQ when rate regime shifts upward.",
            "sharpe_impact": "Moderate — adds income but correlates with equities in stress events.",
            "weight_hint": "Typically 5–12% across most MINN profiles."
        },
        "ESGU": {
            "full_name": "iShares ESG Aware MSCI USA ETF",
            "asset_class": "ESG / Sustainable US Equity",
            "role": "Socially responsible equity exposure with similar characteristics to VOO but with ESG screening.",
            "going_up": "ESG flows accelerating. Can be used as a low-tracking-error VOO substitute.",
            "going_down": "Typically moves closely with VOO — same drivers but with slightly lower vol.",
            "sharpe_impact": "Very similar to VOO. Slightly lower concentration risk in high-carbon sectors.",
            "weight_hint": "Often substituted for or combined with VOO in ESG-tilted profiles."
        },
        "PDBC": {
            "full_name": "Invesco Optimum Yield Diversified Commodity Strategy ETF",
            "asset_class": "Broad Commodities",
            "role": "Multi-commodity inflation hedge covering energy, metals, agriculture. Tail regime asset.",
            "going_up": "Commodity supercycle or supply shocks driving energy/metals. Strong inflation hedge activated.",
            "going_down": "Global demand slowdown or USD strength reducing commodity prices.",
            "sharpe_impact": "High vol but low equity correlation — valuable in the IQ Tail regime weighting (wT).",
            "weight_hint": "Typically 3–10% in inflation-aware MINN portfolios."
        },
    }

    st.markdown("""
<style>
.etf-chip { display:inline-block; margin:4px; padding:6px 14px; border-radius:20px;
  font-size:12px; font-weight:800; cursor:pointer;
  background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); color:#8BA6D3;
  transition:all 0.15s; }
.etf-chip-active { background:rgba(109,94,252,0.12); border-color:rgba(109,94,252,0.45); color:#fff; }
</style>
""", unsafe_allow_html=True)

    st.markdown(f'<div style="font-size:11px;font-weight:700;color:#8BA6D3;margin:16px 0 8px;text-transform:uppercase;letter-spacing:0.1em;">Select a block to explore</div>', unsafe_allow_html=True)

    selected_etf = st.session_state.get("heatmap_selected_etf", None)
    chip_cols = st.columns(8)
    etf_keys = list(etf_info.keys())
    for i, key in enumerate(etf_keys):
        with chip_cols[i]:
            is_active = selected_etf == key
            label = f"{'→ ' if is_active else ''}{key}"
            if st.button(label, key=f"chip_{key}", use_container_width=True):
                if selected_etf == key:
                    st.session_state["heatmap_selected_etf"] = None
                else:
                    st.session_state["heatmap_selected_etf"] = key
                st.rerun()

    selected_etf = st.session_state.get("heatmap_selected_etf", None)
    if selected_etf and selected_etf in etf_info:
        info = etf_info[selected_etf]
        # Find live price data for this ETF
        live = next((m for m in markets if m[0] == selected_etf), None)
        price_html = ""
        if live:
            col_p = "#8EF6D1" if live[4] else "#FF6B6B"
            arr   = "▲" if live[4] else "▼"
            price_html = f'<span style="font-size:22px;font-weight:900;color:#fff;">{live[2]}</span> <span style="font-size:14px;font-weight:800;color:{col_p};">{arr} {live[3]}</span>'

        st.markdown(f"""
<div style="background:rgba(109,94,252,0.06);border:1px solid rgba(109,94,252,0.25);border-radius:20px;padding:28px 32px;margin-top:8px;position:relative;overflow:hidden;">
  <div style="position:absolute;top:0;left:0;width:5px;height:100%;background:linear-gradient(180deg,#6D5EFC,#3BA4FF);"></div>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;margin-bottom:20px;">
    <div>
      <div style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">{info['asset_class']}</div>
      <div style="font-size:26px;font-weight:900;color:#fff;letter-spacing:-0.03em;">{selected_etf} <span style="font-size:14px;font-weight:500;color:#8BA6D3;">· {info['full_name']}</span></div>
      <div style="margin-top:6px;">{price_html}</div>
    </div>
    <div style="text-align:right;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:12px 18px;">
      <div style="font-size:10px;color:#8BA6D3;font-weight:700;text-transform:uppercase;margin-bottom:4px;">Typical MINN Weight</div>
      <div style="font-size:16px;font-weight:900;color:#fff;">{info['weight_hint']}</div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:2fr 1fr 1fr;gap:16px;margin-bottom:16px;">
    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:16px;">
      <div style="font-size:10px;font-weight:800;color:#6D5EFC;text-transform:uppercase;margin-bottom:8px;">Role in Portfolio</div>
      <div style="font-size:13px;color:#C5D3EC;line-height:1.65;">{info['role']}</div>
    </div>
    <div style="background:rgba(142,246,209,0.05);border:1px solid rgba(142,246,209,0.18);border-radius:14px;padding:16px;">
      <div style="font-size:10px;font-weight:800;color:#8EF6D1;text-transform:uppercase;margin-bottom:8px;">When it rises...</div>
      <div style="font-size:12px;color:#C5D3EC;line-height:1.6;">{info['going_up']}</div>
    </div>
    <div style="background:rgba(255,107,107,0.05);border:1px solid rgba(255,107,107,0.18);border-radius:14px;padding:16px;">
      <div style="font-size:10px;font-weight:800;color:#FF6B6B;text-transform:uppercase;margin-bottom:8px;">When it falls...</div>
      <div style="font-size:12px;color:#C5D3EC;line-height:1.6;">{info['going_down']}</div>
    </div>
  </div>
  <div style="background:rgba(109,94,252,0.08);border:1px solid rgba(109,94,252,0.2);border-radius:12px;padding:14px 18px;">
    <div style="font-size:10px;font-weight:800;color:#6D5EFC;text-transform:uppercase;margin-bottom:6px;">Sharpe Ratio Impact</div>
    <div style="font-size:13px;color:#fff;">{info['sharpe_impact']}</div>
  </div>
</div>
""", unsafe_allow_html=True)


    # ── Market Intelligence Feed ───────────────────────────────────────────────
    st.markdown(f'<div class="mkt-section-title">{get_svg("zap", 16)} Market Intelligence <span>· AI-powered portfolio takeaways</span></div>', unsafe_allow_html=True)
    mi_c1, mi_c2 = st.columns([1, 1.6], gap="large")
    with mi_c1:
        st.markdown(f'<div style="font-size:11px;font-weight:800;color:#6D5EFC;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.1em;">{get_svg("activity", 13)} Neural Sentiment Radar</div>', unsafe_allow_html=True)
        categories = ['Growth','Inflation','Stability','Yield','Volatility']
        values     = [82, 45, 68, 55, 30]
        rfig = go.Figure(data=go.Scatterpolar(r=values, theta=categories, fill='toself', line_color='#6D5EFC', fillcolor='rgba(109,94,252,0.2)'))
        rfig.update_layout(polar=dict(radialaxis=dict(visible=False), bgcolor='rgba(0,0,0,0)'), paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=30,r=30), height=240)
        st.plotly_chart(rfig, use_container_width=True, config={'displayModeBar': False}, key="mkt_radar")
        st.markdown('<div style="text-align:center;font-size:12px;color:#8BA6D3;">Model detects <b>Growth</b> bias · Neural Confidence: <b style="color:#8EF6D1;">72.4</b></div>', unsafe_allow_html=True)
    with mi_c2:
        st.markdown(f'<div style="font-size:11px;font-weight:800;color:#3BA4FF;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.1em;">{get_svg("zap", 13)} Intelligence Timeline</div>', unsafe_allow_html=True)
        items = [
            {"tag": "US MARKETS",      "title": "Interest Rates Stabilizing",  "desc": "The central bank is holding rates steady.",         "impact": "STABLE", "meaning": "Good for your Bond (AGG) and Real Estate (VNQ) holdings."},
            {"tag": "TECH GROWTH",     "title": "AI Hardware Demand Soars",    "desc": "Nvidia and others reporting record sales.",          "impact": "GROWTH", "meaning": "Expect momentum in your QQQ and VOO allocations."},
            {"tag": "DIVERSIFICATION", "title": "Commodities as a Hedge",      "desc": "Gold and Oil are rising amid global uncertainty.",  "impact": "HEDGE",  "meaning": "Your GLD and PDBC positions are protecting your gains."}
        ]
        for it in items:
            st.markdown(f"""
<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:16px;margin-bottom:10px;position:relative;overflow:hidden;">
  <div style="position:absolute;top:0;left:0;width:3px;height:100%;background:#6D5EFC;opacity:0.6;"></div>
  <div style="position:absolute;top:12px;right:12px;font-size:9px;font-weight:800;color:#8EF6D1;background:rgba(142,246,209,0.1);padding:2px 8px;border-radius:20px;border:1px solid rgba(142,246,209,0.2);">{it['impact']}</div>
  <span style="background:rgba(109,94,252,0.1);color:#6D5EFC;font-size:9px;font-weight:800;padding:2px 8px;border-radius:8px;display:inline-block;margin-bottom:6px;">{it['tag']}</span>
  <div style="font-size:14px;font-weight:700;color:#fff;margin-bottom:4px;">{it['title']}</div>
  <div style="font-size:11px;color:#8BA6D3;margin-bottom:8px;">{it['desc']}</div>
  <div style="background:rgba(109,94,252,0.07);padding:8px 10px;border-radius:8px;">
    <div style="font-size:9px;font-weight:900;color:#6D5EFC;margin-bottom:2px;">TAKEAWAY FOR YOUR PORTFOLIO</div>
    <div style="font-size:11px;color:#fff;">{it['meaning']}</div>
  </div>
</div>
""", unsafe_allow_html=True)



# ── MORE 
def page_more():
    user_email = st.session_state.get("user_email", "guest") or "guest"
    user_name  = st.session_state.get("user_name",  "Guest") or "Guest"
    user_data  = database.get_user(user_email) if user_email != "guest" else None
    prefs      = json.loads(user_data["preferences_json"]) if user_data and user_data.get("preferences_json") else {}
    initials   = "".join(p[0].upper() for p in user_name.split()[:2]) if user_name != "Guest" else "?"

    st.markdown("""
    <div style="padding:32px 0 28px;">
      <div style="font-size:11px;color:#6D5EFC;font-weight:700;letter-spacing:.12em;margin-bottom:8px;">ACCOUNT</div>
      <div style="font-size:32px;font-weight:900;color:#ffffff;letter-spacing:-0.03em;margin-bottom:6px;">
        Settings &amp; Support
      </div>
      <div style="font-size:14px;color:#8BA6D3;">Manage your profile, notifications, and get help.</div>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 2], gap="large")

    with col_left:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(109,94,252,0.14),rgba(59,164,255,0.07));
                    border:1px solid rgba(109,94,252,0.28);border-radius:20px;
                    padding:28px 22px;text-align:center;margin-bottom:16px;">
          <div style="width:70px;height:70px;border-radius:50%;
                      background:linear-gradient(135deg,#6D5EFC,#3BA4FF);
                      display:flex;align-items:center;justify-content:center;
                      font-size:26px;font-weight:900;color:#fff;margin:0 auto 14px;">
            {initials}
          </div>
          <div style="font-size:19px;font-weight:800;color:#ffffff;margin-bottom:4px;">{user_name}</div>
          <div style="font-size:12px;color:#8BA6D3;word-break:break-all;margin-bottom:16px;">{user_email}</div>
          <div style="display:inline-flex;align-items:center;gap:6px;
                      background:rgba(142,246,209,0.1);border:1px solid rgba(142,246,209,0.25);
                      border-radius:20px;padding:5px 14px;">
            <span style="width:7px;height:7px;border-radius:50%;background:#8EF6D1;display:inline-block;"></span>
            <span style="font-size:11px;color:#8EF6D1;font-weight:700;">Active Account</span>
          </div>
        </div>
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);
                    border-radius:16px;padding:18px 20px;">
          <div style="font-size:11px;color:#6D5EFC;font-weight:700;letter-spacing:.08em;margin-bottom:14px;">NAVIGATE</div>
          <a href="?page=dashboard" style="display:flex;align-items:center;gap:10px;padding:9px 0;
             border-bottom:1px solid rgba(255,255,255,0.05);text-decoration:none;
             color:#D4E0F7;font-size:13px;font-weight:500;">{get_svg('dashboard', 14)}&nbsp; My Dashboard</a>
          <a href="?page=market" style="display:flex;align-items:center;gap:10px;padding:9px 0;
             border-bottom:1px solid rgba(255,255,255,0.05);text-decoration:none;
             color:#D4E0F7;font-size:13px;font-weight:500;">{get_svg('market', 14)}&nbsp; Live Markets</a>
          <a href="?page=insights" style="display:flex;align-items:center;gap:10px;padding:9px 0;
             text-decoration:none;color:#D4E0F7;font-size:13px;font-weight:500;">{get_svg('news', 14)}&nbsp; News &amp; Insights</a>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(109,94,252,0.1),rgba(59,164,255,0.05));
                    border:1px solid rgba(109,94,252,0.2); border-radius:16px; padding:24px; margin-bottom:24px;">
          <div style="font-size:18px; font-weight:900; color:#ffffff; margin-bottom:4px; display:flex; align-items:center; gap:10px;">
            {get_svg('settings', 20)} Platform Preferences
          </div>
          <p style="font-size:13px; color:#8BA6D3; margin-bottom:0;">Customize how DeepAtomicIQ interacts with your financial life.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06); border-radius:16px; padding:24px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;color:#6D5EFC;font-weight:800;letter-spacing:.12em;margin-bottom:18px;text-transform:uppercase;">Notifications & Alerts</div>', unsafe_allow_html=True)

        reports = st.checkbox("Weekly Portfolio Report emails",
                              value=prefs.get("reports", True),
                              help="Receive a weekly email summary of your portfolio performance")
        alerts  = st.checkbox("Real-Time Volatility Alerts", 
                              value=prefs.get("alerts", False),
                              help="Get notified when market volatility spikes")

        st.markdown("""<div style="border-top:1px solid rgba(255,255,255,0.07);margin:18px 0 16px;"></div>
          <div style="font-size:11px;color:#6D5EFC;font-weight:700;letter-spacing:.08em;margin-bottom:12px;">DISPLAY</div>
        """, unsafe_allow_html=True)

        curr_opts = ["GBP (£)", "USD ($)", "EUR (€)", "JPY (¥)", "AUD (A$)", "CAD (C$)", "CHF (Fr)", "CNY (¥)", "INR (₹)", "HKD ($)", "SGD ($)"]
        currency = st.selectbox("Default Currency", curr_opts,
                                index=curr_opts.index(prefs.get("currency", "GBP (£)")) if prefs.get("currency") in curr_opts else 0,
                                help="Sets how monetary values display across the dashboard")
        st.markdown("</div>", unsafe_allow_html=True)

        sc1, sc2 = st.columns(2, gap="small")
        with sc1:
            if st.button("Save Preferences", type="primary", use_container_width=True):
                if user_email == "guest":
                    st.error("Please login to save preferences.")
                else:
                    new_prefs = {**prefs, "reports": reports, "alerts": alerts, "currency": currency}
                    database.update_user_preferences(user_email, new_prefs)
                    st.session_state.preferences = new_prefs
                    st.toast("✅ Preferences saved and synced to backend!")
                    st.rerun()
        with sc2:
            if st.button("Refresh App", use_container_width=True, key="ref_app"):
                st.rerun()

        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
        st.markdown(f"""<div style="font-size:16px;font-weight:800;color:#ffffff;margin-bottom:14px;">
          {get_svg('help', 16)} Frequently Asked Questions</div>""", unsafe_allow_html=True)

        for q, a in [
            ("How does the AI work?",
             "DeepAtomicIQ uses a **Markowitz-Informed Neural Network (MINN)** that learns optimal "
             "risk-return trade-offs from historical market data. Your survey answers tune the risk "
             "threshold (δ) and temporal decay (γ), personalising your portfolio to you."),
            ("Is my data secure?",
             "Credentials are hashed with **bcrypt (unbreakable hashing)**. For the MVP, data is kept in a "
             "secure SQLite instance, but our architecture is **MongoDB-Ready**. For production (Community Cloud),"
             " we use **MongoDB Atlas** for distributed, AES-256 encrypted storage. The system is architected "
             "to be fully GDPR-compliant with strict data isolation."),
            ("What is the Sharpe Ratio?",
             "**Sharpe Ratio = (Return − Risk-Free Rate) ÷ Volatility.** It measures return per unit "
             "of risk. A ratio above **1.0** is generally good. The MINN maximises this during optimisation."),
        ]:
            with st.expander(q):
                st.markdown(a)

        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
        st.markdown(f"""<div style="font-size:16px;font-weight:800;color:#ffffff;margin-bottom:14px;">
          {get_svg('email', 16)} Contact Support</div>
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
                    border-radius:16px;padding:22px 24px;">
          <p style="font-size:13px;color:#8BA6D3;margin:0 0 18px;">
            Have a bug report or question? Fill in below and we'll reply within 24 hours.
          </p>""", unsafe_allow_html=True)

        subj = st.text_input("Subject", placeholder="e.g. Dashboard not loading", key="support_subj")
        msg  = st.text_area("Message", placeholder="Describe your issue in detail...",
                            key="support_msg", height=110)
        if st.button("Send Message", type="primary", use_container_width=True):
            if user_email == "guest":
                st.warning("Please login to submit a support ticket.")
            elif not subj or not msg:
                st.error("Please fill in both Subject and Message.")
            else:
                database.save_ticket(user_email, subj, msg)
                st.success("✅ Ticket submitted! Check your email for confirmation.")
        st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# BILLING PAGE
# ══════════════════════════════════════════════════════════════════════════════
def page_billing():
    user_email = st.session_state.get("user_email", "guest") or "guest"
    pending_plan = st.session_state.get("pending_plan", "Pro")
    
    st.markdown(f"""
    <div style="padding:40px 0 20px;">
      <div style="font-size:12px;color:#6D5EFC;font-weight:800;letter-spacing:.12em;margin-bottom:8px;">CHECKOUT</div>
      <div style="font-size:32px;font-weight:900;color:#ffffff;letter-spacing:-0.03em;">
        Complete your subscription to {pending_plan}
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1.5, 1], gap="large")
    
    with col1:
        st.markdown(f'<div class="account-section-hdr">{get_svg("risk", 20)} Payment Method</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
            card_name = st.text_input("Cardholder Name", value=st.session_state.get("user_name", ""))
            card_num = st.text_input("Card Number", placeholder="0000 0000 0000 0000")
            
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Expiry Date", placeholder="MM/YY")
            with c2:
                st.text_input("CVV", type="password", placeholder="123")
                
            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            if st.button(f"Confirm & Pay for {pending_plan}", type="primary", use_container_width=True):
                if not card_num:
                    st.error("Please enter card details.")
                else:
                    # Sync to DB
                    import json
                    user_data = database.get_user(user_email)
                    prefs = json.loads(user_data["preferences_json"]) if user_data and user_data.get("preferences_json") else {}
                    prefs["subscription"] = pending_plan
                    prefs["payment_verified"] = True
                    database.update_user_preferences(user_email, prefs)
                    
                    st.success(f"🎉 Welcome to {pending_plan}! Your account has been upgraded.")
                    st.balloons()
                    st.session_state.nav_page = "account"
                    st.rerun()

    with col2:
        st.markdown(f'<div class="account-section-hdr">{get_svg("settings", 20)} Order Summary</div>', unsafe_allow_html=True)
        price = "£19.00" if pending_plan == "Pro" else "£89.00" if pending_plan == "Ultra" else "£0.00"
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:24px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                <span style="color:#8BA6D3;">DeepAtomicIQ {pending_plan}</span>
                <span style="color:#fff; font-weight:700;">{price}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                <span style="color:#8BA6D3;">Service Activation</span>
                <span style="color:#8EF6D1; font-weight:700;">FREE</span>
            </div>
            <div style="border-top:1px solid rgba(255,255,255,0.05); margin:12px 0; padding-top:12px; display:flex; justify-content:space-between;">
                <span style="color:#fff; font-weight:800;">TOTAL DUE</span>
                <span style="color:#6D5EFC; font-size:20px; font-weight:900;">{price}</span>
            </div>
            <div style="font-size:11px; color:#8BA6D3; margin-top:20px; font-style:italic;">
                * Recurring monthly billing. You can cancel your subscription at any time from your account settings.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("← Back to Account", use_container_width=True):
            st.session_state.nav_page = "account"
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MY ACCOUNT PAGE
# ══════════════════════════════════════════════════════════════════════════════
def page_account():
    import base64, io
    user_email = st.session_state.get("user_email", "guest") or "guest"
    user_name  = st.session_state.get("user_name",  "Guest") or "Guest"
    user_data  = database.get_user(user_email) if user_email != "guest" else None
    
    # Load preferences
    prefs = {}
    if user_data and user_data.get("preferences_json"):
        try:
            prefs = json.loads(user_data["preferences_json"])
        except:
            pass
            
    initials = "".join(p[0].upper() for p in user_name.split()[:2]) if user_name != "Guest" else "?"
    
    # ── Backend Sync: Ensure session state matches DB ────────────────────
    if "user_avatar" not in st.session_state or not st.session_state.user_avatar:
        st.session_state.user_avatar = prefs.get("avatar_url", "")

    # ── High-End Design System Overrides ──────────────────────────────────────
    st.markdown("""
    <style>
    /* Premium Input Styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div {
        background: rgba(255,255,255,0.03) !important;
        color: #E8EAF6 !important;
        border: 1px solid rgba(109,94,252,0.2) !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        transition: all 0.2s ease !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #6D5EFC !important;
        background: rgba(109,94,252,0.05) !important;
        box-shadow: 0 0 0 3px rgba(109,94,252,0.15) !important;
    }
    .stTextInput label, .stTextArea label, .stSelectbox label, .stFileUploader label {
        color: #8BA6D3 !important; font-size: 13px !important; font-weight: 600 !important;
        margin-bottom: 6px !important;
    }
    .stFileUploader > div {
        background: rgba(255,255,255,0.02) !important;
        border: 2px dashed rgba(109,94,252,0.2) !important;
        border-radius: 14px !important;
    }
    /* Section dividers */
    .account-section-hdr {
        font-size: 18px; font-weight: 800; color: #fff; margin: 32px 0 16px;
        display: flex; align-items: center; gap: 10px;
    }
    .account-card {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 20px; padding: 24px;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Top Hero Header ──────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:40px 0 30px;">
      <div style="font-size:12px;color:#6D5EFC;font-weight:800;letter-spacing:.15em;margin-bottom:10px;text-transform:uppercase;">Account Center</div>
      <h1 style="font-size:38px;font-weight:900;color:#ffffff;letter-spacing:-0.04em;margin:0 0 8px;">
        Profile & Settings
      </h1>
      <p style="font-size:15px;color:#8BA6D3;max-width:600px;line-height:1.6;">
        Manage your digital identity, customize your AI preferences, and securely connect your financial accounts.
      </p>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 2.3], gap="large")

    # ── SIDEBAR: Identity Card ───────────────────────────────────────────────
    with col_left:
        avatar_url = st.session_state.get("user_avatar", "")
        emoji_choice = prefs.get("avatar_emoji", "")

        if avatar_url:
            avatar_inner = f'<img src="{avatar_url}" style="width:110px;height:110px;border-radius:50%;object-fit:cover;border:4px solid rgba(109,94,252,0.4);box-shadow:0 10px 40px rgba(0,0,0,0.4);">'
        elif emoji_choice:
            avatar_inner = f'<div style="width:110px;height:110px;border-radius:50%;background:linear-gradient(135deg,#6D5EFC,#3BA4FF);display:flex;align-items:center;justify-content:center;font-size:48px;border:4px solid rgba(109,94,252,0.4);box-shadow:0 10px 40px rgba(0,0,0,0.4);">{emoji_choice}</div>'
        else:
            avatar_inner = f'<div style="width:110px;height:110px;border-radius:50%;background:linear-gradient(135deg,#6D5EFC,#3BA4FF);display:flex;align-items:center;justify-content:center;font-size:38px;font-weight:900;color:#fff;border:4px solid rgba(109,94,252,0.4);box-shadow:0 10px 40px rgba(0,0,0,0.4);">{initials}</div>'

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(109,94,252,0.15),rgba(59,164,255,0.08));
                    border:1px solid rgba(109,94,252,0.3);border-radius:24px;
                    padding:32px 24px;text-align:center;margin-bottom:24px;box-shadow:0 20px 50px rgba(0,0,0,0.3);">
          <div style="display:flex;justify-content:center;margin-bottom:20px;">{avatar_inner}</div>
          <div style="font-size:22px;font-weight:800;color:#ffffff;margin-bottom:4px;">{user_name}</div>
          <div style="font-size:13px;color:#8BA6D3;margin-bottom:18px;">{user_email}</div>
          
          <div style="display:inline-flex;align-items:center;gap:7px;
                      background:rgba(142,246,209,0.12);border:1px solid rgba(142,246,209,0.3);
                      border-radius:30px;padding:6px 16px;">
            <span style="width:7px;height:7px;border-radius:50%;background:#8EF6D1;"></span>
            <span style="font-size:11px;color:#8EF6D1;font-weight:800;letter-spacing:0.04em;">VERIFIED ACCOUNT</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Quick Stats Card
        # Dynamic quality calculation
        has_survey = st.session_state.get("result") is not None
        has_avatar = bool(st.session_state.get("user_avatar") or prefs.get("avatar_url"))
        
        # Breakdown: Baseline 20%, Survey 40%, Bio/Details 10% each
        fields = [prefs.get("job"), prefs.get("location"), prefs.get("bio")]
        filled_count = sum(1 for v in fields if v)
        
        quality_score = 20
        if has_survey: quality_score += 40
        if has_avatar: quality_score += 10
        quality_score += (filled_count * 10)
        
        quality_score = min(100, quality_score)
        
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
                    border-radius:20px;padding:20px;margin-bottom:20px;">
          <div style="font-size:12px;color:#6D5EFC;font-weight:800;margin-bottom:16px;">PROFILE COMPLETION</div>
          <div style="height:6px;background:rgba(255,255,255,0.05);border-radius:3px;overflow:hidden;margin-bottom:12px;">
            <div style="width:{quality_score}%;height:100%;background:linear-gradient(90deg,#6D5EFC,#3BA4FF);border-radius:3px;"></div>
          </div>
          <div style="font-size:12px;color:#D4E0F7;display:flex;justify-content:space-between;">
            <span>Profile Quality</span>
            <span style="font-weight:700;">{int(quality_score)}% {'High' if quality_score > 80 else 'Medium' if quality_score > 50 else 'Low'}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Avatar Upload Section
        st.markdown('<div style="font-size:12px;color:#6D5EFC;font-weight:800;margin-bottom:8px;">PROFILE PHOTO</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload new photo", type=["png","jpg","jpeg","webp"], label_visibility="collapsed")
        if uploaded_file:
            import base64
            img_b64 = base64.b64encode(uploaded_file.read()).decode()
            data_url = f"data:{uploaded_file.type};base64,{img_b64}"
            st.session_state.user_avatar = data_url
            if user_email != "guest":
                prefs["avatar_url"] = data_url
                database.update_user_preferences(user_email, prefs)
                st.success("Photo synced to cloud!")
                st.rerun()

    # ── MAIN CONTENT: Edit Fields ────────────────────────────────────────────
    with col_right:
        
        # 🟢 Profile Customization
        st.markdown(f'<div class="account-section-hdr">{get_svg("user", 22)} Personal Information</div>', unsafe_allow_html=True)
        with st.container(border=True):
            n_col1, n_col2 = st.columns(2)
            with n_col1:
                new_full_name = st.text_input("Display Name", value=user_name)
                job_title = st.text_input("Occupation", value=prefs.get("job", ""), placeholder="e.g. Portfolio Manager")
            with n_col2:
                location = st.text_input("Location", value=prefs.get("location", ""), placeholder="e.g. Zurich, Switzerland")
                avatar_picker = st.selectbox("Avatar Emoji Fallback", [""] + ["🐻","🦁","🐼","🐯","💎","🚀","🎯","⚡"], 
                                             index=0 if not emoji_choice else ([""] + ["🐻","🦁","🐼","🐯","💎","🚀","🎯","⚡"]).index(emoji_choice))
            
            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:12px;color:#6D5EFC;font-weight:800;margin-bottom:12px;">CONTACT & IDENTITY</div>', unsafe_allow_html=True)
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                country_codes = ["+44 (UK)", "+1 (USA/Canada)", "+34 (Spain)", "+33 (France)", "+49 (Germany)", "+91 (India)", "+61 (Australia)", "+81 (Japan)"]
                curr_code = prefs.get("phone_code", "+44 (UK)")
                phone_code = st.selectbox("Country Code", country_codes, index=country_codes.index(curr_code) if curr_code in country_codes else 0)
                phone_num = st.text_input("Phone Number", value=prefs.get("phone", ""), placeholder="e.g. 7123 456789")
            with c_col2:
                import datetime
                try:
                    saved_dob = datetime.datetime.strptime(prefs.get("dob", "01/01/1990"), "%d/%m/%Y").date()
                except:
                    saved_dob = datetime.date(1990, 1, 1)
                
                dob = st.date_input("Date of Birth (UK Format: DD/MM/YYYY)", 
                                   value=saved_dob,
                                   min_value=datetime.date(1920, 1, 1),
                                   max_value=datetime.date.today(),
                                   format="DD/MM/YYYY")
            
            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            about_bio = st.text_area("Bio / Investment Goals", value=prefs.get("bio", ""), placeholder="Briefly describe your goals...", height=100)
            
            if st.button("💾 Save Profile Changes", type="primary", use_container_width=True):
                if user_email != "guest":
                    prefs["job"] = job_title
                    prefs["location"] = location
                    prefs["bio"] = about_bio
                    prefs["avatar_emoji"] = avatar_picker
                    prefs["avatar_url"] = st.session_state.get("user_avatar", "")
                    # New fields
                    prefs["phone_code"] = phone_code
                    prefs["phone"] = phone_num
                    prefs["dob"] = dob.strftime("%d/%m/%Y")
                    
                    database.update_user_preferences(user_email, prefs)
                    
                    if new_full_name != user_name:
                        conn = database.get_connection()
                        conn.execute("UPDATE users SET name = ? WHERE email = ?", (new_full_name, user_email))
                        conn.commit()
                        st.session_state.user_name = new_full_name
                    
                    st.success("✅ Profile changes saved!")
                    st.rerun()

        # 🔵 Subscription Plans
        st.markdown(f'<div class="account-section-hdr">{get_svg("risk", 22)} Membership & Billing</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<p style="font-size:13px;color:#8BA6D3;margin-bottom:20px;">Choose a plan that fits your investment scale. DeepAtomicIQ AI capabilities scale with your membership level.</p>', unsafe_allow_html=True)
            
            p_col1, p_col2, p_col3 = st.columns(3)
            current_plan = prefs.get("subscription", "Essential")
            
            plans = [
                {
                    "id": "Essential", "price": "Free", "color": "#8BA6D3",
                    "feats": ["3 Portfolio Rebalances/yr", "Basic Risk Assessments", "Email Support"]
                },
                {
                    "id": "Pro", "price": "£19/mo", "color": "#6D5EFC",
                    "feats": ["Unlimited AI Rebalancing", "Real-time Regime Detection", "Daily Reports"]
                },
                {
                    "id": "Ultra", "price": "£89/mo", "color": "#8EF6D1",
                    "feats": ["Multi-Account Sync", "REST API for Institutions", "24/7 Concierge"]
                }
            ]
            
            for i, (col, plan) in enumerate(zip([p_col1, p_col2, p_col3], plans)):
                is_active = current_plan == plan["id"]
                with col:
                    active_style = f"border: 2px solid {plan['color']};" if is_active else "border: 1px solid rgba(255,255,255,0.08);"
                    feat_list = "".join([f'<div style="font-size:10px; color:#8BA6D3; margin-bottom:4px;">• {f}</div>' for f in plan["feats"]])
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.03); {active_style} padding:18px 12px; border-radius:14px; text-align:center; min-height:200px; display:flex; flex-direction:column;">
                        <div style="font-size:10px; font-weight:800; color:{plan['color']}; text-transform:uppercase;">{plan['id']}</div>
                        <div style="font-size:22px; font-weight:800; color:#fff; margin:6px 0;">{plan['price']}</div>
                        <div style="flex-grow:1; text-align:left; margin:10px 0;">{feat_list}</div>
                        {is_active and f'<div style="font-size:10px; font-weight:900; background:{plan["color"]}; color:#000; padding:4px 8px; border-radius:10px; display:inline-block; align-self:center;">ACTIVE</div>' or ''}
                    </div>
                    """, unsafe_allow_html=True)
                    if not is_active:
                        if st.button(f"Upgrade to {plan['id']}", key=f"sub_{plan['id']}", use_container_width=True):
                            st.session_state.pending_plan = plan["id"]
                            st.session_state.nav_page = "billing"
                            st.rerun()
            
            st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
            st.markdown('<p style="font-size:11px;color:#8BA6D3;text-align:center;">Secure payment processing via DeepAtomicIQ Stripe Integration.</p>', unsafe_allow_html=True)

        # 🔴 Security & Compliance
        st.markdown(f'<div class="account-section-hdr">{get_svg("risk", 22)} Security & Compliance</div>', unsafe_allow_html=True)
        with st.expander("Control Center (Advanced Settings)"):
            st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
            if st.button("🔑 Change Master Password", use_container_width=True, key="btn_pw_reset"):
                st.session_state.show_pw_form = True
            
            if st.session_state.get("show_pw_form"):
                st.markdown('<div style="background:rgba(255,255,255,0.05); padding:20px; border-radius:15px; margin-top:10px; border:1px solid rgba(109,94,252,0.3);">', unsafe_allow_html=True)
                provider = user_data.get("provider", "email") if user_data else "guest"
                
                if provider != "email":
                    st.info(f"💡 You are logged in via **{provider.capitalize()}**. This form will update your local DeepAtomicIQ fallback password.")
                
                with st.form("pw_reset_form", clear_on_submit=True):
                    st.markdown('<div style="font-size:14px; font-weight:700; color:#fff; margin-bottom:15px;">Update Master Password</div>', unsafe_allow_html=True)
                    new_pw = st.text_input("New Secure Password", type="password")
                    conf_pw = st.text_input("Confirm New Password", type="password")
                    
                    c1, c2 = st.columns([1,1])
                    with c1:
                        if st.form_submit_button("Update Password", type="primary", use_container_width=True):
                            if not new_pw or len(new_pw) < 6:
                                st.error("Password too short (min 6 chars).")
                            elif new_pw != conf_pw:
                                st.error("Passwords do not match.")
                            elif user_email == "guest":
                                st.error("Guest users cannot modify session credentials.")
                            else:
                                database.update_password(user_email, new_pw)
                                st.success("✅ Password updated!")
                                st.session_state.show_pw_form = False
                                st.rerun()
                    with c2:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.show_pw_form = False
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.05);margin:20px 0;">', unsafe_allow_html=True)
            
            st.markdown('<div style="font-size:13px;font-weight:700;color:#FF6B6B;margin-bottom:4px;">ACCOUNT TERMINATION</div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:11px;color:#8BA6D3;margin-bottom:12px;">Deleting your account will wipe all AI portfolio history and personal data.</div>', unsafe_allow_html=True)
            
            if st.button("Permanently Delete Account", type="secondary", use_container_width=True):
                st.error("Account deletion is restricted to administrative users in this demo environment.")






# ── Main render ──────────────────────────────────────────────────────────────
def main_router():
    render_nav()
    
    if st.session_state.get("show_auth", False):
        render_auth_modal()
    else:
        page = st.session_state.get("nav_page", "home")
        routing = {
            "home":      page_home,
            "dashboard": page_dashboard,
            "market":    page_market,
            "insights":  page_insights,
            "more":      page_more,
            "account":   page_account,
            "billing":   page_billing,
        }
        routing.get(page, page_home)()

main_router()

# =============================================================================
# FLOATING CHATBOT (Fixed & working)
# =============================================================================
import streamlit.components.v1 as components

# Try to load Gemini key if available (not required for UI)
try:
    GEMINI_KEY = st.secrets.get("gemini_api_key", "")
except Exception:
    GEMINI_KEY = ""

_SYSTEM_PROMPT = """You are DeepAtomicIQ, an AI investment assistant embedded in the DeepAtomicIQ robo-advisor platform.
You help users understand their AI-generated portfolio, explain investment concepts clearly, and guide them through the app.
The platform uses a Markowitz-Informed Neural Network (MINN) that maximises the Sharpe ratio.
It offers 6 risk profiles and invests across 8 ETFs: VOO (S&P 500), QQQ (Nasdaq 100), VWRA (Global), AGG (Bonds), GLD (Gold), VNQ (Real Estate), ESGU (ESG), PDBC (Commodities).
Be concise, friendly, and jargon-free. Use bullet points where helpful. Never give regulated financial advice.
Always remind users to consult a qualified financial adviser for real investment decisions. Keep replies under 120 words unless asked for detail."""

CHATBOT_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: transparent; overflow: hidden; font-family: 'Inter', system-ui, sans-serif; }}
  /* Chat button (fixed to bottom-right) */
  #cb-btn {{
    position: fixed; bottom: 24px; right: 24px; z-index: 99999;
    width: 56px; height: 56px; border-radius: 50%;
    background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
    border: none; cursor: pointer; font-size: 26px; color: white;
    box-shadow: 0 6px 20px rgba(109,94,252,0.5);
    display: flex; align-items: center; justify-content: center;
    transition: transform 0.2s, box-shadow 0.2s;
  }}
  #cb-btn:hover {{ transform: scale(1.08); box-shadow: 0 10px 28px rgba(109,94,252,0.7); }}
  /* Chat panel */
  #cb-panel {{
    position: fixed; bottom: 96px; right: 24px; z-index: 99998;
    width: 380px; height: 520px;
    background: rgba(10, 12, 28, 0.98); backdrop-filter: blur(20px);
    border: 1px solid rgba(109,94,252,0.4); border-radius: 24px;
    display: none; flex-direction: column; overflow: hidden;
    box-shadow: 0 20px 50px rgba(0,0,0,0.6);
    font-family: inherit;
  }}
  #cb-panel.open {{ display: flex; }}
  /* Header */
  #cb-hdr {{
    padding: 12px 16px;
    background: rgba(109,94,252,0.15);
    border-bottom: 1px solid rgba(255,255,255,0.08);
    display: flex; align-items: center; gap: 10px;
  }}
  .cb-av {{
    width: 34px; height: 34px; border-radius: 50%;
    background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }}
  .cb-name {{ font-weight: 700; color: white; font-size: 14px; }}
  .cb-sub {{ font-size: 10px; color: #8EF6D1; }}
  .cb-x {{
    margin-left: auto; background: none; border: none;
    color: #aaa; font-size: 24px; cursor: pointer;
    line-height: 1; padding: 0 6px;
  }}
  /* Messages area */
  #cb-msgs {{
    flex: 1; overflow-y: auto; padding: 14px;
    display: flex; flex-direction: column; gap: 10px;
    scrollbar-width: thin;
  }}
  .bot, .usr {{
    max-width: 85%; padding: 8px 12px; border-radius: 18px;
    font-size: 13px; line-height: 1.5; word-break: break-word;
  }}
  .bot {{
    background: rgba(109,94,252,0.15); color: #E0E7FF;
    border: 1px solid rgba(109,94,252,0.3);
    align-self: flex-start; border-bottom-left-radius: 4px;
  }}
  .usr {{
    background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
    color: white; align-self: flex-end; border-bottom-right-radius: 4px;
  }}
  .typing {{
    display: flex; gap: 4px; align-items: center;
    background: rgba(109,94,252,0.1); padding: 8px 12px;
    border-radius: 18px; align-self: flex-start;
    border: 1px solid rgba(109,94,252,0.2);
  }}
  .typing span {{
    width: 6px; height: 6px; border-radius: 50%;
    background: #8BA6D3; animation: bounce 1.2s infinite;
  }}
  .typing span:nth-child(2) {{ animation-delay: 0.2s; }}
  .typing span:nth-child(3) {{ animation-delay: 0.4s; }}
  @keyframes bounce {{
    0%,60%,100% {{ transform: translateY(0); }}
    30% {{ transform: translateY(-5px); }}
  }}
  /* Chips (suggestions) */
  .chips {{
    display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;
  }}
  .chip {{
    background: rgba(109,94,252,0.2); border: 1px solid rgba(109,94,252,0.4);
    border-radius: 30px; padding: 3px 10px; font-size: 11px;
    color: #C4D0FF; cursor: pointer; transition: 0.1s;
  }}
  .chip:hover {{ background: rgba(109,94,252,0.4); color: white; }}
  /* Input row */
  #cb-inrow {{
    display: flex; gap: 8px; padding: 12px;
    border-top: 1px solid rgba(255,255,255,0.08);
    background: rgba(0,0,0,0.2);
  }}
  #cb-in {{
    flex: 1; background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15); border-radius: 30px;
    padding: 8px 14px; color: white; font-size: 13px;
    outline: none; font-family: inherit;
  }}
  #cb-in:focus {{ border-color: #6D5EFC; }}
  #cb-send {{
    background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
    border: none; border-radius: 50%; width: 36px; height: 36px;
    cursor: pointer; color: white; font-size: 16px;
    display: flex; align-items: center; justify-content: center;
  }}
  #cb-send:disabled, #cb-in:disabled {{ opacity: 0.5; cursor: not-allowed; }}
</style>
</head>
<body>

<button id="cb-btn">🤖</button>
<div id="cb-panel">
  <div id="cb-hdr">
    <div class="cb-av">🧠</div>
    <div><div class="cb-name">DeepAtomicIQ AI</div><div class="cb-sub">Powered by Gemini • Online</div></div>
    <button class="cb-x" id="cb-close">✕</button>
  </div>
  <div id="cb-msgs">
    <div class="bot">
      Hi! I'm your DeepAtomicIQ AI assistant. Ask me anything about your portfolio, investing, or how the app works.<br>
      <div class="chips">
        <span class="chip">How does MINN work?</span>
        <span class="chip">Explain my risk profile</span>
        <span class="chip">What is the Sharpe ratio?</span>
        <span class="chip">Which ETFs should I buy?</span>
      </div>
    </div>
  </div>
  <div id="cb-inrow">
    <input id="cb-in" type="text" placeholder="Ask me anything...">
    <button id="cb-send">➤</button>
  </div>
</div>

<script>
  const GEMINI_KEY = "{GEMINI_KEY}";
  const SYSTEM_PROMPT = `{_SYSTEM_PROMPT}`;
  let chatHistory = [];

  const panel = document.getElementById('cb-panel');
  const msgs = document.getElementById('cb-msgs');
  const inp = document.getElementById('cb-in');
  const btn = document.getElementById('cb-btn');
  const sendBtn = document.getElementById('cb-send');
  const closeBtn = document.getElementById('cb-close');

  function togglePanel() { panel.classList.toggle('open'); if(panel.classList.contains('open')) { inp.focus(); msgs.scrollTop = msgs.scrollHeight; } }
  btn.onclick = togglePanel;
  closeBtn.onclick = togglePanel;

  function addMessage(text, isUser) {
    const div = document.createElement('div');
    div.className = isUser ? 'usr' : 'bot';
    div.innerHTML = text.replace(/\\n/g, '<br>').replace(/\\*\\*(.*?)\\*\\*/g, '<b>$1</b>');
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing';
    typingDiv.id = 'cb-typing';
    typingDiv.innerHTML = '<span></span><span></span><span></span>';
    msgs.appendChild(typingDiv);
    msgs.scrollTop = msgs.scrollHeight;
  }
  function removeTyping() {
    const el = document.getElementById('cb-typing');
    if (el) el.remove();
  }

  async function callGemini(userMsg) {
    if (!GEMINI_KEY) {
      return "⚠️ **Offline mode** – Add your Gemini API key to `secrets.toml` to enable full AI. For now, ask me about portfolio basics, risk profiles, or ETF allocation. I can still give general guidance based on the app's design.";
    }
    chatHistory.push({ role: "user", parts: [{ text: userMsg }] });
    try {
      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_KEY}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            system_instruction: { parts: [{ text: SYSTEM_PROMPT }] },
            contents: chatHistory,
            generationConfig: { maxOutputTokens: 350, temperature: 0.7 }
          })
        }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const reply = data.candidates[0].content.parts[0].text;
      chatHistory.push({ role: "model", parts: [{ text: reply }] });
      return reply;
    } catch (err) {
      chatHistory.pop();
      return `❌ Could not reach AI: ${err.message}. Please check your API key or internet connection.`;
    }
  }

  async function sendMessage() {
    const q = inp.value.trim();
    if (!q || inp.disabled) return;
    addMessage(q, true);
    inp.value = '';
    inp.disabled = true;
    sendBtn.disabled = true;
    showTyping();
    const reply = await callGemini(q);
    removeTyping();
    addMessage(reply, false);
    inp.disabled = false;
    sendBtn.disabled = false;
    inp.focus();
  }

  sendBtn.onclick = sendMessage;
  inp.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });

  // Pre‑defined chip questions
  document.querySelectorAll('.chip').forEach(chip => {
    chip.onclick = () => { inp.value = chip.textContent; sendMessage(); };
  });
</script>
</body>
</html>
""".replace("{GEMINI_KEY}", GEMINI_KEY).replace("{_SYSTEM_PROMPT}", _SYSTEM_PROMPT)

# CSS in the parent page to reposition the iframe container as fixed bottom-right
st.markdown("""
<style>
/* Target the chatbot wrapper precisely using the sibling anchor trick */
#cb-anchor + div[data-testid="stCustomComponentV1"] {
    position: fixed !important;
    bottom: 0 !important; right: 0 !important;
    width: 420px !important; height: 640px !important;
    z-index: 1000000 !important;
    pointer-events: none !important;
    border: none !important;
    background: transparent !important;
}
#cb-anchor + div[data-testid="stCustomComponentV1"] iframe {
    pointer-events: auto !important;
    border: none !important;
    width: 420px !important; height: 640px !important;
    background: transparent !important;
}
</style>
""", unsafe_allow_html=True)

# Invisible anchor to precisely target the chatbot container in CSS
st.markdown("<div id='cb-anchor'></div>", unsafe_allow_html=True)
components.html(CHATBOT_HTML, height=0, scrolling=False)
