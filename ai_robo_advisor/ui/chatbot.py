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

def render_chatbot():
    """Inject the floating chatbot widget."""
    # =============================================================================
    # FLOATING CHATBOT (Fixed & working)
    # =============================================================================
    
    # Try to load Gemini key if available (not required for UI)
    try:
        GEMINI_KEY = st.secrets.get("gemini_api_key", "")
    except Exception:
        GEMINI_KEY = ""
    
    _SYSTEM_PROMPT = """You are DeepAtomicIQ, an AI investment assistant embedded in the DeepAtomicIQ robo-advisor platform.
    You help users understand their AI-generated portfolio, explain investment concepts clearly, and guide them through the app.
    The platform uses a Markowitz-Informed Neural Network (MINN) that maximises the Sharpe ratio.
    It offers 6 risk profiles and invests across 8 ETFs: VOO (S&P 500), QQQ (Nasdaq 100), VWRA (Global), AGG (Bonds), GLD (Gold), VNQ (Real Estate), ESGU (ESG), PDBC (Commodities).
    Be concise, friendly, and jargon-free. Use bullet points where helpful. Never give regulated financial advice.
    Always remind users to consult a qualified financial adviser for real investment decisions. Keep replies under 120 words unless asked for detail."""
    
    CHATBOT_HTML = """
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{ background: transparent; overflow: hidden; font-family: 'Inter', system-ui, sans-serif; }}
      /* Chat button (fixed to bottom-right) */
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
      /* Chat panel */
      #cb-panel {{
        position: fixed; bottom: 96px; right: 24px; z-index: 99998;
        width: 380px; height: 520px;
        background: rgba(10, 12, 28, 0.98); backdrop-filter: blur(20px);
        border: 1px solid rgba(109,94,252,0.4); border-radius: 24px;
        display: none; flex-direction: column; overflow: hidden;
        box-shadow: 0 20px 50px rgba(0,0,0,0.6);
        font-family: inherit;
      }}
      #cb-panel.open {{ display: flex; }}
      /* Header */
      #cb-hdr {{
        padding: 12px 16px;
        background: rgba(109,94,252,0.15);
        border-bottom: 1px solid rgba(255,255,255,0.08);
        display: flex; align-items: center; gap: 10px;
      }}
      .cb-av {{
        width: 34px; height: 34px; border-radius: 50%;
        background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
        display: flex; align-items: center; justify-content: center;
        font-size: 18px;
      }}
      .cb-name {{ font-weight: 700; color: white; font-size: 14px; }}
      .cb-sub {{ font-size: 10px; color: #8EF6D1; }}
      .cb-x {{
        margin-left: auto; background: none; border: none;
        color: #aaa; font-size: 24px; cursor: pointer;
        line-height: 1; padding: 0 6px;
      }}
      /* Messages area */
      #cb-msgs {{
        flex: 1; overflow-y: auto; padding: 14px;
        display: flex; flex-direction: column; gap: 10px;
        scrollbar-width: thin;
      }}
      .bot, .usr {{
        max-width: 85%; padding: 8px 12px; border-radius: 18px;
        font-size: 13px; line-height: 1.5; word-break: break-word;
      }}
      .bot {{
        background: rgba(109,94,252,0.15); color: #E0E7FF;
        border: 1px solid rgba(109,94,252,0.3);
        align-self: flex-start; border-bottom-left-radius: 4px;
      }}
      .usr {{
        background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
        color: white; align-self: flex-end; border-bottom-right-radius: 4px;
      }}
      .typing {{
        display: flex; gap: 4px; align-items: center;
        background: rgba(109,94,252,0.1); padding: 8px 12px;
        border-radius: 18px; align-self: flex-start;
        border: 1px solid rgba(109,94,252,0.2);
      }}
      .typing span {{
        width: 6px; height: 6px; border-radius: 50%;
        background: #8BA6D3; animation: bounce 1.2s infinite;
      }}
      .typing span:nth-child(2) {{ animation-delay: 0.2s; }}
      .typing span:nth-child(3) {{ animation-delay: 0.4s; }}
      @keyframes bounce {{
        0%,60%,100% {{ transform: translateY(0); }}
        30% {{ transform: translateY(-5px); }}
      }}
      /* Chips (suggestions) */
      .chips {{
        display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;
      }}
      .chip {{
        background: rgba(109,94,252,0.2); border: 1px solid rgba(109,94,252,0.4);
        border-radius: 30px; padding: 3px 10px; font-size: 11px;
        color: #C4D0FF; cursor: pointer; transition: 0.1s;
      }}
      .chip:hover {{ background: rgba(109,94,252,0.4); color: white; }}
      /* Input row */
      #cb-inrow {{
        display: flex; gap: 8px; padding: 12px;
        border-top: 1px solid rgba(255,255,255,0.08);
        background: rgba(0,0,0,0.2);
      }}
      #cb-in {{
        flex: 1; background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.15); border-radius: 30px;
        padding: 8px 14px; color: white; font-size: 13px;
        outline: none; font-family: inherit;
      }}
      #cb-in:focus {{ border-color: #6D5EFC; }}
      #cb-send {{
        background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
        border: none; border-radius: 50%; width: 36px; height: 36px;
        cursor: pointer; color: white; font-size: 16px;
        display: flex; align-items: center; justify-content: center;
      }}
      #cb-send:disabled, #cb-in:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    </style>
    </head>
    <body>
    
    <button id="cb-btn">🤖</button>
    <div id="cb-panel">
      <div id="cb-hdr">
        <div class="cb-av">🧠</div>
        <div><div class="cb-name">DeepAtomicIQ AI</div><div class="cb-sub">Powered by Gemini • Online</div></div>
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
      <div id="cb-inrow">
        <input id="cb-in" type="text" placeholder="Ask me anything...">
        <button id="cb-send">➤</button>
      </div>
    </div>
    
    <script>
      const GEMINI_KEY = "{GEMINI_KEY}";
      const SYSTEM_PROMPT = `{_SYSTEM_PROMPT}`;
      let chatHistory = [];
    
      const panel = document.getElementById('cb-panel');
      const msgs = document.getElementById('cb-msgs');
      const inp = document.getElementById('cb-in');
      const btn = document.getElementById('cb-btn');
      const sendBtn = document.getElementById('cb-send');
      const closeBtn = document.getElementById('cb-close');
    
      function togglePanel() { panel.classList.toggle('open'); if(panel.classList.contains('open')) { inp.focus(); msgs.scrollTop = msgs.scrollHeight; } }
      btn.onclick = togglePanel;
      closeBtn.onclick = togglePanel;
    
      function addMessage(text, isUser) {
        const div = document.createElement('div');
        div.className = isUser ? 'usr' : 'bot';
        div.innerHTML = text.replace(/\\n/g, '<br>').replace(/\\*\\*(.*?)\\*\\*/g, '<b>$1</b>');
        msgs.appendChild(div);
        msgs.scrollTop = msgs.scrollHeight;
      }
    
      function showTyping() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing';
        typingDiv.id = 'cb-typing';
        typingDiv.innerHTML = '<span></span><span></span><span></span>';
        msgs.appendChild(typingDiv);
        msgs.scrollTop = msgs.scrollHeight;
      }
      function removeTyping() {
        const el = document.getElementById('cb-typing');
        if (el) el.remove();
      }
    
      async function callGemini(userMsg) {
        if (!GEMINI_KEY) {
          return f"{get_svg('warning', 16, ACCENT)} **Offline mode** – Add your Gemini API key to `secrets.toml` to enable full AI. For now, ask me about portfolio basics, risk profiles, or ETF allocation.";
        }
        chatHistory.push({ role: "user", parts: [{ text: userMsg }] });
        try {
          const res = await fetch(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_KEY}`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                system_instruction: { parts: [{ text: SYSTEM_PROMPT }] },
                contents: chatHistory,
                generationConfig: { maxOutputTokens: 350, temperature: 0.7 }
              })
            }
          );
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          const reply = data.candidates[0].content.parts[0].text;
          chatHistory.push({ role: "model", parts: [{ text: reply }] });
          return reply;
        } catch (err) {
          chatHistory.pop();
          return `❌ Could not reach AI: ${err.message}. Please check your API key or internet connection.`;
        }
      }
    
      async function sendMessage() {
        const q = inp.value.trim();
        if (!q || inp.disabled) return;
        addMessage(q, true);
        inp.value = '';
        inp.disabled = true;
        sendBtn.disabled = true;
        showTyping();
        const reply = await callGemini(q);
        removeTyping();
        addMessage(reply, false);
        inp.disabled = false;
        sendBtn.disabled = false;
        inp.focus();
      }
    
      sendBtn.onclick = sendMessage;
      inp.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
    
      // Pre‑defined chip questions
      document.querySelectorAll('.chip').forEach(chip => {
        chip.onclick = () => { inp.value = chip.textContent; sendMessage(); };
      });
    </script>
    </body>
    </html>
    """.replace("{GEMINI_KEY}", GEMINI_KEY).replace("{_SYSTEM_PROMPT}", _SYSTEM_PROMPT)
    
    # CSS in the parent page to reposition the iframe container as fixed bottom-right
    st.markdown("""
    <style>
    /* Target the chatbot wrapper precisely using the sibling anchor trick */
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
    
    # Invisible anchor to precisely target the chatbot container in CSS
    st.markdown("<div id='cb-anchor'></div>", unsafe_allow_html=True)
    components.html(CHATBOT_HTML, height=0, scrolling=False)
