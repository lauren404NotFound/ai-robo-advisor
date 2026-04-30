"""
split_app.py
============
One-shot script that reads the monolithic app.py and writes the ui/ package.
Run from "Demo_prototype copy" directory:
    python split_app.py
"""
import os

SRC = "ai_robo_advisor/app.py"
UI  = "ai_robo_advisor/ui"

with open(SRC, encoding="utf-8") as f:
    lines = f.readlines()   # 1-indexed via lines[n-1]

def L(start, end):
    """Return lines [start..end] inclusive (1-based)."""
    return "".join(lines[start-1:end])

# ─────────────────────────────────────────────────────────────────────────────
# 1. ui/__init__.py
# ─────────────────────────────────────────────────────────────────────────────
with open(f"{UI}/__init__.py", "w", encoding="utf-8") as f:
    f.write('"""ui package — split from the monolithic app.py."""\n')

# ─────────────────────────────────────────────────────────────────────────────
# 2. ui/styles.py  — theme constants, get_svg(), global CSS injector
#    Lines 1–808 but we skip the module docstring (1-27) and take from line 16
#    We export: ACCENT, ACCENT2 … all colour constants, GLOBAL_CURRENCIES,
#               GLOBAL_COUNTRIES, get_svg, inject_global_css
# ─────────────────────────────────────────────────────────────────────────────
styles_header = '''\
"""
ui/styles.py
============
Theme constants, SVG icon helper, and global CSS injector.
Extracted from the monolithic app.py.
"""
from __future__ import annotations
import streamlit as st

'''
styles_body = L(109, 807)   # colour constants → end of <style>/<script> block

with open(f"{UI}/styles.py", "w", encoding="utf-8") as f:
    f.write(styles_header)
    f.write(styles_body)
    f.write("\n\ndef inject_global_css():\n")
    f.write('    """Call once at the top of app.py to apply the global theme."""\n')
    f.write("    pass  # CSS is already injected above at module import time via st.markdown\n")

# ─────────────────────────────────────────────────────────────────────────────
# 3. ui/auth.py  — session helpers, email functions, auth modal
#    Sections: 814-968 (helpers+email), 1194-1227 (restore session),
#              1631-1911 (nav/auth bridge — split off _handle_auth_bridge &
#              proxy buttons from render_nav since render_nav lives in nav.py)
#              1920-2295 (render_auth_modal)
# ─────────────────────────────────────────────────────────────────────────────
auth_header = '''\
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
import os, datetime, json, random, re
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

'''

auth_body = (
    L(814, 968)     # _auth_check, _user_email, _user_name, _session_cache,
                    # _do_login, get_currency_symbol, send_*email, _do_logout
    + "\n\n"
    + L(1194, 1227)  # restore_session_from_storage
    + "\n\n"
    + L(1631, 1650)  # _handle_auth_bridge
    + "\n\n"
    + L(1920, 2295)  # render_auth_modal
)

with open(f"{UI}/auth.py", "w", encoding="utf-8") as f:
    f.write(auth_header)
    f.write(auth_body)

# ─────────────────────────────────────────────────────────────────────────────
# 4. ui/ai_engine.py  — QUESTIONS list + all AI explanation functions
#    Lines 1067–1145, 1298–1445
# ─────────────────────────────────────────────────────────────────────────────
ai_header = '''\
"""
ui/ai_engine.py
===============
Survey questions definition and AI explanation engine:
  - QUESTIONS: 10-question investor risk survey
  - generate_advanced_explanation(): rule-based technical paragraphs
  - get_real_claude_insight(): live Claude 3.5 Sonnet call
  - get_ai_explanation(): unified facade (Claude → local fallback)
"""
from __future__ import annotations
import streamlit as st

# Imports resolved at call time to avoid circular dependencies
def _get_claude():
    import app as _app
    return _app.anthropic_client, _app.claude_status

def _get_local_explain():
    from explainer import explain as local_explain
    return local_explain

'''

ai_body = (
    L(1067, 1145)   # QUESTIONS
    + "\n\n"
    + L(1298, 1445)  # explanation functions
)

with open(f"{UI}/ai_engine.py", "w", encoding="utf-8") as f:
    f.write(ai_header)
    f.write(ai_body)

# ─────────────────────────────────────────────────────────────────────────────
# 5. ui/charts.py  — Plotly chart helpers
#    Lines 1450–1539
# ─────────────────────────────────────────────────────────────────────────────
charts_header = '''\
"""
ui/charts.py
============
Plotly chart factory functions:
  _style, donut_chart, growth_line, monte_chart, shap_fig, prob_fig
"""
from __future__ import annotations
import plotly.graph_objects as go
import streamlit as st

from ui.styles import (
    ACCENT, ACCENT2, TEXT, GRID, TMPL, POS, NEG, PROFILE_COLORS,
)
from ui.auth import get_currency_symbol

'''

charts_body = L(1452, 1539)

with open(f"{UI}/charts.py", "w", encoding="utf-8") as f:
    f.write(charts_header)
    f.write(charts_body)

# ─────────────────────────────────────────────────────────────────────────────
# 6. ui/nav.py  — navbar (render_nav + _handle_query_params)
#    Lines 1542–1912  (stops before auth_bridge which is in auth.py)
# ─────────────────────────────────────────────────────────────────────────────
nav_header = '''\
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
import database

'''

nav_body = L(1545, 1912)

