import os
import re

with open("ai_robo_advisor/app.py", "r") as f:
    text = f.read()

# 1. Navbar changes: "Home, Dashboard, Markets, News, AI Insights"
text = text.replace('("market",    "Market"),', '("market",    "Markets"),')
text = text.replace('("search",    "Search"),', '("insights",  "AI Insights"),')
text = text.replace('("search",    "🔍 Search"),', '("insights",  "🧠 AI Insights"),')
text = text.replace('page=="search"', 'page=="insights"')
text = text.replace('trig_search', 'trig_insights')
text = text.replace('"search":    page_search,', '"search":    page_search, "insights": page_news,')  # fallback

# 2. Add Start Assessment to Navbar Right
old_nav_right = """
        right_html = \"\"\"
          <div class="nav-account" style="background:transparent;border:none;">
            <div class="nav-link" style="padding:8px 12px;color:#ffffff;">Login</div>
            <div class="nav-link" style="background:rgba(155, 114, 242, 0.15);color:#9B72F2;">Sign Up</div>
          </div>
        \"\"\"
"""
new_nav_right = """
        right_html = \"\"\"
          <div class="nav-account" style="background:transparent;border:none;">
            <div class="nav-link" style="padding:8px 12px;color:#ffffff;">Login</div>
            <div class="nav-link" style="padding:8px 12px; border:1px solid rgba(255,255,255,0.1); color:#ffffff; margin-right:8px;">Sign Up</div>
            <div class="nav-link" style="background:#6D5EFC; color:#ffffff; font-weight:700;">Start Assessment</div>
          </div>
        \"\"\"
"""
text = text.replace(old_nav_right, new_nav_right)

# 3. Streamlit column triggers for the CTA
text = text.replace('c1, c2 = st.columns(2)', 'c1, c2, c3 = st.columns([1,1,1.5])')
text = text.replace('if c2.button("Signup", key="trig_signup"):', 'if c2.button("Signup", key="trig_signup"):\n                st.session_state.show_auth = True\n                st.session_state.auth_mode = "signup"; st.rerun()\n            if c3.button("Assessment", key="trig_cta"):\n')

# 4. Update the stApp background CSS
text = text.replace(
    'linear-gradient(180deg, #0A0A16 0%, {CANVAS} 50%, #080812 100%);',
    'linear-gradient(135deg, #070B1A 0%, #0F172A 100%);'
)

