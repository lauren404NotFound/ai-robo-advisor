"""
ui/chatbot.py
=============
Floating Claude AI chatbot widget — investment-aware assistant.
Call render_chatbot() at the bottom of app.py after main_router().
"""
from __future__ import annotations
import streamlit as st


def _get_system_prompt() -> str:
    """Build a context-aware system prompt from the user's current portfolio."""
    base = """You are DeepAtomicIQ Assistant, an expert AI investment adviser for LEM StratIQ. 
You help users understand their portfolio, investment concepts, and financial planning.
You are warm, professional, and speak plain English. UK English spelling.
Never say "as an AI" or "I cannot provide financial advice" — you ARE the adviser.
Keep responses concise — 2-4 sentences unless more detail is needed.
Never use emojis."""

    # Enrich with user's portfolio context if available
    result = st.session_state.get("result")
    if result:
        port  = result.get("portfolio", {})
        stats = port.get("stats", {})
        alloc = port.get("allocation_pct", {})
        cat   = port.get("risk_category", "Balanced")
        score = result.get("score", 5)
        base += f"""

Current user portfolio context:
- Risk profile: {cat} (score: {score:.1f}/10)
- Expected annual return: {stats.get('expected_annual_return', 0):.1f}%
- Expected volatility: {stats.get('expected_volatility', 0):.1f}%
- Sharpe ratio: {stats.get('sharpe_ratio', 0):.2f}
- Asset allocation: {alloc}

Use this context to give personalised answers about their specific portfolio."""

    return base


def _call_claude(messages: list) -> str:
    """Call Claude API and return response text."""
    try:
        import anthropic
        api_key = (
            st.secrets.get("anthropic_api_key")
            or st.secrets.get("ANTHROPIC_API_KEY")
            or st.secrets.get("anthropic", {}).get("api_key")
        )
        if not api_key:
            return "I'm unable to connect right now — the API key is not configured."

        client  = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            system=_get_system_prompt(),
            messages=messages,
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Connection error — please try again. ({type(e).__name__})"


