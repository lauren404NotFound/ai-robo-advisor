"""
ui/nav.py
=========
Fixed top navigation bar:
  - NAV_ITEMS
  - _handle_query_params(): URL param → session_state routing
  - render_nav(): injects HTML navbar + proxy buttons
"""
from __future__ import annotations
import streamlit as st

from ui.styles import ACCENT, ACCENT2, BORDER, MUTED, get_svg
from ui.auth import _do_logout, _handle_auth_bridge
from session_manager import SessionManager as _SM
_sm = _SM()
import database

NAV_ITEMS = [
    ("home",      "Home"),
    ("dashboard", "My Dashboard"),
    ("market",    "Markets"),
    ("insights",  "Why DeepAtomicIQ"),
    ("more",      "Preferences"),
]

def _handle_query_params():
    """Read URL query params set by the HTML nav and update session state."""
    params = st.query_params

    # ── Restore auth from server-side session (MongoDB) ───────────────────
    sid = _sm.get_cookie()
    if sid and not st.session_state.get("authenticated"):
        session_doc = _sm.validate(sid)
        if session_doc:
            st.session_state.authenticated  = True
            st.session_state.user_email     = session_doc["email"]
            st.session_state.user_name      = session_doc["name"]
            st.session_state.user_provider  = session_doc.get("provider", "persistent")
            st.session_state.user_avatar    = session_doc.get("avatar")
            st.session_state.session_id     = sid
            # Reload saved assessment
            saved = database.get_latest_assessment(session_doc["email"])
            if saved:
                st.session_state.result = saved["result"]
                st.session_state.survey_answers = saved["answers"]
                st.session_state.survey_page = "portfolio"
        else:
            _sm.clear_cookie()  # stale/expired cookie

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
            # FORCE CLEAN REDIRECT URI for the exchange
            STRICT_URI = REDIRECT_URI.rstrip("/")
            
            # Exchange code for token
            token = google_oauth.client.get_access_token(code=code, redirect_uri=STRICT_URI)
            jwt = token["id_token"].split(".")[1]
            jwt += "=" * ((4 - len(jwt) % 4) % 4)
            user_info = json.loads(base64.urlsafe_b64decode(jwt).decode("utf-8"))
            
            _do_login(user_info.get("email"), user_info.get("name", "Google User"), "google", user_info.get("picture"))
            if not database.get_user(user_info.get("email")):
                database.create_user_oauth(user_info.get("email"), user_info.get("name", "Google User"), "google")
        except Exception as e:
            st.error(f"⚠️ **Token Exchange Failed**: {e}")
            st.info("Check if your Google Client Secret is correct in the dashboard.")
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
        st.query_params.clear()
        _do_logout()


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

