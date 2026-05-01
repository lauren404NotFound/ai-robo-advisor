"""
ui/chatbot.py
=============
Floating Claude AI chatbot — injected into the parent Streamlit window via JS.
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

    welcome = (
        f"Hi{' ' + name if name else ''}! I can see your portfolio is set up. Ask me anything about your investments or financial planning."
        if has_portfolio else
        f"Hi{' ' + name if name else ''}! I'm your AI investment assistant. Ask me anything about investing or how LEM StratIQ works."
    )

    system_prompt = (
        "You are DeepAtomicIQ Assistant, an expert AI investment adviser for LEM StratIQ. "
        "Help users understand their portfolio, investment concepts, and financial planning. "
        "Be warm, professional, plain English, UK spelling. "
        "Keep responses to 2-4 sentences unless more detail is needed. "
        "Never say 'as an AI'. Never use emojis."
        + (f" User portfolio: {portfolio_ctx}" if portfolio_ctx else "")
    )

    # Escape for safe JS embedding
    import json
    api_key_js      = json.dumps(api_key)
    welcome_js      = json.dumps(welcome)
    system_js       = json.dumps(system_prompt)

    components.html(f"""
<script>
(function() {{
  var pd = window.parent.document;

  // Only inject once
  if (pd.getElementById('diq-chatbot-fab')) return;

  // ── Styles ──────────────────────────────────────────────────────────────
  var style = pd.createElement('style');
  style.textContent = `
    #diq-chatbot-fab {{
      position: fixed; bottom: 24px; right: 24px;
      width: 58px; height: 58px; border-radius: 50%;
      background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
      box-shadow: 0 6px 28px rgba(109,94,252,0.55);
      border: none; cursor: pointer; z-index: 999999;
      display: flex; align-items: center; justify-content: center;
      transition: transform .2s, box-shadow .2s;
    }}
    #diq-chatbot-fab:hover {{
      transform: scale(1.1);
      box-shadow: 0 10px 36px rgba(109,94,252,0.75);
    }}
    #diq-chatbot-panel {{
      position: fixed; bottom: 94px; right: 24px;
      width: 360px; height: 510px;
      background: #fff; border-radius: 20px;
      box-shadow: 0 16px 64px rgba(0,0,0,0.2);
      display: none; flex-direction: column;
      overflow: hidden; z-index: 999998;
      font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
      animation: diqPop .25s cubic-bezier(.34,1.56,.64,1);
    }}
    #diq-chatbot-panel.diq-open {{ display: flex; }}
    @keyframes diqPop {{
      from {{ opacity:0; transform: scale(.9) translateY(16px); }}
      to   {{ opacity:1; transform: scale(1)  translateY(0); }}
    }}
    .diq-hdr {{
      background: linear-gradient(135deg,#6D5EFC,#3BA4FF);
      padding: 14px 18px; display: flex; align-items: center; gap: 12px;
      flex-shrink: 0;
    }}
    .diq-av {{
      width:40px;height:40px;border-radius:50%;
      background:rgba(255,255,255,.22);border:2px solid rgba(255,255,255,.4);
      display:flex;align-items:center;justify-content:center;
      font-size:18px;color:#fff;flex-shrink:0;
    }}
    .diq-hdr-name {{ font-size:14px;font-weight:700;color:#fff; }}
    .diq-hdr-sub  {{ font-size:11px;color:rgba(255,255,255,.75);margin-top:1px; }}
    .diq-dot {{
      width:9px;height:9px;border-radius:50%;
      background:#4AE3A0;box-shadow:0 0 8px #4AE3A0;margin-left:auto;
    }}
    .diq-x {{
      background:rgba(255,255,255,.18);border:none;
      width:28px;height:28px;border-radius:50%;
      cursor:pointer;color:#fff;font-size:15px;
      display:flex;align-items:center;justify-content:center;
    }}
    .diq-x:hover {{ background:rgba(255,255,255,.32); }}
    #diq-msgs {{
      flex:1;overflow-y:auto;padding:14px 14px 8px;
      background:#f7f8fc;display:flex;flex-direction:column;gap:10px;
    }}
    #diq-msgs::-webkit-scrollbar {{ width:4px; }}
    #diq-msgs::-webkit-scrollbar-thumb {{ background:#d1d5db;border-radius:4px; }}
    .diq-bub {{
      max-width:84%;padding:10px 14px;
      font-size:13.5px;line-height:1.55;word-break:break-word;border-radius:18px;
    }}
    .diq-bot {{
      background:#fff;color:#1a1a2e;
      border-radius:4px 18px 18px 18px;
      box-shadow:0 1px 5px rgba(0,0,0,.09);
      align-self:flex-start;
    }}
    .diq-user {{
      background:linear-gradient(135deg,#6D5EFC,#3BA4FF);
      color:#fff;border-radius:18px 18px 4px 18px;
      align-self:flex-end;
      box-shadow:0 2px 10px rgba(109,94,252,.35);
    }}
    .diq-typing {{
      align-self:flex-start;background:#fff;
      border-radius:4px 18px 18px 18px;
      box-shadow:0 1px 5px rgba(0,0,0,.09);
      padding:12px 16px;display:flex;gap:5px;align-items:center;
    }}
    .diq-dot-t {{
      width:7px;height:7px;border-radius:50%;background:#aaa;
      animation:diqBlink 1.2s infinite;
    }}
    .diq-dot-t:nth-child(2){{animation-delay:.2s}}
    .diq-dot-t:nth-child(3){{animation-delay:.4s}}
    @keyframes diqBlink {{
      0%,80%,100%{{opacity:.2;transform:scale(.85)}}
      40%{{opacity:1;transform:scale(1)}}
    }}
    #diq-quick {{
      padding:8px 14px 6px;background:#f7f8fc;
      display:flex;flex-wrap:wrap;gap:6px;flex-shrink:0;
    }}
    .diq-qbtn {{
      background:#fff;border:1.5px solid #e0e3ef;
      border-radius:20px;padding:5px 12px;
      font-size:12px;color:#6D5EFC;font-weight:600;
      cursor:pointer;white-space:nowrap;
      transition:all .15s;font-family:inherit;
    }}
    .diq-qbtn:hover {{ background:#6D5EFC;color:#fff;border-color:#6D5EFC; }}
    .diq-bar {{
      padding:10px 12px;background:#fff;
      border-top:1px solid #eef0f6;
      display:flex;gap:8px;align-items:center;flex-shrink:0;
    }}
    #diq-inp {{
      flex:1;border:1.5px solid #e0e3ef;border-radius:24px;
      padding:9px 16px;font-size:13.5px;color:#1a1a2e;
      outline:none;transition:border-color .2s;background:#f7f8fc;
      font-family:inherit;
    }}
    #diq-inp:focus {{ border-color:#6D5EFC;background:#fff; }}
    #diq-inp::placeholder {{ color:#b0b7c7; }}
    #diq-send {{
      width:40px;height:40px;border-radius:50%;
      background:linear-gradient(135deg,#6D5EFC,#3BA4FF);
      border:none;cursor:pointer;color:#fff;
      display:flex;align-items:center;justify-content:center;
      flex-shrink:0;box-shadow:0 3px 14px rgba(109,94,252,.45);
      transition:transform .15s,box-shadow .15s;
    }}
    #diq-send:hover{{ transform:scale(1.1);box-shadow:0 5px 18px rgba(109,94,252,.6); }}
    .diq-err {{ color:#ef4444;font-size:12px;padding:4px 14px;align-self:flex-start; }}
  `;
  pd.head.appendChild(style);

  // ── FAB ─────────────────────────────────────────────────────────────────
  var fab = pd.createElement('button');
  fab.id = 'diq-chatbot-fab';
  fab.title = 'Chat with DeepAtomicIQ';
  fab.innerHTML = `<svg width="26" height="26" viewBox="0 0 24 24" fill="none"
    stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>`;
  pd.body.appendChild(fab);

  // ── Panel ────────────────────────────────────────────────────────────────
  var panel = pd.createElement('div');
  panel.id = 'diq-chatbot-panel';
  panel.innerHTML = `
    <div class="diq-hdr">
      <div class="diq-av">✦</div>
      <div style="flex:1">
        <div class="diq-hdr-name">DeepAtomicIQ Assistant</div>
        <div class="diq-hdr-sub">Powered by Claude AI</div>
      </div>
      <div class="diq-dot"></div>
      <button class="diq-x" id="diq-close">✕</button>
    </div>
    <div id="diq-msgs">
      <div class="diq-bub diq-bot">${{welcome}}</div>
    </div>
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
  `;
  pd.body.appendChild(panel);

  // ── Logic ────────────────────────────────────────────────────────────────
  var API_KEY    = {api_key_js};
  var SYS_PROMPT = {system_js};
  var welcome    = {welcome_js};
  var history    = [];
  var thinking   = false;
  var msgs       = pd.getElementById('diq-msgs');
  var inp        = pd.getElementById('diq-inp');
  var quick      = pd.getElementById('diq-quick');

  function toggle() {{
    panel.classList.toggle('diq-open');
    if (panel.classList.contains('diq-open')) inp.focus();
  }}
  fab.addEventListener('click', toggle);
  pd.getElementById('diq-close').addEventListener('click', toggle);

  function scrollBottom() {{ msgs.scrollTop = msgs.scrollHeight; }}

  function addBubble(role, text) {{
    var d = pd.createElement('div');
    d.className = 'diq-bub ' + (role === 'user' ? 'diq-user' : 'diq-bot');
    d.textContent = text;
    msgs.appendChild(d);
    scrollBottom();
  }}

  function showTyping() {{
    var d = pd.createElement('div');
    d.className = 'diq-typing'; d.id = 'diq-typing';
    d.innerHTML = '<div class="diq-dot-t"></div><div class="diq-dot-t"></div><div class="diq-dot-t"></div>';
    msgs.appendChild(d); scrollBottom(); return d;
  }}

  function hideQuick() {{
    if (quick) quick.style.display = 'none';
  }}

  quick.querySelectorAll('.diq-qbtn').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      inp.value = btn.textContent;
      hideQuick();
      send();
    }});
  }});

  inp.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); send(); }}
  }});
  pd.getElementById('diq-send').addEventListener('click', send);

  async function send() {{
    var text = inp.value.trim();
    if (!text || thinking) return;
    inp.value = '';
    hideQuick();
    thinking = true;

    addBubble('user', text);
    history.push({{ role: 'user', content: text }});
    var typer = showTyping();

    try {{
      var res = await fetch('https://api.anthropic.com/v1/messages', {{
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

      var data  = await res.json();
      if (!res.ok) throw new Error(data.error?.message || 'HTTP ' + res.status);
      var reply = (data.content && data.content[0] && data.content[0].text) || 'No response.';
      history.push({{ role: 'assistant', content: reply }});
      typer.remove();
      addBubble('assistant', reply);
    }} catch(e) {{
      typer.remove();
      var err = pd.createElement('div');
      err.className = 'diq-err';
      err.textContent = 'Error: ' + e.message;
      msgs.appendChild(err); scrollBottom();
      history.pop();
    }} finally {{
      thinking = false;
      inp.focus();
    }}
  }}
}})();
</script>
""", height=0, scrolling=False)