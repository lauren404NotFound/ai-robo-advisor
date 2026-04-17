import re
with open("ai_robo_advisor/app.py", "r") as f:
    text = f.read()

# Fix authentication state keys
text = text.replace('st.session_state.get("is_authenticated"', 'st.session_state.get("authenticated"')
text = text.replace('st.session_state.is_authenticated = False', 'st.session_state.authenticated = False')

# Fix user reference in render_nav
text = text.replace('user = st.session_state.get("user", {})', '')
text = text.replace('name = user.get("name", "User")', 'name = st.session_state.get("user_name", "User")')
text = text.replace('st.session_state.user = None', 'st.session_state.user_name = None; st.session_state.user_email = None')

# Fix database method calls in page_more
text = text.replace('user_data = get_user(user_email)', 'user_data = database.get_user(user_email)')
text = text.replace('update_user_preferences(user_email, new_prefs)', 'database.update_user_preferences(user_email, new_prefs)')
text = text.replace('save_ticket(user_email, subj, msg)', 'database.save_ticket(user_email, subj, msg)')

# Fix theme variables to light theme
text = text.replace('CANVAS  = "#0B0B1A"  # Deep Space Navy', 'CANVAS  = "#F7F8FB"  # Light background')
text = text.replace('PANEL   = "rgba(18, 18, 38, 0.72)"', 'PANEL   = "rgba(255, 255, 255, 0.9)"')
text = text.replace('BORDER  = "rgba(155, 114, 242, 0.22)"', 'BORDER  = "rgba(0, 0, 0, 0.08)"')
text = text.replace('TEXT    = "#F3F3F9"', 'TEXT    = "#1C1C2A"')
text = text.replace('TMPL    = "plotly_dark"', 'TMPL    = "plotly_white"')
text = text.replace('MUTED   = "rgba(243, 243, 249, 0.55)"', 'MUTED   = "rgba(28, 28, 42, 0.55)"')

# stApp background
text = re.sub(
    r'\.stApp \{\s*background:[^}]+;[ \t]*\n[ \t]*color: \{TEXT\};\s*\}',
    '.stApp {\\n  background: linear-gradient(135deg, #F9F9FF 0%, #F0F2FC 100%);\\n  color: {TEXT};\\n}',
    text
)

# Nav bar styling
old_nav_active = r'\.nav-link-wrap\.active \.nav-link \{\s*color: #fff; background: \{ACCENT\};\s*box-shadow: 0 8px 24px rgba\(155, 114, 242, 0\.35\);\s*\}'
new_nav_active = '.nav-link-wrap.active .nav-link {\\n  color: {ACCENT}; font-weight: 700; background: transparent;\\n}'
text = re.sub(old_nav_active, new_nav_active, text)

# Nav bar html overrides
text = text.replace('background: rgba(11, 11, 26, 0.9);', 'background: rgba(255, 255, 255, 0.85);')
text = text.replace('font-size: 19px; font-weight: 900; color: #fff;', 'font-size: 19px; font-weight: 900; color: #1C1C2A;')

# Modal styling 
text = text.replace('background: linear-gradient(145deg, rgba(14,12,28,0.99), rgba(6,4,16,0.99)) !important;', 'background: #FFFFFF !important;')
text = text.replace('color: #fff', 'color: #1C1C2A') # replace some hardcoded whites

# HTML replacements in render_nav
text = text.replace('color="#fff" if page=="home" else MUTED', 'color=ACCENT if page=="home" else MUTED')
text = text.replace('color="#fff" if page=="dashboard" else MUTED', 'color=ACCENT if page=="dashboard" else MUTED')
text = text.replace('color="#fff" if page=="news" else MUTED', 'color=ACCENT if page=="news" else MUTED')
text = text.replace('color="#fff" if page=="market" else MUTED', 'color=ACCENT if page=="market" else MUTED')
text = text.replace('color="#fff" if page=="search" else MUTED', 'color=ACCENT if page=="search" else MUTED')
text = text.replace('color="#fff" if page=="more" else MUTED', 'color=ACCENT if page=="more" else MUTED')

with open("ai_robo_advisor/app.py", "w") as f:
    f.write(text)

