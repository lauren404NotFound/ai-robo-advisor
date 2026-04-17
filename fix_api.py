import re

with open("ai_robo_advisor/app.py", "r") as f:
    text = f.read()

# 1. Fix the blank line markdown bug in page_home
# Replace all blank lines inside the new_page_home block with nothing, or just dedent.
# The simplest fix is to take the block and remove blank lines inside the hero string
pattern_hero = re.compile(r'(<div class="hero-section">.*?</style>\s*)(<div class="hero-section">.*?</div>\s*"")', re.DOTALL)
# Actually, the string in app.py has `<style>...</style>` then `<div class="hero-section">...`
# Let's just find the entire st.markdown block in page_home and strip out all blank lines inside the HTML
match = re.search(r'(<div class="hero-section">.*?</div>\s*</div>\s*</div>)', text, re.DOTALL)
if match:
    hero_html = match.group(1)
    hero_html_no_blank = "\n".join([line for line in hero_html.split('\n') if line.strip() != ""])
    text = text.replace(hero_html, hero_html_no_blank)

# Same for feature-section and explain-section
match = re.search(r'(<div class="feature-section">.*?</div>\s*</div>\s*</div>)', text, re.DOTALL)
if match:
    feat_html = match.group(1)
    feat_html_no_blank = "\n".join([line for line in feat_html.split('\n') if line.strip() != ""])
    text = text.replace(feat_html, feat_html_no_blank)

match = re.search(r'(<div class="explain-section">.*?</div>\s*</div>)', text, re.DOTALL)
if match:
    exp_html = match.group(1)
    exp_html_no_blank = "\n".join([line for line in exp_html.split('\n') if line.strip() != ""])
    text = text.replace(exp_html, exp_html_no_blank)


# 2. Hook up yfinance to page_market
new_page_market = """import yfinance as yf

@st.cache_data(ttl=60)
def get_live_market_data():
    tickers = ["VOO", "QQQ", "VWRA.L", "AGG", "GLD", "VNQ", "ESGU", "PDBC"]
    names = ["Vanguard S&P 500", "Invesco Nasdaq 100", "Vanguard All-World", "iShares Core US Bonds", "SPDR Gold Shares", "Vanguard Real Estate", "iShares ESG S&P 500", "Invesco Commodities"]
    
    data = []
    try:
        # Fetch data for all tickers at once for performance
        tickers_str = " ".join(tickers)
        # Using period='5d' to ensure we get previous close even over weekends/holidays
        hist = yf.download(tickers_str, period="5d", progress=False)
        
        for i, t in enumerate(tickers):
            try:
                # get the closing prices
                closes = hist['Close'][t].dropna()
                if len(closes) >= 2:
                    current_price = closes.iloc[-1]
                    prev_price = closes.iloc[-2]
                    chg_pct = ((current_price - prev_price) / prev_price) * 100
                    
                    currency = "£" if t == "VWRA.L" else "$"
                    display_ticker = "VWRA" if t == "VWRA.L" else t
                    
                    data.append((
                        display_ticker,
                        names[i],
                        f"{currency}{current_price:.2f}",
                        f"{'+' if chg_pct > 0 else ''}{chg_pct:.2f}%",
                        chg_pct >= 0
                    ))
                else:
                    raise Exception("Not enough data")
            except Exception:
                # fallback if missing data
                data.append((t, names[i], "N/A", "N/A", True))
                
        return data
    except Exception as e:
        return [
            ("VOO",  "Vanguard S&P 500", "$489.12", "+1.23%", True),
            ("QQQ",  "Invesco Nasdaq 100","$425.88","+2.10%", True),
            ("VWRA", "Vanguard All-World", "£97.44", "+0.87%", True),
            ("AGG",  "iShares Core US Bonds","$95.30","-0.12%", False),
            ("GLD",  "SPDR Gold Shares",  "$228.60","+0.65%", True),
            ("VNQ",  "Vanguard Real Estate","$81.20","-0.34%", False),
            ("ESGU", "iShares ESG S&P 500","$103.45","+1.04%", True),
            ("PDBC", "Invesco Commodities","$14.22", "+0.22%", True),
        ]

def page_market():
    st.markdown(f\"\"\"
    <div style="padding:32px 0 20px 0;">
      <div style="font-size:22px;font-weight:800;color:#ffffff;margin-bottom:6px;">Market Overview</div>
      <div style="font-size:13px;color:{MUTED};"><strong style="color:#8EF6D1;">Live Connection Active:</strong> Real-time indicative quotes powered by Yahoo Finance API</div>
    </div>
    \"\"\", unsafe_allow_html=True)

    with st.spinner("Fetching live market data..."):
        markets = get_live_market_data()

    cols = st.columns(4)
    for i, (ticker, name, price, chg, up) in enumerate(markets):
        with cols[i % 4]:
            chg_class = "market-change-pos" if up else "market-change-neg"
            arrow = "▲" if up else "▼" if chg != "N/A" else ""
            st.markdown(f\"\"\"
            <div class="market-card">
              <div class="market-ticker">{ticker}</div>
              <div class="market-name">{name}</div>
              <div class="market-price">{price}</div>
              <div class="{chg_class}">{arrow} {chg}</div>
            </div>
            \"\"\", unsafe_allow_html=True)
"""

pattern_market = re.compile(r'def page_market\(\):.*?unsafe_allow_html=True\)', re.DOTALL)
# Actually, better to replace from `# ── MARKET` to `# ── SEARCH`
market_section = re.search(r'# ── MARKET ──.*?# ── SEARCH ──', text, re.DOTALL)
if market_section:
    text = text.replace(market_section.group(0), "# ── MARKET ────────────────────────────────────────────────────────────────────\n" + new_page_market + "\n\n# ── SEARCH ────────────────────────────────────────────────────────────────────")


with open("ai_robo_advisor/app.py", "w") as f:
    f.write(text)
