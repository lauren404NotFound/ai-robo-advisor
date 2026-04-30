"""
ui/chatbot.py
=============
Floating Claude AI chatbot widget — fixed bottom-right on every page.
Call render_chatbot() at the bottom of app.py after main_router().
"""
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components


def _get_system_prompt() -> str:
    base = """You are DeepAtomicIQ Assistant, an expert AI investment adviser for LEM StratIQ.
You help users understand their portfolio, investment concepts, and financial planning.
You are warm, professional, and speak in plain English. UK English spelling.
Keep responses concise — 2-4 sentences unless more detail is truly needed.
Never use emojis. Never say "as an AI"."""

    result = st.session_state.get("result")
    if result:
        port  = result.get("portfolio", {})
        stats = port.get("stats", {})
        alloc = port.get("allocation_pct", {})
        cat   = port.get("risk_category", "Balanced")
        score = result.get("score", 5)
        base += f"""

User's current portfolio:
- Risk profile: {cat} (score {score:.1f}/10)
- Expected annual return: {stats.get('expected_annual_return', 0):.1f}%
- Volatility: {stats.get('expected_volatility', 0):.1f}%
- Sharpe ratio: {stats.get('sharpe_ratio', 0):.2f}
- Allocation: {alloc}

Reference this when answering questions about their portfolio."""
    return base


def _call_claude(messages: list) -> str:
    try:
        import anthropic
        key = (
            st.secrets.get("anthropic_api_key")
            or st.secrets.get("ANTHROPIC_API_KEY")
            or st.secrets.get("anthropic", {}).get("api_key")
        )
        if not key:
            return "API key not configured — please check your Streamlit secrets."
        client = anthropic.Anthropic(api_key=key)
        resp   = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=350,
            system=_get_system_prompt(),
            messages=messages,
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return f"Connection error — please try again. ({type(e).__name__})"