with open(f"{UI}/nav.py", "w", encoding="utf-8") as f:
    f.write(nav_header)
    f.write(nav_body)

# ─────────────────────────────────────────────────────────────────────────────
# 7. ui/page_home.py
#    Lines 2302–2739
# ─────────────────────────────────────────────────────────────────────────────
home_header = '''\
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

'''

home_body = L(2302, 2739)

with open(f"{UI}/page_home.py", "w", encoding="utf-8") as f:
    f.write(home_header)
    f.write(home_body)

# ─────────────────────────────────────────────────────────────────────────────
# 8. ui/page_dashboard.py  — survey + portfolio full dashboard
#    Lines 2743–3557
# ─────────────────────────────────────────────────────────────────────────────
dash_header = '''\
"""
ui/page_dashboard.py
====================
Dashboard page: authentication gate, survey wizard, portfolio results.
Includes: page_dashboard, _render_survey, _render_analysing, _render_portfolio
"""
from __future__ import annotations
import os, json, datetime
import streamlit as st
import numpy as np
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

def _get_model_objects():
    import app as _app
    return _app.MODEL_PATH

'''

dash_body = L(2743, 3557)

with open(f"{UI}/page_dashboard.py", "w", encoding="utf-8") as f:
    f.write(dash_header)
    f.write(dash_body)

# ─────────────────────────────────────────────────────────────────────────────
# 9. ui/page_insights.py
#    Lines 3559–3663
# ─────────────────────────────────────────────────────────────────────────────
insights_header = '''\
"""
ui/page_insights.py
===================
"Why DeepAtomicIQ" / insights page.
"""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go

from ui.styles import ACCENT, ACCENT2, MUTED, PANEL, BORDER, get_svg, POS, NEG

'''

insights_body = L(3559, 3663)

with open(f"{UI}/page_insights.py", "w", encoding="utf-8") as f:
    f.write(insights_header)
    f.write(insights_body)

# ─────────────────────────────────────────────────────────────────────────────
# 10. ui/page_market.py
#     Lines 3666–4190
# ─────────────────────────────────────────────────────────────────────────────
market_header = '''\
"""
ui/page_market.py
=================
Live market data page.
"""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
import datetime

from ui.styles import ACCENT, ACCENT2, MUTED, PANEL, BORDER, get_svg, POS, NEG, TMPL, TEXT, GRID
from ui.auth import get_currency_symbol
import database

'''

market_body = L(3666, 4190)

with open(f"{UI}/page_market.py", "w", encoding="utf-8") as f:
    f.write(market_header)
    f.write(market_body)

# ─────────────────────────────────────────────────────────────────────────────
# 11. ui/page_more.py
#     Lines 4192–4412
# ─────────────────────────────────────────────────────────────────────────────
more_header = '''\
"""
ui/page_more.py
===============
Preferences / "More" settings page.
"""
from __future__ import annotations
import json
import streamlit as st

from ui.styles import ACCENT, ACCENT2, MUTED, PANEL, BORDER, get_svg, GLOBAL_CURRENCIES
from ui.auth import get_currency_symbol
import database

'''

more_body = L(4192, 4412)

with open(f"{UI}/page_more.py", "w", encoding="utf-8") as f:
    f.write(more_header)
    f.write(more_body)

# ─────────────────────────────────────────────────────────────────────────────
# 12. ui/page_account.py  (includes page_billing)
#     Lines 4339–4718
# ─────────────────────────────────────────────────────────────────────────────
account_header = '''\
"""
ui/page_account.py
==================
User account/profile page and billing page.
"""
from __future__ import annotations
import json, datetime
import streamlit as st

from ui.styles import ACCENT, ACCENT2, ACCENT3, MUTED, PANEL, BORDER, get_svg, POS, NEG
from ui.auth import get_currency_symbol, _do_logout, update_user_name, update_password
import database

'''

account_body = L(4339, 4718)

with open(f"{UI}/page_account.py", "w", encoding="utf-8") as f:
    f.write(account_header)
    f.write(account_body)

# ─────────────────────────────────────────────────────────────────────────────
# 13. ui/chatbot.py
#     Lines 4741–5021
# ─────────────────────────────────────────────────────────────────────────────
chatbot_header = '''\
"""
ui/chatbot.py
=============
Floating AI chatbot widget (Gemini-powered).
Call render_chatbot() after main_router() in app.py.
"""
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components

from ui.styles import get_svg, ACCENT

'''

chatbot_body = L(4741, 5021)

# Wrap the chatbot body in a function so it doesn't auto-execute on import
chatbot_body_wrapped = (
    "def render_chatbot():\n"
    "    \"\"\"Inject the floating chatbot widget.\"\"\"\n"
    + "\n".join("    " + line for line in chatbot_body.splitlines())
    + "\n"
)

with open(f"{UI}/chatbot.py", "w", encoding="utf-8") as f:
    f.write(chatbot_header)
    f.write(chatbot_body_wrapped)

# ─────────────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────────────
modules = [
    "__init__.py", "styles.py", "auth.py", "ai_engine.py",
    "charts.py", "nav.py", "page_home.py", "page_dashboard.py",
    "page_insights.py", "page_market.py", "page_more.py",
    "page_account.py", "chatbot.py",
]
print("✅ ui/ package written:")
for m in modules:
    path = f"{UI}/{m}"
    size = os.path.getsize(path)
    print(f"   {m:<25} {size:>8,} bytes")