def render_nav():
    # ── Global CSS: reduce Streamlit's default top padding on all pages ──────
    st.markdown("""
    <style>
    /* Push content down just enough to clear the fixed navbar — no extra gap */
    div[data-testid="stMainBlockContainer"],
    .block-container {
        padding-top: 72px !important;
        padding-bottom: 24px !important;
    }
    /* Remove default Streamlit top anchor space */
    div[data-testid="stApp"] > section > div:first-child {
        padding-top: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    try:
        _handle_auth_bridge()
        _handle_query_params()
    except Exception as e:
        # Demote to sidebar-only — avoids "Core System Error" banner on every page
        st.sidebar.warning(f"⚠️ Nav diagnostic: {e}")

    page = st.session_state.get("nav_page", "Home")
    auth = st.session_state.get("authenticated", False)
    name = st.session_state.get("user_name", "")
    tok  = st.session_state.get("session_token", "")
    tp   = f"&_tok={tok}" if tok else ""   # token query param suffix

    def _active(p):
        return "active" if page == p else ""

    # ── Professional Nav Icons Mapping ───────────────────────────────────────
    NAV_ICONS = {
        "home":      "⊞",
        "dashboard": "⊟",
        "market":    "⌇",
        "insights":  "◎",
        "more":      "≡",
    }

    links_html = ""
    for pg_id, label in NAV_ITEMS:
        icon = NAV_ICONS.get(pg_id, "·")
        links_html += f"""
        <div class="nav-link-wrap {_active(pg_id)}">
          <a class="nav-link" href="?page={pg_id}{tp}" target="_self">
            <span class="nav-icon">{icon}</span>{label}
          </a>
        </div>
        """

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
              <a class="nav-dd-item" href="?page=account{tp}" target="_self">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                My Profile
              </a>
              <a class="nav-dd-item" href="?page=dashboard{tp}" target="_self">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><rect x="7" y="10" width="4" height="7" rx="1"/><rect x="13" y="5" width="4" height="12" rx="1"/></svg>
                My Portfolio
              </a>
              <a class="nav-dd-item" href="?page=more{tp}" target="_self">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.1a2 2 0 0 0 .73-2.72l-.22-.39a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
                Preferences
              </a>
              <div class="nav-dd-divider"></div>
              <a class="nav-dd-item nav-dd-logout" href="?logout=true{tp}" target="_self">
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
  height: 56px;
  background: rgba(8, 10, 26, 0.97);
  backdrop-filter: blur(24px) saturate(180%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 2px 20px rgba(0,0,0,0.4);
  display: flex; align-items: center;
  padding: 0 40px; gap: 0;
  font-family: 'Inter', system-ui, sans-serif;
}}
.diq-brand {{
  font-size: 15px; font-weight: 900; letter-spacing: -0.02em; color: #fff;
  display: flex; align-items: center; gap: 9px; min-width: 180px; white-space: nowrap;
  text-decoration: none;
}}
.diq-dot {{
  width: 8px; height: 8px; border-radius: 50%;
  background: linear-gradient(135deg, #6D5EFC, #4AE3A0);
  box-shadow: 0 0 8px rgba(109,94,252,0.6); flex-shrink: 0;
}}
.diq-links {{
  display: flex; align-items: center; gap: 0; flex: 1; justify-content: center;
  height: 100%;
}}
.nav-link-wrap {{
  height: 100%; display: flex; align-items: center;
}}
.nav-link {{
  color: rgba(255,255,255,0.45) !important;
  font-size: 13px !important; font-weight: 500 !important;
  transition: all 0.2s ease !important; text-decoration: none !important;
  padding: 0 18px !important; height: 56px !important;
  display: flex !important; align-items: center !important; gap: 7px !important;
  white-space: nowrap !important;
  border-bottom: 2px solid transparent !important;
  cursor: pointer !important;
}}
.nav-link:hover {{
  color: rgba(255,255,255,0.9) !important;
  background: rgba(255,255,255,0.03) !important;
}}
.nav-link-wrap.active .nav-link {{
  color: #ffffff !important;
  font-weight: 700 !important;
  border-bottom-color: #6D5EFC !important;
  background: transparent !important;
}}
.nav-icon {{
  font-size: 14px;
  opacity: 0.8;
  display: flex; align-items: center;
}}
.diq-auth {{
  display: flex; align-items: center; gap: 12px; min-width: 240px; justify-content: flex-end;
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
.nav-bell-wrap {{
  position: relative; cursor: pointer;
  width: 36px; height: 36px; border-radius: 10px;
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
  display: flex; align-items: center; justify-content: center;
  transition: background .15s;
}}
.nav-bell-wrap:hover {{ background: rgba(109,94,252,0.15); border-color: rgba(109,94,252,0.4); }}
.nav-bell-icon {{ color: rgba(237,237,243,0.6); transition: color .15s; }}
.nav-bell-wrap:hover .nav-bell-icon {{ color: #fff; }}
.nav-bell-dot {{
  position: absolute; top: 6px; right: 6px;
  width: 7px; height: 7px; border-radius: 50%;
  background: #FF6B6B; border: 1.5px solid #060814;
}}
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
    {links_html}
  </div>
  <div class="diq-auth" style="display:flex;align-items:center;gap:10px;">
    <div class="nav-bell-wrap" title="Notifications">
      <svg class="nav-bell-icon" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
      <span class="nav-bell-dot"></span>
    </div>
    <div class="nav-sep"></div>
    {auth_html}
  </div>
</div>

<script>
// Force same-tab redirection for all nav links
document.querySelectorAll('.nav-link, .nav-act-btn, .nav-dd-item').forEach(link => {{
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


