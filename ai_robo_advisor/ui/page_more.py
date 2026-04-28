"""
ui/page_more.py
===============
Preferences / "More" settings page.
"""
from __future__ import annotations
import json
import streamlit as st

from ui.styles import ACCENT, ACCENT2, MUTED, PANEL, BORDER, get_svg, GLOBAL_CURRENCIES
from ui.auth import get_currency_symbol
import database

def page_more():
    user_email = st.session_state.get("user_email", "guest") or "guest"
    user_name  = st.session_state.get("user_name",  "Guest") or "Guest"
    user_data  = database.get_user(user_email) if user_email != "guest" else None
    prefs      = json.loads(user_data["preferences_json"]) if user_data and user_data.get("preferences_json") else {}
    initials   = "".join(p[0].upper() for p in user_name.split()[:2]) if user_name != "Guest" else "?"

    st.markdown("""
    <div style="padding:32px 0 28px;">
      <div style="font-size:11px;color:#6D5EFC;font-weight:700;letter-spacing:.12em;margin-bottom:8px;">ACCOUNT</div>
      <div style="font-size:32px;font-weight:900;color:#ffffff;letter-spacing:-0.03em;margin-bottom:6px;">
        Settings &amp; Support
      </div>
      <div style="font-size:14px;color:#8BA6D3;">Manage your profile, notifications, and get help.</div>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 2], gap="large")

    with col_left:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(109,94,252,0.14),rgba(59,164,255,0.07));
                    border:1px solid rgba(109,94,252,0.28);border-radius:20px;
                    padding:28px 22px;text-align:center;margin-bottom:16px;">
          <div style="width:70px;height:70px;border-radius:50%;
                      background:linear-gradient(135deg,#6D5EFC,#3BA4FF);
                      display:flex;align-items:center;justify-content:center;
                      font-size:26px;font-weight:900;color:#fff;margin:0 auto 14px;">
            {initials}
          </div>
          <div style="font-size:19px;font-weight:800;color:#ffffff;margin-bottom:4px;">{user_name}</div>
          <div style="font-size:12px;color:#8BA6D3;word-break:break-all;margin-bottom:16px;">{user_email}</div>
          <div style="display:inline-flex;align-items:center;gap:6px;
                      background:rgba(142,246,209,0.1);border:1px solid rgba(142,246,209,0.25);
                      border-radius:20px;padding:5px 14px;">
            <span style="width:7px;height:7px;border-radius:50%;background:#8EF6D1;display:inline-block;"></span>
            <span style="font-size:11px;color:#8EF6D1;font-weight:700;">Active Account</span>
          </div>
        </div>
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);
                    border-radius:16px;padding:18px 20px;">
          <div style="font-size:11px;color:#6D5EFC;font-weight:700;letter-spacing:.08em;margin-bottom:14px;">NAVIGATE</div>
          <a href="?page=dashboard" style="display:flex;align-items:center;gap:10px;padding:9px 0;
             border-bottom:1px solid rgba(255,255,255,0.05);text-decoration:none;
             color:#D4E0F7;font-size:13px;font-weight:500;">{get_svg('dashboard', 14)}&nbsp; My Dashboard</a>
          <a href="?page=market" style="display:flex;align-items:center;gap:10px;padding:9px 0;
             border-bottom:1px solid rgba(255,255,255,0.05);text-decoration:none;
             color:#D4E0F7;font-size:13px;font-weight:500;">{get_svg('market', 14)}&nbsp; Live Markets</a>
          <a href="?page=insights" style="display:flex;align-items:center;gap:10px;padding:9px 0;
             text-decoration:none;color:#D4E0F7;font-size:13px;font-weight:500;">{get_svg('news', 14)}&nbsp; News &amp; Insights</a>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(109,94,252,0.1),rgba(59,164,255,0.05));
                    border:1px solid rgba(109,94,252,0.2); border-radius:16px; padding:24px; margin-bottom:24px;">
          <div style="font-size:18px; font-weight:900; color:#ffffff; margin-bottom:4px; display:flex; align-items:center; gap:10px;">
            {get_svg('settings', 20)} Platform Preferences
          </div>
          <p style="font-size:13px; color:#8BA6D3; margin-bottom:0;">Customize how DeepAtomicIQ interacts with your financial life.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06); border-radius:16px; padding:24px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;color:#6D5EFC;font-weight:800;letter-spacing:.12em;margin-bottom:18px;text-transform:uppercase;">Notifications & Alerts</div>', unsafe_allow_html=True)

        reports = st.checkbox("Weekly Portfolio Report emails",
                              value=prefs.get("reports", True),
                              help="Receive a weekly email summary of your portfolio performance")
        alerts  = st.checkbox("Real-Time Volatility Alerts", 
                              value=prefs.get("alerts", False),
                              help="Get notified when market volatility spikes")

        st.markdown("""<div style="border-top:1px solid rgba(255,255,255,0.07);margin:18px 0 16px;"></div>
          <div style="font-size:11px;color:#6D5EFC;font-weight:700;letter-spacing:.08em;margin-bottom:12px;">DISPLAY</div>
        """, unsafe_allow_html=True)

        currency = st.selectbox("Default Currency", GLOBAL_CURRENCIES,
                                index=GLOBAL_CURRENCIES.index(prefs.get("currency", "GBP (£)")) if prefs.get("currency") in GLOBAL_CURRENCIES else 45,
                                help="Sets how monetary values display across the dashboard")
        st.markdown("</div>", unsafe_allow_html=True)

        sc1, sc2 = st.columns(2, gap="small")
        with sc1:
            if st.button("Save Preferences", type="primary", use_container_width=True):
                if user_email == "guest":
                    st.error("Please login to save preferences.")
                else:
                    new_prefs = {**prefs, "reports": reports, "alerts": alerts, "currency": currency}
                    database.update_user_preferences(user_email, new_prefs)
                    st.session_state.preferences = new_prefs
                    st.toast("✅ Preferences saved and synced to backend!")
                    st.rerun()
        with sc2:
            if st.button("Refresh App", use_container_width=True, key="ref_app"):
                st.rerun()

        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
        st.markdown(f"""<div style="font-size:16px;font-weight:800;color:#ffffff;margin-bottom:14px;">
          {get_svg('help', 16)} Frequently Asked Questions</div>""", unsafe_allow_html=True)

        for q, a in [
            ("How does the AI work?",
             "DeepAtomicIQ uses a **Markowitz-Informed Neural Network (MINN)** that learns optimal "
             "risk-return trade-offs from historical market data. Your survey answers tune the risk "
             "threshold (δ) and temporal decay (γ), personalising your portfolio to you."),
            ("Is my data secure?",
             "Credentials are hashed with **bcrypt (unbreakable hashing)**. For the MVP, data is kept in a "
             "secure SQLite instance, but our architecture is **MongoDB-Ready**. For production (Community Cloud),"
             " we use **MongoDB Atlas** for distributed, AES-256 encrypted storage. The system is architected "
             "to be fully GDPR-compliant with strict data isolation."),
            ("What is the Sharpe Ratio?",
             "**Sharpe Ratio = (Return − Risk-Free Rate) ÷ Volatility.** It measures return per unit "
             "of risk. A ratio above **1.0** is generally good. The MINN maximises this during optimisation."),
        ]:
            with st.expander(q):
                st.markdown(a)

        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
        st.markdown(f"""<div style="font-size:16px;font-weight:800;color:#ffffff;margin-bottom:14px;">
          {get_svg('email', 16)} Contact Support</div>
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
                    border-radius:16px;padding:22px 24px;">
          <p style="font-size:13px;color:#8BA6D3;margin:0 0 18px;">
            Have a bug report or question? Fill in below and we'll reply within 24 hours.
          </p>""", unsafe_allow_html=True)

        subj = st.text_input("Subject", placeholder="e.g. Dashboard not loading", key="support_subj")
        msg  = st.text_area("Message", placeholder="Describe your issue in detail...",
                            key="support_msg", height=110)
        if st.button("Send Message", type="primary", use_container_width=True):
            if user_email == "guest":
                st.warning("Please login to submit a support ticket.")
            elif not subj or not msg:
                st.error("Please fill in both Subject and Message.")
            else:
                database.save_ticket(user_email, subj, msg)
                st.success("✅ Ticket submitted! Check your email for confirmation.")
        st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# BILLING PAGE
# ══════════════════════════════════════════════════════════════════════════════
def page_billing():
    user_email = st.session_state.get("user_email", "guest") or "guest"
    pending_plan = st.session_state.get("pending_plan", "Pro")
    
    st.markdown(f"""
    <div style="padding:40px 0 20px;">
      <div style="font-size:12px;color:#6D5EFC;font-weight:800;letter-spacing:.12em;margin-bottom:8px;">CHECKOUT</div>
      <div style="font-size:32px;font-weight:900;color:#ffffff;letter-spacing:-0.03em;">
        Complete your subscription to {pending_plan}
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1.5, 1], gap="large")
    
    with col1:
        st.markdown(f'<div class="account-section-hdr">{get_svg("risk", 20)} Payment Method</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
            card_name = st.text_input("Cardholder Name", value=st.session_state.get("user_name", ""))
            card_num = st.text_input("Card Number", placeholder="0000 0000 0000 0000")
            
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Expiry Date", placeholder="MM/YY")
            with c2:
                st.text_input("CVV", type="password", placeholder="123")
                
            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            if st.button(f"Confirm & Pay for {pending_plan}", type="primary", use_container_width=True):
                if not card_num:
                    st.error("Please enter card details.")
                else:
                    # Sync to DB
                    import json
                    user_data = database.get_user(user_email)
                    prefs = json.loads(user_data["preferences_json"]) if user_data and user_data.get("preferences_json") else {}
                    prefs["subscription"] = pending_plan
                    prefs["payment_verified"] = True
                    database.update_user_preferences(user_email, prefs)
                    
                    st.success(f"🎉 Welcome to {pending_plan}! Your account has been upgraded.")
                    st.balloons()
                    st.session_state.nav_page = "account"
                    st.rerun()

    with col2:
        st.markdown(f'<div class="account-section-hdr">{get_svg("settings", 20)} Order Summary</div>', unsafe_allow_html=True)
        price = "£19.00" if pending_plan == "Pro" else "£89.00" if pending_plan == "Ultra" else "£0.00"
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:24px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                <span style="color:#8BA6D3;">DeepAtomicIQ {pending_plan}</span>
                <span style="color:#fff; font-weight:700;">{price}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                <span style="color:#8BA6D3;">Service Activation</span>
                <span style="color:#8EF6D1; font-weight:700;">FREE</span>
            </div>
            <div style="border-top:1px solid rgba(255,255,255,0.05); margin:12px 0; padding-top:12px; display:flex; justify-content:space-between;">
                <span style="color:#fff; font-weight:800;">TOTAL DUE</span>
                <span style="color:#6D5EFC; font-size:20px; font-weight:900;">{price}</span>
            </div>
            <div style="font-size:11px; color:#8BA6D3; margin-top:20px; font-style:italic;">
                * Recurring monthly billing. You can cancel your subscription at any time from your account settings.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("← Back to Account", use_container_width=True):
            st.session_state.nav_page = "account"
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MY ACCOUNT PAGE