def render_chatbot():
    """Render the floating chatbot widget."""

    # ── Session state init ────────────────────────────────────────────────────
    if "chatbot_open" not in st.session_state:
        st.session_state.chatbot_open = False
    if "chatbot_messages" not in st.session_state:
        st.session_state.chatbot_messages = []
    if "chatbot_input_key" not in st.session_state:
        st.session_state.chatbot_input_key = 0

    # ── Toggle button (fixed bottom-right) ───────────────────────────────────
    st.markdown("""
    <style>
    #chatbot-fab-marker + div {
        position: fixed !important;
        bottom: 28px !important;
        right: 28px !important;
        z-index: 10000 !important;
        width: auto !important;
    }
    #chatbot-fab-marker + div button {
        width: 56px !important;
        height: 56px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #6D5EFC, #3BA4FF) !important;
        border: none !important;
        box-shadow: 0 8px 32px rgba(109,94,252,0.5) !important;
        font-size: 22px !important;
        padding: 0 !important;
        color: white !important;
        transition: all 0.3s ease !important;
    }
    #chatbot-fab-marker + div button:hover {
        transform: scale(1.1) !important;
        box-shadow: 0 12px 40px rgba(109,94,252,0.7) !important;
    }
    </style>
    <div id="chatbot-fab-marker"></div>
    """, unsafe_allow_html=True)

    fab_label = "✕" if st.session_state.chatbot_open else "💬"
    if st.button(fab_label, key="chatbot_fab"):
        st.session_state.chatbot_open = not st.session_state.chatbot_open
        st.rerun()

    if not st.session_state.chatbot_open:
        return

    # ── Chat panel (fixed bottom-right above FAB) ─────────────────────────────
    st.markdown("""
    <style>
    #chatbot-panel-marker + div[data-testid="stVerticalBlock"] {
        position: fixed !important;
        bottom: 96px !important;
        right: 28px !important;
        width: 380px !important;
        max-height: 520px !important;
        z-index: 9999 !important;
        background: rgba(8, 10, 26, 0.98) !important;
        border: 1px solid rgba(109,94,252,0.4) !important;
        border-radius: 20px !important;
        padding: 0 !important;
        box-shadow: 0 24px 80px rgba(0,0,0,0.7), 0 0 0 1px rgba(109,94,252,0.2) !important;
        backdrop-filter: blur(24px) !important;
        overflow: hidden !important;
        display: flex !important;
        flex-direction: column !important;
    }
    </style>
    <div id="chatbot-panel-marker"></div>
    """, unsafe_allow_html=True)

    with st.container():
        # Header
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, rgba(109,94,252,0.3), rgba(59,164,255,0.15));
            padding: 16px 20px;
            border-bottom: 1px solid rgba(109,94,252,0.2);
            display: flex; align-items: center; gap: 12px;
        ">
            <div style="
                width: 36px; height: 36px; border-radius: 10px;
                background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
                display: flex; align-items: center; justify-content: center;
                font-size: 18px; flex-shrink: 0;
            ">✦</div>
            <div>
                <div style="font-size: 14px; font-weight: 800; color: #fff;">DeepAtomicIQ Assistant</div>
                <div style="font-size: 11px; color: rgba(255,255,255,0.45);">Powered by Claude AI · Always available</div>
            </div>
            <div style="margin-left:auto; width:8px; height:8px; border-radius:50%; background:#4AE3A0; box-shadow: 0 0 8px #4AE3A0;"></div>
        </div>
        """, unsafe_allow_html=True)

        # Messages area
        messages = st.session_state.chatbot_messages

        if not messages:
            # Welcome message
            name = st.session_state.get("user_name", "").split()[0] if st.session_state.get("user_name") else ""
            greeting = f"Hi {name}! " if name else "Hi! "
            has_portfolio = bool(st.session_state.get("result"))
            if has_portfolio:
                welcome = f"{greeting}I can see your portfolio is set up. Ask me anything about your investments, risk profile, or financial planning."
            else:
                welcome = f"{greeting}I'm your AI investment assistant. Ask me anything about investing, portfolio strategy, or how LEM StratIQ works."

            st.markdown(f"""
            <div style="padding: 16px 20px;">
                <div style="
                    background: rgba(109,94,252,0.08);
                    border: 1px solid rgba(109,94,252,0.15);
                    border-radius: 14px 14px 14px 4px;
                    padding: 12px 16px;
                    font-size: 13px; color: #C5D3EC; line-height: 1.6;
                    margin-bottom: 12px;
                ">{welcome}</div>
                <div style="display:flex; flex-wrap:wrap; gap:6px;">
                    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:20px;padding:5px 12px;font-size:11px;color:#8BA6D3;cursor:pointer;">What is my Sharpe ratio?</div>
                    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:20px;padding:5px 12px;font-size:11px;color:#8BA6D3;cursor:pointer;">Explain my allocation</div>
                    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:20px;padding:5px 12px;font-size:11px;color:#8BA6D3;cursor:pointer;">What is a Sharpe ratio?</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Render message history
            msgs_html = '<div style="padding: 12px 20px; max-height: 300px; overflow-y: auto;">'
            for msg in messages[-20:]:  # last 20 messages
                if msg["role"] == "user":
                    msgs_html += f"""
                    <div style="display:flex;justify-content:flex-end;margin-bottom:10px;">
                        <div style="
                            background: linear-gradient(135deg, rgba(109,94,252,0.4), rgba(59,164,255,0.2));
                            border: 1px solid rgba(109,94,252,0.3);
                            border-radius: 14px 14px 4px 14px;
                            padding: 10px 14px; max-width: 80%;
                            font-size: 13px; color: #fff; line-height: 1.5;
                        ">{msg['content']}</div>
                    </div>"""
                else:
                    msgs_html += f"""
                    <div style="display:flex;justify-content:flex-start;margin-bottom:10px;">
                        <div style="
                            background: rgba(255,255,255,0.04);
                            border: 1px solid rgba(255,255,255,0.08);
                            border-radius: 14px 14px 14px 4px;
                            padding: 10px 14px; max-width: 85%;
                            font-size: 13px; color: #C5D3EC; line-height: 1.6;
                        ">{msg['content']}</div>
                    </div>"""
            msgs_html += '</div>'
            st.markdown(msgs_html, unsafe_allow_html=True)

        # Input area
        st.markdown('<div style="padding: 12px 16px; border-top: 1px solid rgba(255,255,255,0.06);">', unsafe_allow_html=True)

        col_input, col_send = st.columns([5, 1])
        with col_input:
            user_input = st.text_input(
                "",
                placeholder="Ask anything about your portfolio...",
                key=f"chatbot_input_{st.session_state.chatbot_input_key}",
                label_visibility="collapsed",
            )
        with col_send:
            send = st.button("→", key="chatbot_send", use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Process message
        if (send or user_input) and user_input and user_input.strip():
            user_msg = user_input.strip()
            st.session_state.chatbot_messages.append({"role": "user", "content": user_msg})

            # Build messages for Claude (last 10 for context)
            claude_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.chatbot_messages[-10:]
            ]

            with st.spinner(""):
                reply = _call_claude(claude_messages)

            st.session_state.chatbot_messages.append({"role": "assistant", "content": reply})
            st.session_state.chatbot_input_key += 1
            st.rerun()

        # Clear button
        if messages:
            if st.button("Clear conversation", key="chatbot_clear"):
                st.session_state.chatbot_messages = []
                st.session_state.chatbot_input_key += 1
                st.rerun()