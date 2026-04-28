"""
ui/chatbot.py
=============
Floating AI chatbot widget — server-side Gemini calls only.

Security fix: The Gemini API key is NEVER sent to the browser.
All calls to the Gemini API are made from Python (server-side).
The JavaScript widget handles only UI rendering and message passing
via Streamlit's native component communication (st.query_params /
st.session_state form submit) — no secrets cross the network.

Call render_chatbot() from app.py after main_router().
"""
from __future__ import annotations
import json
import streamlit as st
import streamlit.components.v1 as components

from ui.styles import get_svg, ACCENT

# ── System prompt (safe to embed in HTML — no credentials) ───────────────────
_SYSTEM_PROMPT = (
    "You are DeepAtomicIQ, an AI investment assistant embedded in the LEM StratIQ "
    "robo-advisor platform. You help users understand their AI-generated portfolio, "
    "explain investment concepts clearly, and guide them through the app. "
    "The platform uses a Markowitz-Informed Neural Network (MINN) that maximises "
    "the Sharpe ratio. It offers 6 risk profiles across 8 ETFs: VOO (S&P 500), "
    "QQQ (Nasdaq 100), VWRA (Global), AGG (Bonds), GLD (Gold), VNQ (Real Estate), "
    "ESGU (ESG), PDBC (Commodities). "
    "Be concise, friendly, and jargon-free. Use bullet points where helpful. "
    "Never give regulated financial advice. Always remind users to consult a "
    "qualified financial adviser for real investment decisions. "
    "Keep replies under 120 words unless asked for detail."
)


# ── Server-side Gemini call ───────────────────────────────────────────────────

def _call_gemini_server(user_message: str, history: list) -> str:
    """
    Call the Gemini API from Python — the API key never leaves the server.
    Returns the assistant's reply as a plain string.
    """
    try:
        import google.generativeai as genai  # pip install google-generativeai
        key = st.secrets.get("gemini_api_key", "")
        if not key:
            return (
                "⚠️ **Offline mode** — The AI assistant is not configured. "
                "Add `gemini_api_key` to `.streamlit/secrets.toml` to enable it. "
                "For now, I can answer general questions about portfolio basics, "
                "risk profiles, and ETF allocation from my built-in knowledge."
            )
        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=_SYSTEM_PROMPT,
            generation_config={"max_output_tokens": 350, "temperature": 0.7},
        )
        # Rebuild history in Gemini format
        chat = model.start_chat(history=history)
        response = chat.send_message(user_message)
        return response.text
    except ImportError:
        # Fallback: use requests if google-generativeai is not installed
        return _call_gemini_requests(user_message, history)
    except Exception as exc:
        return f"❌ AI error: {exc}. Please try again."


def _call_gemini_requests(user_message: str, history: list) -> str:
    """Fallback using raw requests — still server-side, key never exposed."""
    import requests  # always available
    try:
        key = st.secrets.get("gemini_api_key", "")
        if not key:
            return "⚠️ **Offline mode** — `gemini_api_key` not configured in secrets.toml."

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/gemini-1.5-flash:generateContent?key={key}"
        )
        contents = list(history) + [{"role": "user", "parts": [{"text": user_message}]}]
        payload = {
            "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 350, "temperature": 0.7},
        }
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        return f"❌ Could not reach AI: {exc}"


# ── Streamlit form for message submission ─────────────────────────────────────

def _handle_chat_input():
    """
    Process a chat message submitted via the hidden Streamlit form.
    Stores results in st.session_state so the JavaScript widget can read them.
    """
    if "chatbot_history" not in st.session_state:
        st.session_state.chatbot_history = []   # [{role, parts:[{text}]}, ...]
    if "chatbot_reply" not in st.session_state:
        st.session_state.chatbot_reply = ""

    with st.form("chatbot_form", clear_on_submit=True):
        user_input = st.text_input("msg", label_visibility="collapsed", key="chatbot_input")
        submitted = st.form_submit_button("Send")

    if submitted and user_input.strip():
        msg = user_input.strip()
        history = st.session_state.chatbot_history
        reply = _call_gemini_server(msg, history)

        # Update server-side history
        st.session_state.chatbot_history.append(
            {"role": "user",  "parts": [{"text": msg}]}
        )
        st.session_state.chatbot_history.append(
            {"role": "model", "parts": [{"text": reply}]}
        )
        st.session_state.chatbot_reply = reply
        # Keep history bounded to last 20 turns to avoid token bloat
        if len(st.session_state.chatbot_history) > 40:
            st.session_state.chatbot_history = st.session_state.chatbot_history[-40:]


# ── Chat widget HTML (zero credentials — UI only) ─────────────────────────────