# 5. Overwrite page_home content completely using regex
new_page_home = '''def page_home():
    st.markdown("""
    <style>
      .hero-section {
        display: flex; align-items: center; justify-content: space-between;
        margin-top: 40px; margin-bottom: 80px; gap: 40px;
      }
      .hero-left { flex: 1; min-width: 45%; }
      .hero-headline {
        font-size: 3.8rem; font-weight: 900; letter-spacing: -0.04em; color: #ffffff;
        line-height: 1.1; margin-bottom: 24px;
      }
      .hero-subhead {
        font-size: 1.1rem; color: #8BA6D3; line-height: 1.6; margin-bottom: 40px;
        max-width: 90%;
      }
      .cta-btn-primary {
        background: #6D5EFC; color: #ffffff; font-size: 16px; font-weight: 700;
        padding: 14px 28px; border-radius: 12px; border: none; cursor: pointer;
        transition: all 0.2s; text-decoration: none; display: inline-block;
        box-shadow: 0 8px 24px rgba(109, 94, 252, 0.4);
      }
      .cta-btn-primary:hover { transform: translateY(-2px); box-shadow: 0 12px 32px rgba(109, 94, 252, 0.6); }
      .cta-btn-secondary {
        background: rgba(255,255,255,0.03); color: #ffffff; font-size: 16px; font-weight: 600;
        padding: 14px 28px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); cursor: pointer;
        transition: all 0.2s; text-decoration: none; display: inline-flex; align-items: center; gap: 8px;
        margin-left: 16px;
      }
      .cta-btn-secondary:hover { background: rgba(255,255,255,0.08); }
      
      .hero-right { flex: 1; }
      .glass-card-hero {
        background: rgba(255,255,255,0.02); backdrop-filter: blur(24px);
        border: 1px solid rgba(255,255,255,0.06); border-radius: 20px;
        padding: 30px; box-shadow: 0 24px 60px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1);
        position: relative; overflow: hidden;
      }
      .glass-card-hero::before {
        content: ""; position: absolute; top: -50px; right: -50px;
        width: 150px; height: 150px; background: radial-gradient(circle, rgba(142,246,209,0.2) 0%, transparent 70%);
        border-radius: 50%; pointer-events: none;
      }
      
      .hero-metric-grid { display: grid; grid-template-columns: 1.5fr 1fr; gap: 16px; margin-bottom: 16px; }
      .hero-metric { background: rgba(0,0,0,0.2); border-radius: 12px; padding: 16px; border: 1px solid rgba(255,255,255,0.03); }
      .hm-title { font-size: 11px; color: #8BA6D3; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
      .hm-val { font-size: 24px; font-weight: 800; color: #ffffff; }
      .hm-trend { font-size: 12px; color: #8EF6D1; margin-left: 8px; }
      
      /* Features */
      .feature-section { margin-top: 80px; }
      .feature-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-top: 40px; }
      .feature-card {
        background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
        border-radius: 16px; padding: 28px; transition: all 0.3s ease;
        backdrop-filter: blur(12px); position: relative; overflow: hidden;
      }
      .feature-card:hover {
        background: rgba(255,255,255,0.04); border-color: rgba(109, 94, 252, 0.4);
        transform: translateY(-4px); box-shadow: 0 16px 40px rgba(0,0,0,0.3);
      }
      .feature-icon {
        width: 48px; height: 48px; border-radius: 12px; margin-bottom: 20px;
        background: linear-gradient(135deg, rgba(109,94,252,0.2), rgba(59,164,255,0.1));
        display: flex; align-items: center; justify-content: center; font-size: 24px;
        border: 1px solid rgba(109,94,252,0.2);
      }
      .feature-title { font-size: 18px; font-weight: 700; color: #ffffff; margin-bottom: 10px; }
      .feature-desc { font-size: 14px; color: #8BA6D3; line-height: 1.6; }
      
      /* Explainer */
      .explain-section { margin-top: 100px; margin-bottom: 60px; text-align: center; }
      .explain-title { font-size: 32px; font-weight: 800; color: #ffffff; margin-bottom: 16px; }
      .chat-box {
        background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05);
        border-radius: 20px; padding: 30px; text-align: left; max-width: 800px; margin: 0 auto;
        border-left: 4px solid #3BA4FF; box-shadow: 0 20px 50px rgba(0,0,0,0.3);
      }
    </style>

    <div class="hero-section">
      <div class="hero-left">
        <div class="hero-headline">AI-Powered <br><span style="background: linear-gradient(90deg, #6D5EFC, #3BA4FF); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Portfolio Intelligence</span></div>
        <div class="hero-subhead">
          Personalised portfolio construction using neural inference, regime detection, and risk-aware optimisation directly mapped to your unique financial DNA.
        </div>
      </div>
      <div class="hero-right">
        <div class="glass-card-hero">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <div style="font-size:14px; color:#ffffff; font-weight:700;">Live Dashboard</div>
            <div style="background:rgba(142,246,209,0.1); color:#8EF6D1; padding:4px 10px; border-radius:20px; font-size:11px; font-weight:700;">Profile 4 Active</div>
          </div>
          
          <div class="hero-metric-grid">
            <div class="hero-metric">
              <div class="hm-title">Portfolio Performance</div>
              <div class="hm-val">£87,966.37 <span class="hm-trend">▲ 6.35%</span></div>
            </div>
            <div class="hero-metric">
              <div class="hm-title">AI Confidence</div>
              <div class="hm-val" style="color:#6D5EFC;">87<span style="font-size:14px;">/100</span></div>
            </div>
          </div>
          
          <div style="display:flex; gap:16px;">
            <div class="hero-metric" style="flex:1;">
              <div class="hm-title">Asset Allocation</div>
              <div style="height:80px; width:80px; border-radius:50%; border:8px solid #3BA4FF; border-top-color:#6D5EFC; border-right-color:#8EF6D1; margin: 10px auto;"></div>
            </div>
          </div>
          
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ── Invisible Streamlit buttons for navigation on Hero ──
    h_cols = st.columns([1.5, 1])
    with h_cols[0]:
        cc1, cc2, cc3 = st.columns([1.2, 1, 1.5])
        with cc1:
            if st.button("Start Assessment →", key="hero_start", type="primary", use_container_width=True):
                st.session_state.nav_page = "dashboard"; st.session_state.survey_page = "survey"
                st.session_state.survey_step = 0; st.session_state.survey_answers = {}; st.rerun()
        with cc2:
            st.button("Play Demo", key="hero_demo", use_container_width=True)

    st.markdown("""
    <div class="feature-section">
      <div class="feature-grid">
        <div class="feature-card">
          <div class="feature-icon">🧠</div>
          <div class="feature-title">Neural Optimisation</div>
          <div class="feature-desc">Markowitz-Informed Neural Networks maximize Sharpe Ratios in real-time.</div>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🛡️</div>
          <div class="feature-title">Regime Detection</div>
          <div class="feature-desc">AI protects capital during extreme co-movement events dynamically.</div>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🔬</div>
          <div class="feature-title">Explainable AI Signals</div>
          <div class="feature-desc">No black boxes. We expose parameters that explain the model's logic.</div>
        </div>
        <div class="feature-card">
          <div class="feature-icon">📊</div>
          <div class="feature-title">Correlation Intelligence</div>
          <div class="feature-desc">IQ-based bounds outperform historical averages via nonlinear ties.</div>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🎲</div>
          <div class="feature-title">Risk Engine</div>
          <div class="feature-desc">Deep Monte Carlo simulations based on manifold structures, not standard curves.</div>
        </div>
        <div class="feature-card">
          <div class="feature-icon">⚡</div>
          <div class="feature-title">Adaptive Allocation</div>
          <div class="feature-desc">Real-time balancing informed by instantaneous macroeconomic shifts.</div>
        </div>
      </div>
    </div>
    
    <div class="explain-section">
      <div class="explain-title">Why This Portfolio Fits You</div>
      <div class="chat-box">
        <div style="display:flex; align-items:center; margin-bottom:12px;">
          <div style="background:#3BA4FF; width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; margin-right:12px;">🤖</div>
          <div style="font-weight:700; color:#fff;">DeepAtomicIQ Interpreter</div>
        </div>
        <div style="color:#8BA6D3; line-height:1.7; font-size:15px; margin-bottom:16px;">
          "Based on your inputs, our models infer a <b>Moderate-Aggressive</b> profile with <b>87%</b> confidence.<br><br>
          We allocate heavily towards technology and large-cap equities (expected growth: <b>7.8%</b>) to capitalize on 
          your 15-year horizon, while embedding a 30% defensive wing to hedge against predicted short-term volatility."
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
'''

# Use regex to replace the entire old page_home block.
pattern = re.compile(r'def page_home\(\):(.*?)# ── SURVEY \+ PORTFOLIO', re.DOTALL)
text = pattern.sub(new_page_home + "\n\n# ── SURVEY + PORTFOLIO", text)

with open("ai_robo_advisor/app.py", "w") as f:
    f.write(text)
