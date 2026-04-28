"""
ui/auth.py
==========
Authentication helpers:
  - Session management (_do_login, _do_logout, _auth_check)
  - SMTP email verification (send_verification_email, send_portfolio_report)
  - Session restore from localStorage (restore_session_from_storage)
  - OAuth bridge (_handle_auth_bridge)
  - Auth modal UI (render_auth_modal)

All Streamlit session_state access goes through st.session_state directly —
no global variables needed because st is a module-level singleton.
"""
from __future__ import annotations
import os, datetime, json, random, re, smtplib, hmac, hashlib, secrets as _secrets
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st

# Shared constants imported from styles
from ui.styles import (
    ACCENT, ACCENT2, ACCENT3, PANEL, BORDER, TEXT, MUTED,
    GLOBAL_CURRENCIES, GLOBAL_COUNTRIES, get_svg,
    POS, NEG,
)
import database

# OAuth components are created in app.py and passed in where needed,
# or re-imported here via the module-level google_oauth / linkedin_oauth
# objects that app.py creates before importing this module.
# We use a lazy-import pattern to avoid circular imports.

def _get_oauth():
    import app as _app
    return _app.google_oauth, _app.linkedin_oauth, _app.REDIRECT_URI

def _auth_check() -> bool:
    return st.session_state.get("authenticated", False)

def _user_email() -> str:
    return st.session_state.get("user_email", "")

def _user_name() -> str:
    return st.session_state.get("user_name", "")

# ── Server-side session manager ──────────────────────────────────────────────
# Sessions are stored in MongoDB; only an opaque session_id lives in the
# browser cookie.  No sensitive user data is ever stored client-side.
from session_manager import SessionManager as _SM
_sm = _SM()


def _do_login(email: str, name: str, provider: str = "email",
              avatar: str = None, remember: bool = True):
    """
    Authenticate the user:
      1. Create a server-side session in MongoDB.
      2. Write the opaque session_id to a SameSite=Strict cookie.
      3. Populate st.session_state for the current render cycle.
    """
    # Invalidate any previous session for this email before creating a new one
    # (prevents session accumulation; single-session enforcement)
    _sm.invalidate_all_for_email(email)

    sid = _sm.create_session(email, name, provider, avatar)
    _sm.set_cookie(sid)

    st.session_state.session_id    = sid
    st.session_state.authenticated = True
    st.session_state.user_email    = email
    st.session_state.user_name     = name
    st.session_state.user_provider = provider
    st.session_state.user_avatar   = avatar
    st.session_state.show_auth     = False

    if remember:
        st.session_state.save_login_email = email
        st.session_state.save_login_name  = name

    # Rest of existing code (saved assessment, preferences...)
    saved = database.get_latest_assessment(email)
    if saved:
        st.session_state.result = saved["result"]
        st.session_state.survey_answers = saved["answers"]
        st.session_state.survey_page = "portfolio"
    else:
        # Tie rogue guest survey session to the newly logged in user!
        if st.session_state.get("result") and st.session_state.get("survey_answers"):
            database.save_assessment(email, st.session_state.survey_answers, st.session_state.result)
            st.session_state.survey_page = "portfolio"

    st.session_state.preferences = {}
    user_data = database.get_user(email)
    if user_data and user_data.get("preferences_json"):
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

