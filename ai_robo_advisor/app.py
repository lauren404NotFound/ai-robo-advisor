"""
app.py  —  AI & ML Robo-Advisor  (Streamlit) — Entry Point
===========================================================
This file is the application entry point only.
All UI logic lives in the ui/ package:

    ui/styles.py         — Theme constants, get_svg(), global CSS
    ui/auth.py           — Session helpers, email, OAuth, auth modal
    ui/ai_engine.py      — Survey questions, Claude & local AI explanations
    ui/charts.py         — Plotly chart factory functions
    ui/nav.py            — Fixed top navigation bar
    ui/page_home.py      — Landing / home page
    ui/page_dashboard.py — Survey wizard + portfolio dashboard
    ui/page_insights.py  — Why DeepAtomicIQ insights page
    ui/page_market.py    — Live market data page
    ui/page_more.py      — Preferences / settings page
    ui/page_account.py   — Account profile + billing pages
    ui/chatbot.py        — Floating Gemini-powered chatbot widget

Run:
    cd "Demo_prototype copy"
    python3 -m streamlit run ai_robo_advisor/app.py --server.port 8507

Architecture:
    In production this file would start a FastAPI service (backend_api.py)
    and serve the Streamlit UI as a thin frontend layer. For now both layers
    run in the same process, with the FastAPI file showing the intended API
    surface for a decoupled deployment.
"""

from __future__ import annotations
import os
import sys
import streamlit as st
import anthropic
from streamlit_oauth import OAuth2Component

# ── Package path setup ───────────────────────────────────────────────────────
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)

# Add ui/ to path so ui sub-modules can import each other without the prefix
_UI_DIR = os.path.join(_PKG_DIR, "ui")
if _UI_DIR not in sys.path:
    sys.path.insert(0, _UI_DIR)

# ── PAGE CONFIG (must be the very first Streamlit call) ───────────────────────
st.set_page_config(
    page_title="AI Robo-Advisor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Anthropic API setup ───────────────────────────────────────────────────────
_api_key = st.secrets.get("anthropic_api_key")
if not _api_key:
    _api_key = st.secrets.get("ANTHROPIC_API_KEY")
if not _api_key:
    try:
        _api_key = st.secrets.anthropic.get("api_key")
    except Exception:
        pass

claude_status = "Disconnected"
anthropic_client = None

if _api_key:
    try:
        anthropic_client = anthropic.Anthropic(api_key=_api_key)
        claude_status = "Connected"
    except Exception as e:
        claude_status = f"Init Error: {e}"
else:
    claude_status = "Key Missing in Secrets"

# ── OAuth components ──────────────────────────────────────────────────────────
try:
    LINKEDIN_CLIENT_ID     = st.secrets["linkedin"]["client_id"]
    LINKEDIN_CLIENT_SECRET = st.secrets["linkedin"]["client_secret"]
    REDIRECT_URI = "https://ai-robo-advisor-gpxvxjfgyp4cml7xjswbsh.streamlit.app"
except Exception:
    LINKEDIN_CLIENT_ID = LINKEDIN_CLIENT_SECRET = ""
    REDIRECT_URI = "http://localhost:8501"

try:
    GOOGLE_CLIENT_ID     = st.secrets["auth"]["client_id"]
    GOOGLE_CLIENT_SECRET = st.secrets["auth"]["client_secret"]
except Exception:
    GOOGLE_CLIENT_ID = GOOGLE_CLIENT_SECRET = ""

google_oauth = OAuth2Component(
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    "https://accounts.google.com/o/oauth2/v2/auth",
    "https://oauth2.googleapis.com/token",
    "https://www.googleapis.com/oauth2/v3/userinfo",
    "https://www.googleapis.com/oauth2/v3/userinfo",
)

linkedin_oauth = OAuth2Component(
    LINKEDIN_CLIENT_ID,
    LINKEDIN_CLIENT_SECRET,
    "https://www.linkedin.com/oauth/v2/authorization",
    "https://www.linkedin.com/oauth/v2/accessToken",
    "https://api.linkedin.com/v2/userinfo",
)

# ── ML model path (shared with portfolio pages) ───────────────────────────────
MODEL_PATH = os.path.join(_PKG_DIR, "model.pkl")

# ── Internal engine imports ───────────────────────────────────────────────────
try:
    from portfolio_engine import build_portfolio, TICKER_MAP, ASSETS
except (KeyError, ImportError):
    import portfolio_engine
    build_portfolio = portfolio_engine.build_portfolio
    TICKER_MAP      = portfolio_engine.TICKER_MAP
    ASSETS          = portfolio_engine.ASSETS

from explainer import DeepIQInterpreter, explain as local_explain
import database

# ── UI package imports ────────────────────────────────────────────────────────
from ui.auth import _init, restore_session_from_storage
from ui.nav import render_nav
from ui.auth import render_auth_modal
from ui.page_home import page_home
from ui.page_dashboard import page_dashboard
from ui.page_insights import page_insights
from ui.page_market import page_market
from ui.page_more import page_more
from ui.page_account import page_account, page_billing
from ui.chatbot import render_chatbot

# ── Sidebar status ────────────────────────────────────────────────────────────
st.sidebar.markdown("### Systems Status")
if claude_status == "Connected":
    st.sidebar.success(f"● Claude: {claude_status}")
elif "Key Missing" in claude_status:
    st.sidebar.warning(f"● Claude: {claude_status}")
    if st.sidebar.button("🔍 Debug Secrets"):
        st.sidebar.write("App Path:", __file__)
        st.sidebar.write("Available Keys:", list(st.secrets.keys()))

# ── Session init + splash + session restore ───────────────────────────────────
_init()

# Splash screen (first load only)
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
    .splash-bar { margin-top: 40px; width: 120px; height: 3px;
        background: rgba(255,255,255,0.06); border-radius: 99px; overflow: hidden; }
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

restore_session_from_storage()

if "explanation_mode" not in st.session_state:
    st.session_state.explanation_mode = "simple"

# ── Main router ───────────────────────────────────────────────────────────────
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
render_chatbot()