def render_chatbot():
    """Inject the floating chatbot. Call once per page at the bottom of app.py."""

    # ── Session init ──────────────────────────────────────────────────────────
    if "cb_open"     not in st.session_state: st.session_state.cb_open     = False
    if "cb_messages" not in st.session_state: st.session_state.cb_messages = []
    if "cb_key"      not in st.session_state: st.session_state.cb_key      = 0

    # ── Inject persistent floating HTML/CSS (always present) ─────────────────
    name = ""
    if st.session_state.get("user_name"):
        name = st.session_state.user_name.strip().split()[0]

    has_portfolio = bool(st.session_state.get("result"))
    if has_portfolio:
        welcome = f"Hi{' ' + name if name else ''}! I can see your portfolio is set up. Ask me anything about your investments or financial planning."
    else:
        welcome = f"Hi{' ' + name if name else ''}! I'm your AI investment assistant. Ask me anything about investing or how LEM StratIQ works."

    # Build message HTML
    msgs_html = ""
    for m in st.session_state.cb_messages[-30:]:
        if m["role"] == "user":
            msgs_html += f'<div class="cb-bubble cb-user">{m["content"]}</div>'
        else:
            msgs_html += f'<div class="cb-bubble cb-bot">{m["content"]}</div>'

    open_class = "cb-open" if st.session_state.cb_open else ""

    components.html(f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', system-ui, sans-serif; }}

  /* FAB button */
  #cb-fab {{
    position: fixed;
    bottom: 28px; right: 28px;
    width: 56px; height: 56px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6D5EFC 0%, #3BA4FF 100%);
    box-shadow: 0 6px 28px rgba(109,94,252,0.55);
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; z-index: 99999;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    border: none;
  }}
  #cb-fab:hover {{
    transform: scale(1.08);
    box-shadow: 0 10px 36px rgba(109,94,252,0.7);
  }}
  #cb-fab svg {{ transition: transform 0.3s ease; }}

  /* Chat panel */
  #cb-panel {{
    position: fixed;
    bottom: 96px; right: 28px;
    width: 360px;
    background: #ffffff;
    border-radius: 20px;
    box-shadow: 0 12px 60px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.08);
    display: flex; flex-direction: column;
    overflow: hidden;
    z-index: 99998;
    transform: scale(0.92) translateY(16px);
    opacity: 0;
    pointer-events: none;
    transition: transform 0.25s cubic-bezier(0.34,1.56,0.64,1), opacity 0.2s ease;
    max-height: 520px;
  }}
  #cb-panel.cb-open {{
    transform: scale(1) translateY(0);
    opacity: 1;
    pointer-events: all;
  }}

  /* Header */
  .cb-header {{
    background: linear-gradient(135deg, #6D5EFC 0%, #3BA4FF 100%);
    padding: 14px 18px;
    display: flex; align-items: center; gap: 12px;
  }}
  .cb-avatar {{
    width: 38px; height: 38px; border-radius: 50%;
    background: rgba(255,255,255,0.25);
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; flex-shrink: 0;
    border: 2px solid rgba(255,255,255,0.4);
  }}
  .cb-header-text {{ flex: 1; }}
  .cb-header-name {{ font-size: 14px; font-weight: 700; color: #fff; }}
  .cb-header-sub  {{ font-size: 11px; color: rgba(255,255,255,0.7); margin-top: 1px; }}
  .cb-online {{
    width: 9px; height: 9px; border-radius: 50%;
    background: #4AE3A0;
    box-shadow: 0 0 8px #4AE3A0;
    flex-shrink: 0;
  }}
  .cb-close {{
    background: rgba(255,255,255,0.15); border: none;
    width: 26px; height: 26px; border-radius: 50%;
    cursor: pointer; color: #fff; font-size: 14px;
    display: flex; align-items: center; justify-content: center;
    transition: background 0.15s;
  }}
  .cb-close:hover {{ background: rgba(255,255,255,0.3); }}

  /* Messages */
  .cb-messages {{
    flex: 1; overflow-y: auto; padding: 16px 14px;
    display: flex; flex-direction: column; gap: 10px;
    background: #f8f9fc;
    min-height: 200px; max-height: 320px;
  }}
  .cb-messages::-webkit-scrollbar {{ width: 4px; }}
  .cb-messages::-webkit-scrollbar-track {{ background: transparent; }}
  .cb-messages::-webkit-scrollbar-thumb {{ background: #d1d5db; border-radius: 4px; }}

  .cb-bubble {{
    max-width: 82%; padding: 10px 14px;
    font-size: 13px; line-height: 1.55;
    border-radius: 18px; word-break: break-word;
  }}
  .cb-bot {{
    background: #ffffff; color: #1a1a2e;
    border-radius: 4px 18px 18px 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    align-self: flex-start;
  }}
  .cb-user {{
    background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
    color: #ffffff;
    border-radius: 18px 18px 4px 18px;
    align-self: flex-end;
    box-shadow: 0 2px 8px rgba(109,94,252,0.3);
  }}

  /* Quick replies */
  .cb-quick {{
    padding: 10px 14px 4px;
    display: flex; flex-wrap: wrap; gap: 6px;
    background: #f8f9fc;
  }}
  .cb-qbtn {{
    background: #fff; border: 1px solid #e5e7eb;
    border-radius: 20px; padding: 5px 12px;
    font-size: 11.5px; color: #6D5EFC; cursor: pointer;
    transition: all 0.15s; white-space: nowrap;
    font-weight: 600;
  }}
  .cb-qbtn:hover {{
    background: #6D5EFC; color: #fff; border-color: #6D5EFC;
  }}

  /* Input */
  .cb-input-wrap {{
    padding: 12px 14px;
    background: #fff;
    border-top: 1px solid #f0f0f5;
    display: flex; gap: 8px; align-items: center;
  }}
  .cb-input {{
    flex: 1; border: 1.5px solid #e5e7eb; border-radius: 24px;
    padding: 9px 16px; font-size: 13px; color: #1a1a2e;
    outline: none; transition: border-color 0.2s;
    background: #f8f9fc;
  }}
  .cb-input:focus {{ border-color: #6D5EFC; background: #fff; }}
  .cb-input::placeholder {{ color: #9ca3af; }}
  .cb-send {{
    width: 38px; height: 38px; border-radius: 50%;
    background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
    border: none; cursor: pointer; color: #fff;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 3px 12px rgba(109,94,252,0.4);
    transition: transform 0.15s, box-shadow 0.15s;
  }}
  .cb-send:hover {{ transform: scale(1.08); box-shadow: 0 5px 16px rgba(109,94,252,0.55); }}
</style>
</head>
<body>

<!-- FAB -->
<button id="cb-fab" onclick="toggleChat()">
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
</button>

<!-- Chat panel -->
<div id="cb-panel" class="{open_class}">
  <!-- Header -->
  <div class="cb-header">
    <div class="cb-avatar">✦</div>
    <div class="cb-header-text">
      <div class="cb-header-name">DeepAtomicIQ Assistant</div>
      <div class="cb-header-sub">Powered by Claude AI</div>
    </div>
    <div class="cb-online"></div>
    <button class="cb-close" onclick="toggleChat()">✕</button>
  </div>

  <!-- Messages -->
  <div class="cb-messages" id="cb-msgs">
    {'<div class="cb-bubble cb-bot">' + welcome + '</div>' if not msgs_html else msgs_html}
  </div>

  <!-- Quick replies (only show when no messages) -->
  {'<div class="cb-quick"><button class="cb-qbtn" onclick="sendQuick(this)">What is my Sharpe ratio?</button><button class="cb-qbtn" onclick="sendQuick(this)">Explain my allocation</button><button class="cb-qbtn" onclick="sendQuick(this)">What is volatility?</button><button class="cb-qbtn" onclick="sendQuick(this)">How does rebalancing work?</button></div>' if not msgs_html else ''}

  <!-- Input -->
  <div class="cb-input-wrap">
    <input class="cb-input" id="cb-input" type="text"
      placeholder="Write your message..."
      onkeydown="if(event.key==='Enter')sendMsg()">
    <button class="cb-send" onclick="sendMsg()">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
      </svg>
    </button>
  </div>
</div>

<script>
function toggleChat() {{
  var panel = document.getElementById('cb-panel');
  panel.classList.toggle('cb-open');
}}

function scrollToBottom() {{
  var msgs = document.getElementById('cb-msgs');
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
}}
scrollToBottom();

function sendQuick(btn) {{
  document.getElementById('cb-input').value = btn.textContent;
  sendMsg();
}}

function sendMsg() {{
  var input = document.getElementById('cb-input');
  var text  = input.value.trim();
  if (!text) return;
  input.value = '';
  // Send to Streamlit via URL param trick
  window.parent.postMessage({{type: 'streamlit:setComponentValue', value: text}}, '*');
}}
</script>
</body>
</html>
""", height=0, scrolling=False)

    # ── Streamlit-side: hidden input + send button ────────────────────────────
    # The FAB and panel are pure HTML injected via components.html above.
    # For actual message sending we use a hidden Streamlit form.

    with st.container():
        st.markdown("""
        <style>
        /* Hide the Streamlit chatbot form — interaction happens via the HTML widget */
        div[data-testid="stForm"]:has(#cb-hidden-marker) {
            position: fixed !important;
            bottom: 160px !important;
            right: 28px !important;
            width: 360px !important;
            z-index: 100000 !important;
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
        }
        div[data-testid="stForm"]:has(#cb-hidden-marker) > div {
            display: flex !important;
            gap: 8px !important;
            align-items: center !important;
            background: #fff !important;
            border-radius: 28px !important;
            padding: 8px 8px 8px 16px !important;
            box-shadow: 0 2px 12px rgba(0,0,0,0.1) !important;
            border: 1.5px solid #e5e7eb !important;
        }
        div[data-testid="stForm"]:has(#cb-hidden-marker) input {
            border: none !important;
            background: transparent !important;
            font-size: 13px !important;
            color: #1a1a2e !important;
            box-shadow: none !important;
        }
        div[data-testid="stForm"]:has(#cb-hidden-marker) button[kind="primaryFormSubmit"] {
            width: 36px !important; height: 36px !important;
            border-radius: 50% !important;
            background: linear-gradient(135deg, #6D5EFC, #3BA4FF) !important;
            padding: 0 !important;
            border: none !important;
            box-shadow: 0 3px 10px rgba(109,94,252,0.4) !important;
            min-width: 0 !important;
        }
        </style>
        <div id="cb-hidden-marker"></div>
        """, unsafe_allow_html=True)

        if st.session_state.cb_open:
            with st.form(key=f"cb_form_{st.session_state.cb_key}", clear_on_submit=True):
                cols = st.columns([6, 1])
                with cols[0]:
                    user_input = st.text_input(
                        "", placeholder="Write your message...",
                        label_visibility="collapsed",
                        key=f"cb_text_{st.session_state.cb_key}"
                    )
                with cols[1]:
                    submitted = st.form_submit_button("→")

            if submitted and user_input and user_input.strip():
                msg = user_input.strip()
                st.session_state.cb_messages.append({"role": "user", "content": msg})
                claude_msgs = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.cb_messages[-12:]
                ]
                with st.spinner(""):
                    reply = _call_claude(claude_msgs)
                st.session_state.cb_messages.append({"role": "assistant", "content": reply})
                st.session_state.cb_key += 1
                st.rerun()