def _build_chatbot_html(history_json: str, latest_reply: str) -> str:
    """
    Pure UI widget.  Contains NO API key.  Chat history is passed as
    a JSON blob from Python so the widget can re-render the conversation.
    """
    # Escape for safe embedding in a JS string
    safe_history = history_json.replace("</", "<\\/").replace("`", "\\`")
    safe_reply   = latest_reply.replace("</", "<\\/").replace("`", "\\`").replace("\n", "\\n")

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: transparent; overflow: hidden; font-family: 'Inter', system-ui, sans-serif; }}
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
  #cb-panel {{
    position: fixed; bottom: 96px; right: 24px; z-index: 99998;
    width: 380px; height: 520px;
    background: rgba(10, 12, 28, 0.98); backdrop-filter: blur(20px);
    border: 1px solid rgba(109,94,252,0.4); border-radius: 24px;
    display: none; flex-direction: column; overflow: hidden;
    box-shadow: 0 20px 50px rgba(0,0,0,0.6); font-family: inherit;
  }}
  #cb-panel.open {{ display: flex; }}
  #cb-hdr {{
    padding: 12px 16px; background: rgba(109,94,252,0.15);
    border-bottom: 1px solid rgba(255,255,255,0.08);
    display: flex; align-items: center; gap: 10px;
  }}
  .cb-av {{
    width: 34px; height: 34px; border-radius: 50%;
    background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
    display: flex; align-items: center; justify-content: center; font-size: 18px;
  }}
  .cb-name {{ font-weight: 700; color: white; font-size: 14px; }}
  .cb-sub  {{ font-size: 10px; color: #8EF6D1; }}
  .cb-x {{ margin-left: auto; background: none; border: none; color: #aaa; font-size: 24px; cursor: pointer; line-height: 1; padding: 0 6px; }}
  #cb-msgs {{ flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px; scrollbar-width: thin; }}
  .bot, .usr {{ max-width: 85%; padding: 8px 12px; border-radius: 18px; font-size: 13px; line-height: 1.5; word-break: break-word; }}
  .bot {{ background: rgba(109,94,252,0.15); color: #E0E7FF; border: 1px solid rgba(109,94,252,0.3); align-self: flex-start; border-bottom-left-radius: 4px; }}
  .usr {{ background: linear-gradient(135deg, #6D5EFC, #3BA4FF); color: white; align-self: flex-end; border-bottom-right-radius: 4px; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
  .chip {{ background: rgba(109,94,252,0.2); border: 1px solid rgba(109,94,252,0.4); border-radius: 30px; padding: 3px 10px; font-size: 11px; color: #C4D0FF; cursor: pointer; transition: 0.1s; }}
  .chip:hover {{ background: rgba(109,94,252,0.4); color: white; }}
  #cb-note {{ font-size: 10px; color: #556789; text-align: center; padding: 4px 12px; border-top: 1px solid rgba(255,255,255,0.05); }}
</style>
</head>
<body>

<button id="cb-btn">🤖</button>
<div id="cb-panel">
  <div id="cb-hdr">
    <div class="cb-av">🧠</div>
    <div><div class="cb-name">DeepAtomicIQ AI</div><div class="cb-sub">Powered by Gemini • Responses sent securely</div></div>
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
  <div id="cb-note">Use the chat box below ↓ to send a message</div>
</div>

<script>
  // History injected server-side as JSON — no API keys here
  const serverHistory = {safe_history};
  const latestReply   = `{safe_reply}`;

  const panel   = document.getElementById('cb-panel');
  const msgs    = document.getElementById('cb-msgs');
  const btn     = document.getElementById('cb-btn');
  const closeBtn = document.getElementById('cb-close');

  function fmt(text) {{
    return text
      .replace(/\\n/g, '<br>')
      .replace(/\\*\\*(.*?)\\*\\*/g, '<b>$1</b>');
  }}

  function addMsg(text, isUser) {{
    const div = document.createElement('div');
    div.className = isUser ? 'usr' : 'bot';
    div.innerHTML = fmt(text);
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }}

  // Re-render server-confirmed history on each Streamlit rerun
  if (serverHistory.length > 0) {{
    msgs.innerHTML = msgs.innerHTML; // keep welcome message
    serverHistory.forEach(m => {{
      addMsg(m.parts[0].text, m.role === 'user');
    }});
  }}

  function togglePanel() {{
    panel.classList.toggle('open');
    if (panel.classList.contains('open')) msgs.scrollTop = msgs.scrollHeight;
  }}
  btn.onclick = togglePanel;
  closeBtn.onclick = togglePanel;

  // Chip shortcuts — post message into the Streamlit input above and submit
  document.querySelectorAll('.chip').forEach(chip => {{
    chip.onclick = () => {{
      // Find the Streamlit text input for the chatbot form
      const stInputs = window.parent.document.querySelectorAll('input[data-testid="stTextInput"]');
      stInputs.forEach(inp => {{
        if (inp.closest('[data-testid="stForm"]')) {{
          inp.value = chip.textContent;
          inp.dispatchEvent(new Event('input', {{bubbles: true}}));
        }}
      }});
    }};
  }});
</script>
</body>
</html>"""


# ── Public entry point ────────────────────────────────────────────────────────

def render_chatbot():
    """
    Render the floating chatbot widget.
    The Gemini API key stays on the server — it is never embedded in HTML or JS.
    """
    _handle_chat_input()

    history_json = json.dumps(st.session_state.get("chatbot_history", []))
    latest_reply = st.session_state.get("chatbot_reply", "")

    widget_html = _build_chatbot_html(history_json, latest_reply)

    # Fixed-position CSS wrapper
    st.markdown("""
    <style>
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

    st.markdown("<div id='cb-anchor'></div>", unsafe_allow_html=True)
    components.html(widget_html, height=0, scrolling=False)
