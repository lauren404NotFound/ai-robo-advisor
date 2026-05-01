"""
ui/chatbot.py
=============
Floating Claude AI chatbot — secure, split-render architecture:
- HTML + CSS injected via st.markdown (directly into page DOM)
- JS executed via components.html (iframe can reach parent document)
- Claude called server-side only (API key never exposed)
Call render_chatbot() at the bottom of app.py after main_router().
"""
from __future__ import annotations
import json
import streamlit as st
import streamlit.components.v1 as components


def _get_portfolio_context() -> str:
    result = st.session_state.get("result")
    if not result:
        return ""
    port  = result.get("portfolio", {})
    stats = port.get("stats", {})
    alloc = port.get("allocation_pct", {})
    cat   = port.get("risk_category", "Balanced")
    score = result.get("score", 5)
    return (
        f"Risk profile: {cat} (score {score:.1f}/10), "
        f"Expected return: {stats.get('expected_annual_return', 0):.1f}%, "
        f"Volatility: {stats.get('expected_volatility', 0):.1f}%, "
        f"Sharpe: {stats.get('sharpe_ratio', 0):.2f}, "
        f"Allocation: {alloc}"
    )


def _call_claude_secure(history: list) -> str:
    """Server-side Claude call — API key never leaves the server."""
    try:
        import anthropic
        key = (
            st.secrets.get("anthropic_api_key")
            or st.secrets.get("ANTHROPIC_API_KEY")
            or st.secrets.get("anthropic", {}).get("api_key")
        )
        if not key:
            return "API key not configured. Please check Streamlit secrets."

        portfolio_ctx = _get_portfolio_context()
        system = (
            "You are DeepAtomicIQ Assistant, an expert AI investment adviser for LEM StratIQ. "
            "Help users understand their portfolio, investment concepts, and financial planning. "
            "Be warm, professional, plain English, UK spelling. "
            "Keep responses to 2-4 sentences unless more detail is truly needed. "
            "Never say 'as an AI'. Never use emojis."
            + (f" User portfolio: {portfolio_ctx}" if portfolio_ctx else "")
        )

        client = anthropic.Anthropic(api_key=key)
        resp   = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            system=system,
            messages=history[-12:],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return f"Sorry, I couldn't connect right now. ({type(e).__name__})"


