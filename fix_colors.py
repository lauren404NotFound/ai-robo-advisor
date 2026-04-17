with open("ai_robo_advisor/app.py", "r") as f:
    text = f.read()

# Fix remaining light-text colors
text = text.replace('color:#fff;', 'color:#1C1C2A;')
text = text.replace('color: #fff;', 'color: #1C1C2A;')
text = text.replace('rgba(237,237,243,0.5)', 'rgba(28,28,42,0.5)')
text = text.replace('rgba(237,237,243,0.7)', 'rgba(28,28,42,0.7)')
text = text.replace('rgba(237,237,243,0.85)', 'rgba(28,28,42,0.85)')
text = text.replace('rgba(237,237,243,0.45)', 'rgba(28,28,42,0.45)')
text = text.replace('rgba(237,237,243,0.4)', 'rgba(28,28,42,0.4)')
text = text.replace('background:rgba(0,0,0,0.2)', 'background:rgba(0,0,0,0.04)')
text = text.replace('background:rgba(255,255,255,0.03)', 'background:rgba(0,0,0,0.02)')
text = text.replace('background:rgba(255,255,255,0.04)', 'background:rgba(0,0,0,0.02)')
text = text.replace('background:rgba(255,255,255,0.02)', 'background:rgba(0,0,0,0.01)')
text = text.replace('border: 1px solid rgba(255,255,255,0.1)', 'border: 1px solid #E6E6EF')

# Fix user_email in page_more
text = text.replace('user_email = st.session_state.get("user", {}).get("email", "guest")', 
                    'user_email = st.session_state.get("user_email", "guest") or "guest"')

with open("ai_robo_advisor/app.py", "w") as f:
    f.write(text)

