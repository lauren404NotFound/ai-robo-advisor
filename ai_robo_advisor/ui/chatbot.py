"""
ui/chatbot.py
=============
Floating Claude AI chatbot — pure HTML/JS widget injected via components.html.
The entire chat UI lives inside an iframe so positioning is guaranteed.
Call render_chatbot() at the bottom of app.py after main_router().
"""
from __future__ import annotations
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
        f"Expected return: {stats.get('expected_annual_return',0):.1f}%, "
        f"Volatility: {stats.get('expected_volatility',0):.1f}%, "
        f"Sharpe: {stats.get('sharpe_ratio',0):.2f}, "
        f"Allocation: {alloc}"
    )


def render_chatbot():
    """Render a self-contained floating chatbot widget."""

    # Get API key and context to pass into the widget
    api_key = (
        st.secrets.get("anthropic_api_key")
        or st.secrets.get("ANTHROPIC_API_KEY")
        or st.secrets.get("anthropic", {}).get("api_key")
        or ""
    )

    name = ""
    if st.session_state.get("user_name"):
        name = st.session_state.user_name.strip().split()[0]

    portfolio_ctx = _get_portfolio_context()
    has_portfolio = bool(portfolio_ctx)

    if has_portfolio:
        welcome = f"Hi{' ' + name if name else ''}! I can see your portfolio is set up. Ask me anything about your investments or financial planning."
    else:
        welcome = f"Hi{' ' + name if name else ''}! I'm your AI investment assistant. Ask me anything about investing or how LEM StratIQ works."

    system_prompt = f"""You are DeepAtomicIQ Assistant, an expert AI investment adviser for LEM StratIQ.
You help users understand their portfolio, investment concepts, and financial planning.
Be warm, professional, and use plain English. UK English spelling.
Keep responses concise — 2-4 sentences unless more detail is needed.
Never say "as an AI". Never use emojis.
{f"User's portfolio context: {portfolio_ctx}" if portfolio_ctx else ""}"""

    components.html(f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
    background: transparent;
    overflow: hidden;
  }}

  /* ── FAB ── */
  #fab {{
    position: fixed;
    bottom: 24px; right: 24px;
    width: 58px; height: 58px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6D5EFC 0%, #3BA4FF 100%);
    box-shadow: 0 6px 28px rgba(109,94,252,0.55);
    border: none; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    z-index: 9999;
  }}
  #fab:hover {{
    transform: scale(1.1);
    box-shadow: 0 10px 36px rgba(109,94,252,0.75);
  }}

  /* ── Chat Panel ── */
  #panel {{
    position: fixed;
    bottom: 94px; right: 24px;
    width: 360px;
    height: 500px;
    background: #ffffff;
    border-radius: 20px;
    box-shadow: 0 16px 64px rgba(0,0,0,0.2), 0 2px 8px rgba(0,0,0,0.08);
    display: none;
    flex-direction: column;
    overflow: hidden;
    z-index: 9998;
    animation: popIn 0.25s cubic-bezier(0.34,1.56,0.64,1);
  }}
  #panel.open {{ display: flex; }}

  @keyframes popIn {{
    from {{ opacity: 0; transform: scale(0.9) translateY(16px); }}
    to   {{ opacity: 1; transform: scale(1) translateY(0); }}
  }}

  /* Header */
  .cb-hdr {{
    background: linear-gradient(135deg, #6D5EFC 0%, #3BA4FF 100%);
    padding: 14px 18px;
    display: flex; align-items: center; gap: 12px;
    flex-shrink: 0;
  }}
  .cb-av {{
    width: 40px; height: 40px; border-radius: 50%;
    background: rgba(255,255,255,0.22);
    border: 2px solid rgba(255,255,255,0.4);
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; color: #fff; flex-shrink: 0;
  }}
  .cb-hdr-text {{ flex: 1; }}
  .cb-hdr-name {{ font-size: 14px; font-weight: 700; color: #fff; }}
  .cb-hdr-sub  {{ font-size: 11px; color: rgba(255,255,255,0.75); margin-top: 1px; }}
  .cb-dot {{
    width: 9px; height: 9px; border-radius: 50%;
    background: #4AE3A0; box-shadow: 0 0 8px #4AE3A0;
  }}
  .cb-x {{
    background: rgba(255,255,255,0.18); border: none;
    width: 28px; height: 28px; border-radius: 50%;
    cursor: pointer; color: #fff; font-size: 15px;
    display: flex; align-items: center; justify-content: center;
  }}
  .cb-x:hover {{ background: rgba(255,255,255,0.32); }}

  /* Messages */
  #msgs {{
    flex: 1; overflow-y: auto; padding: 14px 14px 8px;
    background: #f7f8fc;
    display: flex; flex-direction: column; gap: 10px;
  }}
  #msgs::-webkit-scrollbar {{ width: 4px; }}
  #msgs::-webkit-scrollbar-thumb {{ background: #d1d5db; border-radius: 4px; }}

  .bub {{
    max-width: 84%; padding: 10px 14px;
    font-size: 13.5px; line-height: 1.55; word-break: break-word;
  }}
  .bub-bot {{
    background: #fff; color: #1a1a2e;
    border-radius: 4px 18px 18px 18px;
    box-shadow: 0 1px 5px rgba(0,0,0,0.09);
    align-self: flex-start;
  }}
  .bub-user {{
    background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
    color: #fff;
    border-radius: 18px 18px 4px 18px;
    align-self: flex-end;
    box-shadow: 0 2px 10px rgba(109,94,252,0.35);
  }}
  .typing {{
    align-self: flex-start;
    background: #fff; border-radius: 4px 18px 18px 18px;
    box-shadow: 0 1px 5px rgba(0,0,0,0.09);
    padding: 12px 16px; display: flex; gap: 5px; align-items: center;
  }}
  .dot {{
    width: 7px; height: 7px; border-radius: 50%; background: #aaa;
    animation: blink 1.2s infinite;
  }}
  .dot:nth-child(2) {{ animation-delay: 0.2s; }}
  .dot:nth-child(3) {{ animation-delay: 0.4s; }}
  @keyframes blink {{
    0%,80%,100% {{ opacity: 0.2; transform: scale(0.85); }}
    40%          {{ opacity: 1;   transform: scale(1); }}
  }}

  /* Quick replies */
  #quick {{
    padding: 8px 14px 6px;
    background: #f7f8fc;
    display: flex; flex-wrap: wrap; gap: 6px;
  }}
  .qbtn {{
    background: #fff; border: 1.5px solid #e0e3ef;
    border-radius: 20px; padding: 5px 12px;
    font-size: 12px; color: #6D5EFC; font-weight: 600;
    cursor: pointer; white-space: nowrap;
    transition: all 0.15s;
  }}
  .qbtn:hover {{ background: #6D5EFC; color: #fff; border-color: #6D5EFC; }}

  /* Input bar */
  .cb-bar {{
    padding: 10px 12px;
    background: #fff;
    border-top: 1px solid #eef0f6;
    display: flex; gap: 8px; align-items: center;
    flex-shrink: 0;
  }}
  #inp {{
    flex: 1; border: 1.5px solid #e0e3ef; border-radius: 24px;
    padding: 9px 16px; font-size: 13.5px; color: #1a1a2e;
    outline: none; transition: border-color 0.2s; background: #f7f8fc;
    font-family: inherit;
  }}
  #inp:focus {{ border-color: #6D5EFC; background: #fff; }}
  #inp::placeholder {{ color: #b0b7c7; }}
  #send {{
    width: 40px; height: 40px; border-radius: 50%;
    background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
    border: none; cursor: pointer; color: #fff;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; box-shadow: 0 3px 14px rgba(109,94,252,0.45);
    transition: transform 0.15s, box-shadow 0.15s;
  }}
  #send:hover {{ transform: scale(1.1); box-shadow: 0 5px 18px rgba(109,94,252,0.6); }}

  /* Error */
  .err {{ color: #ef4444; font-size: 12px; padding: 4px 14px; }}
</style>
</head>
<body>

<!-- FAB -->
<button id="fab" onclick="toggle()" title="Chat with DeepAtomicIQ">
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none"
       stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
</button>

<!-- Panel -->
<div id="panel">

  <!-- Header -->
  <div class="cb-hdr">
    <div class="cb-av">✦</div>
    <div class="cb-hdr-text">
      <div class="cb-hdr-name">DeepAtomicIQ Assistant</div>
      <div class="cb-hdr-sub">Powered by Claude AI</div>
    </div>
    <div class="cb-dot"></div>
    <button class="cb-x" onclick="toggle()">✕</button>
  </div>

  <!-- Messages -->
  <div id="msgs">
    <div class="bub bub-bot">{welcome}</div>
  </div>

  <!-- Quick replies -->
  <div id="quick">
    <button class="qbtn" onclick="sendQuick(this)">What is my Sharpe ratio?</button>
    <button class="qbtn" onclick="sendQuick(this)">Explain my allocation</button>
    <button class="qbtn" onclick="sendQuick(this)">What is volatility?</button>
    <button class="qbtn" onclick="sendQuick(this)">How does rebalancing work?</button>
  </div>

  <!-- Input -->
  <div class="cb-bar">
    <input id="inp" type="text" placeholder="Write your message..."
           onkeydown="if(event.key==='Enter' && !event.shiftKey){{ event.preventDefault(); send(); }}">
    <button id="send" onclick="send()">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none"
           stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="22" y1="2" x2="11" y2="13"/>
        <polygon points="22 2 15 22 11 13 2 9 22 2"/>
      </svg>
    </button>
  </div>

</div>

<script>
const API_KEY     = {repr(api_key)};
const SYS_PROMPT  = {repr(system_prompt)};
const msgs        = document.getElementById('msgs');
const inp         = document.getElementById('inp');
const quickDiv    = document.getElementById('quick');
const panel       = document.getElementById('panel');
let history       = [];
let thinking      = false;

function toggle() {{
  panel.classList.toggle('open');
  if (panel.classList.contains('open')) inp.focus();
}}

function scrollBottom() {{
  msgs.scrollTop = msgs.scrollHeight;
}}

function addBubble(role, text) {{
  const d = document.createElement('div');
  d.className = 'bub ' + (role === 'user' ? 'bub-user' : 'bub-bot');
  d.textContent = text;
  msgs.appendChild(d);
  scrollBottom();
  return d;
}}

function showTyping() {{
  const d = document.createElement('div');
  d.className = 'typing'; d.id = 'typing';
  d.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
  msgs.appendChild(d); scrollBottom(); return d;
}}

function hideQuick() {{
  if (quickDiv) quickDiv.style.display = 'none';
}}

function sendQuick(btn) {{
  inp.value = btn.textContent;
  hideQuick();
  send();
}}

async function send() {{
  const text = inp.value.trim();
  if (!text || thinking) return;
  inp.value = '';
  hideQuick();
  thinking = true;

  addBubble('user', text);
  history.push({{ role: 'user', content: text }});

  const typer = showTyping();

  try {{
    const res = await fetch('https://api.anthropic.com/v1/messages', {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        'x-api-key': API_KEY,
        'anthropic-version': '2023-06-01',
      }},
      body: JSON.stringify({{
        model: 'claude-sonnet-4-20250514',
        max_tokens: 400,
        system: SYS_PROMPT,
        messages: history.slice(-12),
      }}),
    }});

    if (!res.ok) {{
      const err = await res.json().catch(() => ({{}}));
      throw new Error(err.error?.message || `HTTP ${{res.status}}`);
    }}

    const data  = await res.json();
    const reply = data.content?.[0]?.text?.trim() || 'No response received.';
    history.push({{ role: 'assistant', content: reply }});
    typer.remove();
    addBubble('assistant', reply);
  }} catch(e) {{
    typer.remove();
    const errDiv = document.createElement('div');
    errDiv.className = 'err';
    errDiv.textContent = 'Error: ' + e.message;
    msgs.appendChild(errDiv);
    scrollBottom();
    // Remove from history so user can retry
    history.pop();
  }} finally {{
    thinking = false;
    inp.focus();
  }}
}}
</script>
</body>
</html>
""", height=620, scrolling=False)