# ────────────────────────────────────────────────────────────────────────────────
# SMTP REAL EMAIL VERIFICATION ENGINE
# ────────────────────────────────────────────────────────────────────────────────
def send_verification_email(to_email: str, code: str) -> bool:
    
    smtp_creds = st.secrets.get("smtp", {})
    sender_email = smtp_creds.get("email", "")
    sender_pw = smtp_creds.get("password", "")
    
    if not sender_email or not sender_pw:
        return False
        
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your LEM StratIQ Verification Code"
    msg["From"] = f"LEM StratIQ <{sender_email}>"
    msg["To"] = to_email
    
    html = f"""
    <html>
      <body style="font-family: sans-serif; background-color: #0A0A1C; color: #ffffff; padding: 40px; text-align: center;">
        <h2 style="color: #6D5EFC;">Welcome to LEM StratIQ</h2>
        <p>Verification code:</p>
        <div style="margin: 30px; background: #1E1F35; padding: 15px; border-radius: 12px; border: 1px solid rgba(109,94,252,0.3);">
            <h1 style="font-size: 42px; color: #ffffff;">{code}</h1>
        </div>
      </body>
    </html>
    """
    msg.attach(MIMEText(html, "html"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587); server.starttls()
        server.login(sender_email, sender_pw); server.sendmail(sender_email, to_email, msg.as_string()); server.quit()
        return True
    except: return False

def send_portfolio_report(to_email: str, port_name: str, score: float, summary: str) -> bool:
    
    smtp_creds = st.secrets.get("smtp", {})
    sender_email = smtp_creds.get("email", "")
    sender_pw = smtp_creds.get("password", "")
    if not sender_email or not sender_pw: return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your LEM StratIQ Portfolio Analysis: {port_name}"
    msg["From"] = f"LEM StratIQ AI <{sender_email}>"
    msg["To"] = to_email

    summary_html = summary.replace('\n', '<br>')
    html = f"""
    <html>
      <body style="font-family: sans-serif; background-color: #0A0A1C; color: #ffffff; padding: 40px;">
        <h1 style="color: #6D5EFC;">Your AI Portfolio Report</h1>
        <p>Your Investor DNA has been mapped to: <b>{port_name}</b> (Risk Score: {score}/10)</p>
        <hr style="border: 0; border-top: 1px solid #1E1F35;">
        <h3 style="color: #3BA4FF;">AI Inference Summary</h3>
        <p style="color: #8BA6D3; line-height: 1.6;">{summary_html}</p>
        <br>
        <p style="font-size:11px; color:#556789;">This is an automated report from your LEM StratIQ Private Wealth Dashboard.</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(html, "html"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587); server.starttls()
        server.login(sender_email, sender_pw); server.sendmail(sender_email, to_email, msg.as_string()); server.quit()
        return True
    except: return False

def _do_logout():
    """
    Invalidate the server-side session in MongoDB, clear the cookie,
    and wipe all auth state from st.session_state.
    """
    sid = st.session_state.get("session_id")
    if sid:
        _sm.invalidate(sid)   # hard-delete from MongoDB
    _sm.clear_cookie()         # remove cookie from browser

    st.session_state.clear_login_token = True
    for k in ["authenticated", "user_email", "user_name", "user_provider",
              "user_avatar", "session_id"]:
        st.session_state.pop(k, None)

    st.session_state.result   = None
    st.session_state.nav_page = "home"

    if hasattr(st, "user") and hasattr(st.user, "is_logged_in") and getattr(st.user, "is_logged_in"):
        try:
            st.logout()
            return
        except Exception:
            pass
    st.rerun()


# ── HMAC helpers for the localStorage session-restore flow ───────────────────

def _session_signing_key() -> bytes:
    """
    Returns a stable per-process signing key derived from the Anthropic API key
    (already in secrets). Falls back to a random key if the secret is absent,
    which simply means the auto-login will never verify (safe fail-open to login
    screen rather than accepting forged params).
    """
    base = st.secrets.get("anthropic_api_key", _secrets.token_hex(32))
    return hashlib.sha256(f"diq_session_v1:{base}".encode()).digest()


def _sign_session(email: str, name: str) -> str:
    """Return a hex HMAC-SHA256 of 'email|name' using the server key."""
    msg = f"{email}|{name}"
    return hmac.new(_session_signing_key(), msg.encode(), hashlib.sha256).hexdigest()


def _verify_session_sig(email: str, name: str, sig: str) -> bool:
    """Constant-time verification of the session signature."""
    expected = _sign_session(email, name)
    try:
        return hmac.compare_digest(expected, sig)
    except Exception:
        return False


def restore_session_from_storage():
    """
    Restore a persistent login by reading the session_id from the browser
    cookie and validating it against MongoDB.

    Security properties:
      - The cookie value is an opaque random ID (no user data).
      - The session document lives in MongoDB — expiry is enforced server-side.
      - Forging a cookie requires guessing 384 bits of entropy (infeasible).
      - User identity (email, name) is always sourced from the DB record,
        never from the cookie or URL parameters.
      - On logout the session is hard-deleted from MongoDB; the old cookie
        value becomes permanently invalid (no replay possible).
    """
    if st.session_state.get("authenticated"):
        return

    if st.session_state.get("clear_login_token"):
        return

    # Read the session_id from the browser cookie
    sid = _sm.get_cookie()
    if not sid:
        return

    # Validate against MongoDB (enforces expiry server-side)
    session_doc = _sm.validate(sid)
    if not session_doc:
        _sm.clear_cookie()
        return

    # Session valid — populate state from the DB record (never from cookie)
    st.session_state.session_id    = sid
    st.session_state.authenticated = True
    st.session_state.user_email    = session_doc["email"]
    st.session_state.user_name     = session_doc["name"]
    st.session_state.user_provider = session_doc.get("provider", "persistent")
    st.session_state.user_avatar   = session_doc.get("avatar")
    st.session_state.show_auth     = False

    # Restore saved assessment and preferences
    try:
        import database as _db
        saved = _db.get_latest_assessment(session_doc["email"])
        if saved:
            st.session_state.result         = saved["result"]
            st.session_state.survey_answers = saved["answers"]
            st.session_state.survey_page    = "portfolio"
        user_data = _db.get_user(session_doc["email"])
        if user_data and user_data.get("preferences_json"):
            try:
                st.session_state.preferences = json.loads(user_data["preferences_json"])
            except Exception:
                pass
    except Exception:
        pass


def _handle_auth_bridge():
    """
    Bridge between built-in st.user (Google) and app's custom session_state.
    """
    if st.user.get("is_logged_in"):
        if not st.session_state.get("authenticated"):
            # Auto-sync st.user to our state
            st.session_state.authenticated = True
            st.session_state.user_name = st.user.get("name", "Google User")
            st.session_state.user_email = st.user.get("email")
            st.session_state.user_avatar = st.user.get("picture", "")
            st.session_state.auth_provider = "google"
            
            # Ensure user exists in DB
            u_email = st.user.get("email")
            if u_email:
                user = database.get_user(u_email)
                if not user:
                    database.create_user(u_email, st.user.get("name", "Google User"), "google_oauth_fresh", "1990-01-01", "google")



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
            color: #877cfc;
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
        
        /* Remove the hook's physical space footprint so the button perfectly aligns horizontally */
        div[data-testid="stElementContainer"]:has(#google-btn-hook) {{
            position: absolute !important;
            height: 0 !important;
            width: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            visibility: hidden !important;
        }}

        /* GUARANTEED hook for the native Google button */
        div[data-testid="stElementContainer"]:has(#google-btn-hook) + div[data-testid="stElementContainer"] button {{
            display: flex !important; align-items: center !important; justify-content: center !important;
            height: 52px !important; border-radius: 12px !important;
            background: rgba(255,255,255,0.08) !important; border: 1px solid {BORDER} !important;
            color: #ffffff !important; font-weight: 700 !important; text-decoration: none !important; 
            transition: all 0.25s ease !important; width: 100% !important; gap: 12px !important;
            margin-bottom: 0 !important;
            
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z' fill='%234285F4'/%3E%3Cpath d='M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z' fill='%2334A853'/%3E%3Cpath d='M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z' fill='%23FBBC05'/%3E%3Cpath d='M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z' fill='%23EA4335'/%3E%3C/svg%3E") !important;
            background-repeat: no-repeat !important;
            background-position: calc(50% - 38px) center !important;
            background-size: 18px 18px !important;
            padding-left: 20px !important;
        }}
        
        div[data-testid="stElementContainer"]:has(#google-btn-hook) + div[data-testid="stElementContainer"] button:hover {{
            background-color: rgba(255,255,255,0.15) !important; 
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z' fill='%234285F4'/%3E%3Cpath d='M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z' fill='%2334A853'/%3E%3Cpath d='M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z' fill='%23FBBC05'/%3E%3Cpath d='M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z' fill='%23EA4335'/%3E%3C/svg%3E") !important;
            background-repeat: no-repeat !important;
            background-position: calc(50% - 38px) center !important;
            background-size: 18px 18px !important;
            border-color: {ACCENT} !important;
            box-shadow: 0 0 20px rgba(155, 114, 242, 0.2) !important;
            transform: translateY(-2px) !important;
            color: #ffffff !important;
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
        
        /* Wrapper overrides (fixes squished password eye icon) */
        div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) div[data-baseweb="input"] {{
            background: rgba(255,255,255,0.05) !important;
            border: 1px solid {BORDER} !important;
            border-radius: 10px !important;
        }}
        div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) div[data-baseweb="input"]:focus-within {{
            border-color: {ACCENT} !important;
            box-shadow: 0 0 0 1px {ACCENT} !important;
        }}
        
        /* Input tag text styling */
        div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) div[data-baseweb="input"] input {{
            background: transparent !important;
            color: white !important;
            -webkit-text-fill-color: white !important;
            border: none !important;
            box-shadow: none !important;
        }}
        
        /* Stop native browser autofill from turning inputs bright yellow */
        div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) div[data-baseweb="input"] input:-webkit-autofill,
        div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) div[data-baseweb="input"] input:-webkit-autofill:hover,
        div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) div[data-baseweb="input"] input:-webkit-autofill:focus,
        div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) div[data-baseweb="input"] input:-webkit-autofill:active {{
            -webkit-box-shadow: 0 0 0 30px #161628 inset !important;
            -webkit-text-fill-color: #ffffff !important;
            transition: background-color 5000s ease-in-out 0s !important;
            border-radius: 10px !important;
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
        google_url = "#"
        linkedin_url = "#"
        g_err = None
        l_err = None
        
        try:
            _google_oauth, _linkedin_oauth, _redirect_uri = _get_oauth()
            google_url = _google_oauth.authorize_button(
                name="Continue with Google",
                icon="https://www.google.com/favicon.ico",
                redirect_uri=_redirect_uri,
                scope="openid email profile",
                key="google_manual_auth"
            )
            linkedin_url = asyncio.run(
                _linkedin_oauth.client.get_authorization_url(
                    redirect_uri=_redirect_uri, scope=["openid", "profile", "email"]
                )
            )
        except Exception as e:
            g_err = str(e)

        # Social Buttons
        s1, s2 = st.columns(2)
        with s1:
            st.markdown('<span id="google-btn-hook"></span>', unsafe_allow_html=True)
            # Use the Manual Google Component
            st.write(google_url, unsafe_allow_html=True)
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
            if st.button("Email", icon=":material/mail:", use_container_width=True, type="primary" if tab == "email" else "secondary", key="email_tab_btn"):
                st.session_state.auth_tab = "email"; st.rerun()
        with t2:
            if st.button("Phone", icon=":material/phone_iphone:", use_container_width=True, type="primary" if tab == "phone" else "secondary", key="phone_tab_btn"):
                st.session_state.auth_tab = "phone"; st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        import random, re
        # VERIFICATION
        if st.session_state.get("auth_verify_pending"):
            if st.session_state.get("real_email_sent"):
                st.success(f"Verified: Code sent to `{st.session_state.pending_data['email']}`", icon=":material/mail:")
            else:
                # Silent failure to keep UI clean for the demo
                pass
            code_in = st.text_input("Enter 4-digit code", placeholder="####", key="auth_code_input_final", max_chars=4)
            vc1, vc2 = st.columns(2)
            with vc1:
                if st.button("Cancel", use_container_width=True, key="vc_cancel"):
                    st.session_state.auth_verify_pending = False; st.rerun()
            with vc2:
                if st.button("Verify & Proceed", type="primary", use_container_width=True, key="vc_verify"):
                    action = st.session_state.get("pending_action")
                    data   = st.session_state.get("pending_data")
                    
                    # Verify against MongoDB backend or fallback to session state mock for testing
                    is_valid = False
                    if data and "email" in data:
                        is_valid = database.verify_code(data["email"], code_in)
                        
                    # SECURITY BYPASS FOR DEMO RECORDING (0000)
                    if is_valid or code_in == st.session_state.get("mock_code") or code_in == "0000":
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
                        
                        today = date.today()
                        age = today.year - dob_in.year - ((today.month, today.day) < (dob_in.month, dob_in.day))
                        if age < 18:
                            st.error("You must be at least 18 years old to create an account.")
                            return
                            
                        if database.get_user(email_in): st.error("Email exists."); return
                        st.session_state.auth_verify_pending = True
                        vcode = str(random.randint(1000, 9999))
                        st.session_state.mock_code = vcode
                        database.save_verification_code(email_in, vcode)
                        st.session_state.pending_action = "signup_email"
                        st.session_state.pending_data = {"email": email_in, "name": name_in, "pw": pw_in, "dob": dob_in.strftime("%Y-%m-%d")}
                        
                        email_sent = send_verification_email(email_in, vcode)
                        st.session_state.real_email_sent = email_sent
                        st.rerun()
                    else:
                        user = database.get_user(email_in)
                        if user and database.check_password(pw_in, user["password_hash"]):
                            st.session_state.auth_verify_pending = True
                            vcode = str(random.randint(1000, 9999))
                            st.session_state.mock_code = vcode
                            database.save_verification_code(email_in, vcode)
                            st.session_state.pending_action = "login_email"
                            st.session_state.pending_data = {"email": email_in, "name": user["name"]}
                            
                            email_sent = send_verification_email(email_in, vcode)
                            st.session_state.real_email_sent = email_sent
                            st.rerun()
                        else: st.error("Invalid credentials.")
        else:
            # PHONE PICKER RESTORED
            if mode == "signup":
                name_in_phone = st.text_input("FULL NAME", placeholder="John Doe", key="phone_name_f")
                dob_in_phone = st.date_input(
                    "DATE OF BIRTH",
                    value=datetime.date(1990, 1, 1),
                    min_value=datetime.date(1900, 1, 1),
                    max_value=datetime.date.today(),
                    key="phone_dob_f"
                )

            p1, p2 = st.columns([0.4, 0.6])
            with p1:
                p_code = st.selectbox("CODE", GLOBAL_COUNTRIES, index=14, key="auth_p_code_f") # default +44 UK
            with p2:
                p_num = st.text_input("NUMBER", placeholder="7123 456789", key="phone_f_final")
            
            phone_pw_in = st.text_input("PASSWORD", type="password", key="phone_pw_f_final")
            st.checkbox("Keep me logged in", value=True, key="rem_f_phone")
            
            _btn_col2, _ = st.columns(2)
            with _btn_col2:
                btn_text = "Sign In Now" if mode == "login" else "Create Account"
                if st.button(btn_text, type="primary", use_container_width=True, key="phone_gobutton"):
                    if not p_num or not phone_pw_in: st.error("All fields mandatory."); return
                    
                    import re
                    # Strip spaces and formatting
                    clean_p = re.sub(r'[\s-]', '', p_num)
                    if not clean_p.isdigit() or len(clean_p) < 7 or len(clean_p) > 15:
                        st.error("Invalid phone number format. Please enter a valid number (7-15 digits).")
                        return
                    
                    full_phone = f"{p_code} {clean_p}"
                    st.session_state.auth_verify_pending = True
                    st.session_state.mock_code = "1234"
                    
                    if mode == "signup":
                        if not name_in_phone: st.error("Name mandatory."); return
                        
                        today = date.today()
                        age = today.year - dob_in_phone.year - ((today.month, today.day) < (dob_in_phone.month, dob_in_phone.day))
                        if age < 18:
                            st.error("You must be at least 18 years old to create an account.")
                            return
                            
                        # Here you'd check DB if phone exists
                        st.session_state.pending_action = "signup_phone"
                        st.session_state.pending_data = {"phone": full_phone, "name": name_in_phone, "pw": phone_pw_in, "dob": dob_in_phone.strftime("%Y-%m-%d")}
                    else:
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

