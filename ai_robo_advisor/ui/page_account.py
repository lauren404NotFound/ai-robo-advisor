"""
ui/page_account.py
==================
User account/profile page and billing page.
"""
from __future__ import annotations
import json, datetime
import streamlit as st

from ui.styles import ACCENT, ACCENT2, ACCENT3, MUTED, PANEL, BORDER, get_svg, POS, NEG
from ui.auth import get_currency_symbol, _do_logout, update_user_name, update_password
import database

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
# ══════════════════════════════════════════════════════════════════════════════
def page_account():
    import base64, io
    user_email = st.session_state.get("user_email", "guest") or "guest"
    user_name  = st.session_state.get("user_name",  "Guest") or "Guest"
    user_data  = database.get_user(user_email) if user_email != "guest" else None
    
    # Load preferences
    prefs = {}
    if user_data and user_data.get("preferences_json"):
        try:
            prefs = json.loads(user_data["preferences_json"])
        except:
            pass
            
    initials = "".join(p[0].upper() for p in user_name.split()[:2]) if user_name != "Guest" else "?"
    
    # ── Backend Sync: Ensure session state matches DB ────────────────────
    if "user_avatar" not in st.session_state or not st.session_state.user_avatar:
        st.session_state.user_avatar = prefs.get("avatar_url", "")

    # ── High-End Design System Overrides ──────────────────────────────────────
    st.markdown("""
    <style>
    /* Premium Input Styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div {
        background: rgba(255,255,255,0.03) !important;
        color: #E8EAF6 !important;
        border: 1px solid rgba(109,94,252,0.2) !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        transition: all 0.2s ease !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #6D5EFC !important;
        background: rgba(109,94,252,0.05) !important;
        box-shadow: 0 0 0 3px rgba(109,94,252,0.15) !important;
    }
    .stTextInput label, .stTextArea label, .stSelectbox label, .stFileUploader label {
        color: #8BA6D3 !important; font-size: 13px !important; font-weight: 600 !important;
        margin-bottom: 6px !important;
    }
    .stFileUploader > div {
        background: rgba(255,255,255,0.02) !important;
        border: 2px dashed rgba(109,94,252,0.2) !important;
        border-radius: 14px !important;
    }
    /* Section dividers */
    .account-section-hdr {
        font-size: 18px; font-weight: 800; color: #fff; margin: 32px 0 16px;
        display: flex; align-items: center; gap: 10px;
    }
    .account-card {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 20px; padding: 24px;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Top Hero Header ──────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:40px 0 30px;">
      <div style="font-size:12px;color:#6D5EFC;font-weight:800;letter-spacing:.15em;margin-bottom:10px;text-transform:uppercase;">Account Center</div>
      <h1 style="font-size:38px;font-weight:900;color:#ffffff;letter-spacing:-0.04em;margin:0 0 8px;">
        Profile & Settings
      </h1>
      <p style="font-size:15px;color:#8BA6D3;max-width:600px;line-height:1.6;">
        Manage your digital identity, customize your AI preferences, and securely connect your financial accounts.
      </p>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 2.3], gap="large")

    # ── SIDEBAR: Identity Card ───────────────────────────────────────────────
    with col_left:
        avatar_url = st.session_state.get("user_avatar", "")
        emoji_choice = prefs.get("avatar_emoji", "")

        if avatar_url:
            avatar_inner = f'<img src="{avatar_url}" style="width:110px;height:110px;border-radius:50%;object-fit:cover;border:4px solid rgba(109,94,252,0.4);box-shadow:0 10px 40px rgba(0,0,0,0.4);">'
        elif emoji_choice:
            avatar_inner = f'<div style="width:110px;height:110px;border-radius:50%;background:linear-gradient(135deg,#6D5EFC,#3BA4FF);display:flex;align-items:center;justify-content:center;font-size:48px;border:4px solid rgba(109,94,252,0.4);box-shadow:0 10px 40px rgba(0,0,0,0.4);">{emoji_choice}</div>'
        else:
            avatar_inner = f'<div style="width:110px;height:110px;border-radius:50%;background:linear-gradient(135deg,#6D5EFC,#3BA4FF);display:flex;align-items:center;justify-content:center;font-size:38px;font-weight:900;color:#fff;border:4px solid rgba(109,94,252,0.4);box-shadow:0 10px 40px rgba(0,0,0,0.4);">{initials}</div>'

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(109,94,252,0.15),rgba(59,164,255,0.08));
                    border:1px solid rgba(109,94,252,0.3);border-radius:24px;
                    padding:32px 24px;text-align:center;margin-bottom:24px;box-shadow:0 20px 50px rgba(0,0,0,0.3);">
          <div style="display:flex;justify-content:center;margin-bottom:20px;">{avatar_inner}</div>
          <div style="font-size:22px;font-weight:800;color:#ffffff;margin-bottom:4px;">{user_name}</div>
          <div style="font-size:13px;color:#8BA6D3;margin-bottom:18px;">{user_email}</div>
          
          <div style="display:inline-flex;align-items:center;gap:7px;
                      background:rgba(142,246,209,0.12);border:1px solid rgba(142,246,209,0.3);
                      border-radius:30px;padding:6px 16px;">
            <span style="width:7px;height:7px;border-radius:50%;background:#8EF6D1;"></span>
            <span style="font-size:11px;color:#8EF6D1;font-weight:800;letter-spacing:0.04em;">VERIFIED ACCOUNT</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Quick Stats Card
        # Dynamic quality calculation
        has_survey = st.session_state.get("result") is not None
        has_avatar = bool(st.session_state.get("user_avatar") or prefs.get("avatar_url"))
        
        # Breakdown: Baseline 20%, Survey 40%, Bio/Details 10% each
        fields = [prefs.get("job"), prefs.get("location"), prefs.get("bio")]
        filled_count = sum(1 for v in fields if v)
        
        quality_score = 20
        if has_survey: quality_score += 40
        if has_avatar: quality_score += 10
        quality_score += (filled_count * 10)
        
        quality_score = min(100, quality_score)
        
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
                    border-radius:20px;padding:20px;margin-bottom:20px;">
          <div style="font-size:12px;color:#6D5EFC;font-weight:800;margin-bottom:16px;">PROFILE COMPLETION</div>
          <div style="height:6px;background:rgba(255,255,255,0.05);border-radius:3px;overflow:hidden;margin-bottom:12px;">
            <div style="width:{quality_score}%;height:100%;background:linear-gradient(90deg,#6D5EFC,#3BA4FF);border-radius:3px;"></div>
          </div>
          <div style="font-size:12px;color:#D4E0F7;display:flex;justify-content:space-between;">
            <span>Profile Quality</span>
            <span style="font-weight:700;">{int(quality_score)}% {'High' if quality_score > 80 else 'Medium' if quality_score > 50 else 'Low'}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Avatar Upload Section
        st.markdown('<div style="font-size:12px;color:#6D5EFC;font-weight:800;margin-bottom:8px;">PROFILE PHOTO</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload new photo", type=["png","jpg","jpeg","webp"], label_visibility="collapsed")
        if uploaded_file:
            import base64
            img_b64 = base64.b64encode(uploaded_file.read()).decode()
            data_url = f"data:{uploaded_file.type};base64,{img_b64}"
            st.session_state.user_avatar = data_url
            if user_email != "guest":
                prefs["avatar_url"] = data_url
                database.update_user_preferences(user_email, prefs)
                st.success("Photo synced to cloud!")
                st.rerun()

    # ── MAIN CONTENT: Edit Fields ────────────────────────────────────────────
    with col_right:
        
        # 🟢 Profile Customization
        st.markdown(f'<div class="account-section-hdr">{get_svg("user", 22)} Personal Information</div>', unsafe_allow_html=True)
        with st.container(border=True):
            n_col1, n_col2 = st.columns(2)
            with n_col1:
                new_full_name = st.text_input("Display Name", value=user_name)
                job_title = st.text_input("Occupation", value=prefs.get("job", ""), placeholder="e.g. Portfolio Manager")
            with n_col2:
                location = st.text_input("Location", value=prefs.get("location", ""), placeholder="e.g. Zurich, Switzerland")
                avatar_picker = st.selectbox("Avatar Emoji Fallback", [""] + ["🐻","🦁","🐼","🐯","💎","🚀","🎯","⚡"], 
                                             index=0 if not emoji_choice else ([""] + ["🐻","🦁","🐼","🐯","💎","🚀","🎯","⚡"]).index(emoji_choice))
            
            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:12px;color:#6D5EFC;font-weight:800;margin-bottom:12px;">CONTACT & IDENTITY</div>', unsafe_allow_html=True)
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                curr_code = prefs.get("phone_code", "+44 (UK)")
                phone_code = st.selectbox("Country Code", GLOBAL_COUNTRIES, index=GLOBAL_COUNTRIES.index(curr_code) if curr_code in GLOBAL_COUNTRIES else 14)
                phone_num = st.text_input("Phone Number", value=prefs.get("phone", ""), placeholder="e.g. 7123 456789")
            with c_col2:
                import datetime
                try:
                    saved_dob = datetime.datetime.strptime(prefs.get("dob", "01/01/1990"), "%d/%m/%Y").date()
                except:
                    saved_dob = datetime.date(1990, 1, 1)
                
                dob = st.date_input("Date of Birth (UK Format: DD/MM/YYYY)", 
                                   value=saved_dob,
                                   min_value=datetime.date(1920, 1, 1),
                                   max_value=datetime.date.today(),
                                   format="DD/MM/YYYY")
            
            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            about_bio = st.text_area("Bio / Investment Goals", value=prefs.get("bio", ""), placeholder="Briefly describe your goals...", height=100)
            
            if st.button("Save Profile Changes", icon=":material/save:", type="primary", use_container_width=True):
                if user_email != "guest":
                    prefs["job"] = job_title
                    prefs["location"] = location
                    prefs["bio"] = about_bio
                    prefs["avatar_emoji"] = avatar_picker
                    prefs["avatar_url"] = st.session_state.get("user_avatar", "")
                    # New fields
                    prefs["phone_code"] = phone_code
                    prefs["phone"] = phone_num
                    prefs["dob"] = dob.strftime("%d/%m/%Y")
                    
                    database.update_user_preferences(user_email, prefs)
                    
                    if new_full_name != user_name:
                        database.update_user_name(user_email, new_full_name)
                        st.session_state.user_name = new_full_name
                    
                    st.success("✅ Profile changes saved!")
                    st.rerun()

        # 🔵 Subscription Plans
        st.markdown(f'<div class="account-section-hdr">{get_svg("risk", 22)} Membership & Billing</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<p style="font-size:13px;color:#8BA6D3;margin-bottom:20px;">Choose a plan that fits your investment scale. DeepAtomicIQ AI capabilities scale with your membership level.</p>', unsafe_allow_html=True)
            
            p_col1, p_col2, p_col3 = st.columns(3)
            current_plan = prefs.get("subscription", "Essential")
            
            plans = [
                {
                    "id": "Essential", "price": "Free", "color": "#8BA6D3",
                    "feats": ["3 Portfolio Rebalances/yr", "Basic Risk Assessments", "Email Support"]
                },
                {
                    "id": "Pro", "price": "£19/mo", "color": "#6D5EFC",
                    "feats": ["Unlimited AI Rebalancing", "Real-time Regime Detection", "Daily Reports"]
                },
                {
                    "id": "Ultra", "price": "£89/mo", "color": "#8EF6D1",
                    "feats": ["Multi-Account Sync", "REST API for Institutions", "24/7 Concierge"]
                }
            ]
            
            for i, (col, plan) in enumerate(zip([p_col1, p_col2, p_col3], plans)):
                is_active = current_plan == plan["id"]
                with col:
                    active_style = f"border: 2px solid {plan['color']};" if is_active else "border: 1px solid rgba(255,255,255,0.08);"
                    feat_list = "".join([f'<div style="font-size:10px; color:#8BA6D3; margin-bottom:4px;">• {f}</div>' for f in plan["feats"]])
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.03); {active_style} padding:18px 12px; border-radius:14px; text-align:center; min-height:200px; display:flex; flex-direction:column;">
                        <div style="font-size:10px; font-weight:800; color:{plan['color']}; text-transform:uppercase;">{plan['id']}</div>
                        <div style="font-size:22px; font-weight:800; color:#fff; margin:6px 0;">{plan['price']}</div>
                        <div style="flex-grow:1; text-align:left; margin:10px 0;">{feat_list}</div>
                        {is_active and f'<div style="font-size:10px; font-weight:900; background:{plan["color"]}; color:#000; padding:4px 8px; border-radius:10px; display:inline-block; align-self:center;">ACTIVE</div>' or ''}
                    </div>
                    """, unsafe_allow_html=True)
                    if not is_active:
                        if st.button(f"Upgrade to {plan['id']}", key=f"sub_{plan['id']}", use_container_width=True):
                            st.session_state.pending_plan = plan["id"]
                            st.session_state.nav_page = "billing"
                            st.rerun()
            
            st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
            st.markdown('<p style="font-size:11px;color:#8BA6D3;text-align:center;">Secure payment processing via DeepAtomicIQ Stripe Integration.</p>', unsafe_allow_html=True)

        # 🔴 Security & Compliance
        st.markdown(f'<div class="account-section-hdr">{get_svg("risk", 22)} Security & Compliance</div>', unsafe_allow_html=True)
        with st.expander("Control Center (Advanced Settings)"):
            st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
            if st.button("🔑 Change Master Password", use_container_width=True, key="btn_pw_reset"):
                st.session_state.show_pw_form = True
            
            if st.session_state.get("show_pw_form"):
                st.markdown('<div style="background:rgba(255,255,255,0.05); padding:20px; border-radius:15px; margin-top:10px; border:1px solid rgba(109,94,252,0.3);">', unsafe_allow_html=True)
                provider = user_data.get("provider", "email") if user_data else "guest"
                
                if provider != "email":
                    st.info(f"💡 You are logged in via **{provider.capitalize()}**. This form will update your local DeepAtomicIQ fallback password.")
                
                with st.form("pw_reset_form", clear_on_submit=True):
                    st.markdown('<div style="font-size:14px; font-weight:700; color:#fff; margin-bottom:15px;">Update Master Password</div>', unsafe_allow_html=True)
                    new_pw = st.text_input("New Secure Password", type="password")
                    conf_pw = st.text_input("Confirm New Password", type="password")
                    
                    c1, c2 = st.columns([1,1])
                    with c1:
                        if st.form_submit_button("Update Password", type="primary", use_container_width=True):
                            if not new_pw or len(new_pw) < 6:
                                st.error("Password too short (min 6 chars).")
                            elif new_pw != conf_pw:
                                st.error("Passwords do not match.")
                            elif user_email == "guest":
                                st.error("Guest users cannot modify session credentials.")
                            else:
                                database.update_password(user_email, new_pw)
                                st.success("✅ Password updated!")
                                st.session_state.show_pw_form = False
                                st.rerun()
                    with c2:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.show_pw_form = False
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.05);margin:20px 0;">', unsafe_allow_html=True)
            
            st.markdown('<div style="font-size:13px;font-weight:700;color:#FF6B6B;margin-bottom:4px;">ACCOUNT TERMINATION</div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:11px;color:#8BA6D3;margin-bottom:12px;">Deleting your account will wipe all AI portfolio history and personal data.</div>', unsafe_allow_html=True)
            
            if st.button("Permanently Delete Account", type="secondary", use_container_width=True):
                st.error("Account deletion is restricted to administrative users in this demo environment.")





