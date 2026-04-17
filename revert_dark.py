import re

with open("ai_robo_advisor/app.py", "r") as f:
    text = f.read()

# 1. Variables
text = text.replace('CANVAS  = "#F7F8FB"', 'CANVAS  = "#0B0B1A"')
text = text.replace('PANEL   = "rgba(255, 255, 255, 0.9)"', 'PANEL   = "rgba(18, 18, 38, 0.72)"')
text = text.replace('BORDER  = "rgba(0, 0, 0, 0.08)"', 'BORDER  = "rgba(155, 114, 242, 0.22)"')
text = text.replace('TEXT    = "#1C1C2A"', 'TEXT    = "#F3F3F9"')
text = text.replace('MUTED   = "rgba(28, 28, 42, 0.55)"', 'MUTED   = "rgba(237, 237, 243, 0.55)"')
text = text.replace('TMPL    = "plotly_white"', 'TMPL    = "plotly_dark"')

# 2. Hardcoded #1C1C2A
text = text.replace('#1C1C2A', '#ffffff')

# 3. rgba values reverted
text = text.replace('rgba(28,28,42,0.5)', 'rgba(237,237,243,0.5)')
text = text.replace('rgba(28,28,42,0.7)', 'rgba(237,237,243,0.7)')
text = text.replace('rgba(28,28,42,0.85)', 'rgba(237,237,243,0.85)')
text = text.replace('rgba(28,28,42,0.45)', 'rgba(237,237,243,0.45)')
text = text.replace('rgba(28,28,42,0.4)', 'rgba(237,237,243,0.4)')
text = text.replace('background:rgba(0,0,0,0.04)', 'background:rgba(0,0,0,0.2)')
text = text.replace('background:rgba(0,0,0,0.02)', 'background:rgba(255,255,255,0.03)')
text = text.replace('background:rgba(0,0,0,0.01)', 'background:rgba(255,255,255,0.02)')

# 4. Auth Modal
text = text.replace('background: #FFFFFF !important;', 'background: linear-gradient(145deg, rgba(14,12,28,0.99), rgba(6,4,16,0.99)) !important;')
text = text.replace('border: 1px solid #E6E6EF', 'border: 1px solid rgba(255,255,255,0.1)')

# 5. Native Streamlit Inputs
old_input = """div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) [data-baseweb="input"] {{
  background-color: #FAFBFF !important;
  border-radius: 12px;
  border: 1px solid #E6E6EF;
  transition: all 0.2s;
}}"""
new_input = """div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) [data-baseweb="input"] {{
  background-color: rgba(255,255,255,0.04) !important;
  border-radius: 12px;
  border: 1px solid rgba(138,43,226,0.25) !important;
  transition: all 0.2s;
  color: #fff !important;
}}"""
text = text.replace(old_input, new_input)

# 6. Nav Bar HTML Background
text = text.replace('background: rgba(255, 255, 255, 0.85);', 'background: rgba(11, 11, 26, 0.9);')

with open("ai_robo_advisor/app.py", "w") as f:
    f.write(text)