def render_chatbot():
    """Render the secure floating chatbot."""

    # ── Session state init ────────────────────────────────────────────────
    if "cb_open"     not in st.session_state: st.session_state.cb_open     = False
    if "cb_messages" not in st.session_state: st.session_state.cb_messages = []
    if "cb_pending"  not in st.session_state: st.session_state.cb_pending  = ""
    if "cb_key"      not in st.session_state: st.session_state.cb_key      = 0

    # ── Process pending message from JS bridge ────────────────────────────
    if st.session_state.cb_pending:
        user_msg = st.session_state.cb_pending
        st.session_state.cb_pending = ""
        st.session_state.cb_messages.append({"role": "user", "content": user_msg})
        reply = _call_claude_secure(st.session_state.cb_messages)
        st.session_state.cb_messages.append({"role": "assistant", "content": reply})
        st.session_state.cb_key += 1
        st.rerun()

    # ── Build context for JS ──────────────────────────────────────────────
    name = ""
    if st.session_state.get("user_name"):
        name = st.session_state.user_name.strip().split()[0]

    portfolio_ctx = _get_portfolio_context()
    welcome = (
        f"Hi{' ' + name if name else ''}! I can see your portfolio is set up. "
        "Ask me anything about your investments or financial planning."
        if portfolio_ctx else
        f"Hi{' ' + name if name else ''}! I'm your AI investment assistant. "
        "Ask me anything about investing or how LEM StratIQ works."
    )

    messages_json = json.dumps(st.session_state.cb_messages)
    welcome_js    = json.dumps(welcome)
    is_open_js    = json.dumps(st.session_state.cb_open)

    # ── STEP 1: Inject HTML + CSS via st.markdown ─────────────────────────
    st.markdown("""
<style>
#diq-fab {
  position: fixed !important; bottom: 24px !important; right: 24px !important;
  width: 58px !important; height: 58px !important; border-radius: 50% !important;
  background: linear-gradient(135deg, #6D5EFC, #3BA4FF) !important;
  box-shadow: 0 6px 28px rgba(109,94,252,0.55) !important;
  border: none !important; cursor: pointer !important; z-index: 999999 !important;
  display: flex !important; align-items: center !important; justify-content: center !important;
  transition: transform .2s, box-shadow .2s !important;
}
#diq-fab:hover { transform: scale(1.1) !important; box-shadow: 0 10px 36px rgba(109,94,252,0.75) !important; }
#diq-panel {
  position: fixed !important; bottom: 94px !important; right: 24px !important;
  width: 360px !important; height: 510px !important;
  background: #ffffff !important; border-radius: 20px !important;
  box-shadow: 0 16px 64px rgba(0,0,0,0.2), 0 2px 8px rgba(0,0,0,0.08) !important;
  flex-direction: column !important; overflow: hidden !important; z-index: 999998 !important;
  font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif !important;
  display: none;
}
#diq-panel.diq-open { display: flex !important; animation: diqPop .25s cubic-bezier(.34,1.56,.64,1); }
@keyframes diqPop {
  from { opacity:0; transform:scale(.9) translateY(16px); }
  to   { opacity:1; transform:scale(1) translateY(0); }
}
.diq-hdr {
  background: linear-gradient(135deg,#6D5EFC,#3BA4FF) !important;
  padding:14px 18px !important; display:flex !important;
  align-items:center !important; gap:12px !important; flex-shrink:0 !important;
}
.diq-av {
  width:40px;height:40px;border-radius:50%;
  background:rgba(255,255,255,.22);border:2px solid rgba(255,255,255,.4);
  display:flex;align-items:center;justify-content:center;font-size:18px;color:#fff;flex-shrink:0;
}
.diq-hdr-name { font-size:14px;font-weight:700;color:#fff !important; }
.diq-hdr-sub  { font-size:11px;color:rgba(255,255,255,.75) !important;margin-top:1px; }
.diq-online   { width:9px;height:9px;border-radius:50%;background:#4AE3A0;box-shadow:0 0 8px #4AE3A0;margin-left:auto; }
.diq-x {
  background:rgba(255,255,255,.18);border:none;width:28px;height:28px;border-radius:50%;
  cursor:pointer;color:#fff;font-size:15px;display:flex;align-items:center;justify-content:center;
}
.diq-x:hover { background:rgba(255,255,255,.32); }
#diq-msgs {
  flex:1 !important;overflow-y:auto !important;padding:14px 14px 8px !important;
  background:#f7f8fc !important;display:flex !important;flex-direction:column !important;gap:10px !important;
}
#diq-msgs::-webkit-scrollbar { width:4px; }
#diq-msgs::-webkit-scrollbar-thumb { background:#d1d5db;border-radius:4px; }
.diq-bub { max-width:84%;padding:10px 14px;font-size:13.5px;line-height:1.55;word-break:break-word; }
.diq-bot  { background:#fff;color:#1a1a2e;border-radius:4px 18px 18px 18px;box-shadow:0 1px 5px rgba(0,0,0,.09);align-self:flex-start; }
.diq-user { background:linear-gradient(135deg,#6D5EFC,#3BA4FF);color:#fff;border-radius:18px 18px 4px 18px;align-self:flex-end;box-shadow:0 2px 10px rgba(109,94,252,.35); }
.diq-typing { align-self:flex-start;background:#fff;border-radius:4px 18px 18px 18px;box-shadow:0 1px 5px rgba(0,0,0,.09);padding:12px 16px;display:flex;gap:5px;align-items:center; }
.diq-dot { width:7px;height:7px;border-radius:50%;background:#aaa;animation:diqBlink 1.2s infinite; }
.diq-dot:nth-child(2){animation-delay:.2s}.diq-dot:nth-child(3){animation-delay:.4s}
@keyframes diqBlink { 0%,80%,100%{opacity:.2;transform:scale(.85)} 40%{opacity:1;transform:scale(1)} }
#diq-quick { padding:8px 14px 6px;background:#f7f8fc;display:flex;flex-wrap:wrap;gap:6px;flex-shrink:0; }
.diq-qbtn {
  background:#fff;border:1.5px solid #e0e3ef;border-radius:20px;padding:5px 12px;
  font-size:12px;color:#6D5EFC;font-weight:600;cursor:pointer;white-space:nowrap;
  transition:all .15s;font-family:inherit;
}
.diq-qbtn:hover { background:#6D5EFC;color:#fff;border-color:#6D5EFC; }
.diq-bar {
  padding:10px 12px;background:#fff;border-top:1px solid #eef0f6;
  display:flex !important;gap:8px;align-items:center;flex-shrink:0;
}
#diq-inp {
  flex:1;border:1.5px solid #e0e3ef;border-radius:24px;
  padding:9px 16px;font-size:13.5px;color:#1a1a2e;
  outline:none;transition:border-color .2s;background:#f7f8fc;font-family:inherit;
}
#diq-inp:focus { border-color:#6D5EFC;background:#fff; }
#diq-inp::placeholder { color:#b0b7c7; }
#diq-send {
  width:40px;height:40px;border-radius:50%;
  background:linear-gradient(135deg,#6D5EFC,#3BA4FF);
  border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;
  flex-shrink:0;box-shadow:0 3px 14px rgba(109,94,252,.45);transition:transform .15s;
}
#diq-send:hover { transform:scale(1.1); }
</style>

<!-- FAB — no inline onclick, JS attaches listener -->
<button id="diq-fab">
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none"
       stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
</button>

<!-- Chat panel — no inline onclicks -->
<div id="diq-panel">
  <div class="diq-hdr">
    <div class="diq-av">✦</div>
    <div style="flex:1">
      <div class="diq-hdr-name">DeepAtomicIQ Assistant</div>
      <div class="diq-hdr-sub">Powered by Claude AI · Secure</div>
    </div>
    <div class="diq-online"></div>
    <button class="diq-x">✕</button>
  </div>
  <div id="diq-msgs"></div>
  <div id="diq-quick">
    <button class="diq-qbtn">What is my Sharpe ratio?</button>
    <button class="diq-qbtn">Explain my allocation</button>
    <button class="diq-qbtn">What is volatility?</button>
    <button class="diq-qbtn">How does rebalancing work?</button>
  </div>
  <div class="diq-bar">
    <input id="diq-inp" type="text" placeholder="Write your message..." autocomplete="off">
    <button id="diq-send">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none"
           stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="22" y1="2" x2="11" y2="13"/>
        <polygon points="22 2 15 22 11 13 2 9 22 2"/>
      </svg>
    </button>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── STEP 2: Execute JS via components.html (iframe reaches parent) ────
    components.html(f"""
<script>
(function() {{
  var pd      = window.parent.document;
  var WELCOME = {welcome_js};
  var HISTORY = {messages_json};
  var IS_OPEN = {is_open_js};

  var panel = pd.getElementById('diq-panel');
  var msgs  = pd.getElementById('diq-msgs');
  var inp   = pd.getElementById('diq-inp');
  var quick = pd.getElementById('diq-quick');
  var fab   = pd.getElementById('diq-fab');
  var closeBtn = pd.querySelector('.diq-x');
  var busy  = false;

  if (!panel || !fab) return; // elements not ready yet

  // ── Render message history ──────────────────────────────────────────
  function renderHistory() {{
    msgs.innerHTML = '';
    if (HISTORY.length === 0) {{
      addBubble('assistant', WELCOME, false);
    }} else {{
      HISTORY.forEach(function(m) {{ addBubble(m.role, m.content, false); }});
      quick.style.display = 'none';
    }}
    scrollBottom();
  }}

  function addBubble(role, text, doScroll) {{
    var d = pd.createElement('div');
    d.className = 'diq-bub ' + (role === 'user' ? 'diq-user' : 'diq-bot');
    d.textContent = text;
    msgs.appendChild(d);
    if (doScroll !== false) scrollBottom();
  }}

  function showTyping() {{
    var d = pd.createElement('div');
    d.className = 'diq-typing'; d.id = 'diq-typing';
    d.innerHTML = '<div class="diq-dot"></div><div class="diq-dot"></div><div class="diq-dot"></div>';
    msgs.appendChild(d); scrollBottom();
  }}

  function hideTyping() {{
    var t = pd.getElementById('diq-typing');
    if (t) t.remove();
  }}

  function scrollBottom() {{ msgs.scrollTop = msgs.scrollHeight; }}

  // ── Toggle open/close ───────────────────────────────────────────────
  function toggle() {{
    panel.classList.toggle('diq-open');
    if (panel.classList.contains('diq-open')) inp.focus();
  }}

  fab.addEventListener('click', toggle);
  if (closeBtn) closeBtn.addEventListener('click', toggle);

  // ── Quick reply chips ───────────────────────────────────────────────
  quick.querySelectorAll('.diq-qbtn').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      inp.value = btn.textContent;
      quick.style.display = 'none';
      sendMessage();
    }});
  }});

  // ── Input events ────────────────────────────────────────────────────
  inp.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); sendMessage(); }}
  }});
  pd.getElementById('diq-send').addEventListener('click', sendMessage);

  // ── Send via Streamlit bridge ───────────────────────────────────────
  function sendMessage() {{
    var text = inp.value.trim();
    if (!text || busy) return;
    inp.value = '';
    quick.style.display = 'none';
    busy = true;

    addBubble('user', text);
    showTyping();

    var bridge = pd.querySelector('input[placeholder="diq_bridge_input"]');

    if (bridge) {{
      var nativeSetter = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, 'value').set;
      nativeSetter.call(bridge, text);
      bridge.dispatchEvent(new window.parent.Event('input', {{ bubbles: true }}));
      bridge.dispatchEvent(new window.parent.Event('change', {{ bubbles: true }}));
      setTimeout(function() {{
        bridge.dispatchEvent(new window.parent.KeyboardEvent('keydown', {{
          key: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true
        }}));
        bridge.dispatchEvent(new window.parent.KeyboardEvent('keypress', {{
          key: 'Enter', keyCode: 13, which: 13, bubbles: true
        }}));
        bridge.dispatchEvent(new window.parent.KeyboardEvent('keyup', {{
          key: 'Enter', keyCode: 13, which: 13, bubbles: true
        }}));
      }}, 100);
    }} else {{
      hideTyping();
      addBubble('assistant', 'Bridge not found — please refresh the page.');
      busy = false;
    }}
  }}

  // Open panel if it was open before rerun
  if (IS_OPEN) panel.classList.add('diq-open');

  renderHistory();
}})();
</script>
""", height=0, scrolling=False)

    # ── Hidden Streamlit bridge input ─────────────────────────────────────
    # CSS hides it; JS finds it by id and sets value to trigger rerun
    st.markdown("""
    <style>
    /* Hide the bridge input from view */
    div[data-testid="stTextInput"]:has(input[id*="diq_bridge"]) {
        position: absolute !important;
        opacity: 0 !important;
        pointer-events: none !important;
        height: 0 !important;
        overflow: hidden !important;
    }
    </style>
    """, unsafe_allow_html=True)

    bridge_val = st.text_input(
        "diq_bridge",
        value="",
        key=f"diq_bridge_{st.session_state.cb_key}",
        label_visibility="collapsed",
        placeholder="diq_bridge_input",
    )

    if bridge_val and bridge_val.strip():
        st.session_state.cb_pending = bridge_val.strip()
        st.rerun()