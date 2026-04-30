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
    if "cb_open" not in st.session_state: 
        st.session_state.cb_open = False
    if "cb_messages" not in st.session_state:
        name = st.session_state.get("user_name", "").strip().split()[0] if st.session_state.get("user_name") else ""
        has_portfolio = bool(st.session_state.get("result"))
        if has_portfolio:
            welcome = f"Hi{' ' + name if name else ''}! I can see your portfolio is set up. Ask me anything about your investments or financial planning."
        else:
            welcome = f"Hi{' ' + name if name else ''}! I'm your AI investment assistant. Ask me anything about investing or how LEM StratIQ works."
        st.session_state.cb_messages = [{"role": "assistant", "content": welcome}]

    def toggle_cb():
        st.session_state.cb_open = not st.session_state.cb_open

    # ── Global CSS for internal panel styling ───────────────
    st.markdown("""
    <style>
    /* We only style the internal panel here. The actual positioning is handled by JS to be 100% robust. */
    #cb-panel-marker { display: none; }
    
    .cb-native-header {
        background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
        padding: 18px 20px;
        color: white;
        display: flex;
        align-items: center;
        gap: 14px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        border-radius: 20px 20px 0 0;
    }
    .cb-native-avatar {
        width: 42px; height: 42px; border-radius: 50%;
        background: rgba(255,255,255,0.25);
        display: flex; align-items: center; justify-content: center;
        font-size: 22px;
        border: 1px solid rgba(255,255,255,0.4);
    }
    .cb-native-title { font-weight: 800; font-size: 15px; }
    .cb-native-sub { font-size: 11px; opacity: 0.85; margin-top: 2px; }
    </style>
    """, unsafe_allow_html=True)

    # ── JavaScript to reliably float the container ────────────────────────
    import streamlit.components.v1 as components
    components.html("""
    <script>
    const parentDoc = window.parent.document;
    
    // Find the marker we injected
    const wrapperMarker = parentDoc.getElementById('cb-wrapper');
    if (wrapperMarker) {
        // Find the closest Streamlit vertical block container
        const container = wrapperMarker.closest('div[data-testid="stVerticalBlock"]');
        if (container) {
            // Apply floating styles to the main container
            container.style.position = 'fixed';
            container.style.bottom = '24px';
            container.style.right = '24px';
            container.style.zIndex = '999999';
            container.style.width = '360px';
            container.style.display = 'flex';
            container.style.flexDirection = 'column';
            container.style.alignItems = 'flex-end';
            container.style.gap = '16px';
            container.style.pointerEvents = 'none'; // let clicks pass through the wrapper background
            
            // Re-enable pointer events for all children
            Array.from(container.children).forEach(child => {
                child.style.pointerEvents = 'auto';
                child.style.width = '100%';
            });
            
            // Format the Chat Panel if it exists
            const panelMarker = parentDoc.getElementById('cb-panel-marker');
            if (panelMarker) {
                const panel = panelMarker.closest('div[data-testid="stVerticalBlock"]');
                if (panel) {
                    panel.style.background = 'rgba(10,10,28,0.98)';
                    panel.style.backdropFilter = 'blur(20px)';
                    panel.style.border = '1px solid rgba(109,94,252,0.3)';
                    panel.style.borderRadius = '20px';
                    panel.style.boxShadow = '0 12px 50px rgba(0,0,0,0.7)';
                    panel.style.overflow = 'hidden';
                    panel.style.width = '360px';
                }
            }
            
            // Format the Toggle Button
            const buttons = container.querySelectorAll('button[kind="primary"]');
            if (buttons.length > 0) {
                const btn = buttons[buttons.length - 1]; // get the FAB
                btn.style.borderRadius = '50%';
                btn.style.width = '64px';
                btn.style.height = '64px';
                btn.style.background = 'linear-gradient(135deg, #6D5EFC, #3BA4FF)';
                btn.style.border = 'none';
                btn.style.boxShadow = '0 6px 24px rgba(109,94,252,0.5)';
                btn.style.padding = '0';
                btn.style.display = 'flex';
                btn.style.alignItems = 'center';
                btn.style.justifyContent = 'center';
                btn.style.marginLeft = 'auto'; // align right
                
                const p = btn.querySelector('p');
                if (p) {
                    p.style.color = 'white';
                    p.style.fontSize = '28px';
                    p.style.lineHeight = '1';
                    p.style.margin = '0';
                }
                
                // Set the container of the button to align right
                const btnWrapper = btn.closest('div');
                if (btnWrapper) {
                    btnWrapper.style.display = 'flex';
                    btnWrapper.style.justifyContent = 'flex-end';
                }
            }
        }
    }
    </script>
    """, height=0, scrolling=False)

    # ── Main Chatbot DOM Structure ──────────────────────────────────────────
    with st.container():
        st.markdown('<div id="cb-wrapper"></div>', unsafe_allow_html=True)
        
        # 1. Chat Panel (Conditional)
        if st.session_state.cb_open:
            with st.container():
                st.markdown('<div id="cb-panel-marker"></div>', unsafe_allow_html=True)
                
                # Custom Header
                st.markdown("""
                <div class="cb-native-header">
                    <div class="cb-native-avatar">✦</div>
                    <div>
                        <div class="cb-native-title">DeepAtomicIQ Assistant</div>
                        <div class="cb-native-sub">Powered by Claude AI</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Chat Messages Container
                msg_container = st.container(height=380, border=False)
                with msg_container:
                    for msg in st.session_state.cb_messages:
                        st.chat_message(msg["role"]).write(msg["content"])
                    
                    # If the last message is from the user, call Claude!
                    if st.session_state.cb_messages[-1]["role"] == "user":
                        with st.spinner("Thinking..."):
                            reply = _call_claude(st.session_state.cb_messages)
                        st.session_state.cb_messages.append({"role": "assistant", "content": reply})
                        st.rerun()
                
                # Chat Input
                if prompt := st.chat_input("Ask me anything...", key="cb_input"):
                    st.session_state.cb_messages.append({"role": "user", "content": prompt})
                    st.rerun()

        # 2. Toggle Button (Changed to Bank emoji)
        st.button("✕" if st.session_state.cb_open else "🏦", key="cb_fab", on_click=toggle_cb, type="primary")