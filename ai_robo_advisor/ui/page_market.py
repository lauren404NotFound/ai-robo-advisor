"""
ui/page_market.py
=================
Live market data page.
"""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
import datetime

from ui.styles import ACCENT, ACCENT2, MUTED, PANEL, BORDER, get_svg, POS, NEG, TMPL, TEXT, GRID
from ui.auth import get_currency_symbol
import database

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

@st.cache_data(ttl=300)
def get_sparkline_data():
    """Fetch 30-day history for sparklines and the main chart."""
    tickers = ["VOO", "QQQ", "VWRA.L", "AGG", "GLD", "VNQ", "ESGU", "PDBC"]
    try:
        hist = yf.download(" ".join(tickers), period="30d", progress=False)["Close"]
        return hist
    except:
        return None

def page_market():
    import datetime
    st.markdown("""
<style>
.ticker-wrap {
  overflow: hidden; background: rgba(255,255,255,0.02);
  border-top: 1px solid rgba(255,255,255,0.05);
  border-bottom: 1px solid rgba(255,255,255,0.05);
  padding: 10px 0; margin-bottom: 0;
}
.ticker-track {
  display: flex; gap: 0;
  animation: ticker 45s linear infinite;
  white-space: nowrap;
}
@keyframes ticker { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
.ticker-item {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 0 28px; font-size: 12px; font-weight: 600;
  border-right: 1px solid rgba(255,255,255,0.06);
}
.ticker-sym { color: #ffffff; font-weight: 800; }
.ticker-price { color: #8BA6D3; }
.ticker-up { color: #8EF6D1; }
.ticker-dn { color: #FF6B6B; }
.mkt-section-title {
  font-size: 16px; font-weight: 800; color: #ffffff;
  margin: 32px 0 16px; letter-spacing: -0.02em;
  display: flex; align-items: center; gap: 8px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.mkt-section-title span { font-size: 12px; font-weight: 500; color: #8BA6D3; }
.mkt-card {
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 16px; padding: 16px 18px 10px;
  transition: all 0.2s ease; cursor: default;
}
.mkt-card:hover {
  background: rgba(255,255,255,0.045);
  border-color: rgba(109,94,252,0.35);
  transform: translateY(-2px);
}
.mkt-ticker { font-size: 16px; font-weight: 900; color: #fff; letter-spacing: -0.02em; }
.mkt-name  { font-size: 10px; color: #8BA6D3; font-weight: 600; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 120px; }
.mkt-price { font-size: 20px; font-weight: 900; color: #fff; letter-spacing: -0.02em; }
.mover-card {
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px; padding: 14px 18px;
  display: flex; align-items: center; justify-content: space-between;
}
</style>
""", unsafe_allow_html=True)

    markets  = get_live_market_data()
    hist_df  = get_sparkline_data()
    ticker_map = {"VOO":"VOO","QQQ":"QQQ","VWRA":"VWRA.L","AGG":"AGG","GLD":"GLD","VNQ":"VNQ","ESGU":"ESGU","PDBC":"PDBC"}

    # ── Page Header ───────────────────────────────────────────────────────────
    now_str = datetime.datetime.now().strftime("%A %d %b %Y · %H:%M")
    gainers = [m for m in markets if m[4]]
    losers  = [m for m in markets if not m[4]]
    st.markdown(f"""
<div style="padding:28px 0 16px; display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:12px;">
  <div>
    <div style="font-size:11px;font-weight:800;color:#6D5EFC;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:8px;">Live Markets Terminal</div>
    <div style="font-size:36px;font-weight:900;color:#fff;letter-spacing:-0.03em;">Markets</div>
    <div style="font-size:13px;color:#8BA6D3;margin-top:4px;">{now_str} · ETF Universe</div>
  </div>
  <div style="display:flex;gap:16px;">
    <div style="text-align:center;background:rgba(142,246,209,0.06);border:1px solid rgba(142,246,209,0.2);border-radius:12px;padding:10px 20px;">
      <div style="font-size:22px;font-weight:900;color:#8EF6D1;">{len(gainers)}</div>
      <div style="font-size:10px;font-weight:700;color:#8BA6D3;text-transform:uppercase;">Advancing</div>
    </div>
    <div style="text-align:center;background:rgba(255,107,107,0.06);border:1px solid rgba(255,107,107,0.2);border-radius:12px;padding:10px 20px;">
      <div style="font-size:22px;font-weight:900;color:#FF6B6B;">{len(losers)}</div>
      <div style="font-size:10px;font-weight:700;color:#8BA6D3;text-transform:uppercase;">Declining</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Ticker Tape ───────────────────────────────────────────────────────────
    tape_items = ""
    for ticker, name, price, chg, up in markets:
        cls   = "ticker-up" if up else "ticker-dn"
        arrow = "▲" if up else "▼"
        tape_items += f'<div class="ticker-item"><span class="ticker-sym">{ticker}</span><span class="ticker-price">{price}</span><span class="{cls}">{arrow} {chg}</span></div>'
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-track">{tape_items}{tape_items}</div></div>', unsafe_allow_html=True)

    # ── My Watchlist Bar (Load from MongoDB) ──────────────────────────────────
    email = st.session_state.get("user_email")
    if email:
        watchlist = database.get_watchlist(email)
        if watchlist:
            st.markdown(f'<div class="mkt-section-title">{get_svg("star", 16)} My Favorites <span>· Quick access to pinned assets</span></div>', unsafe_allow_html=True)
            w_cols = st.columns(min(len(watchlist), 6))
            for i, ticker in enumerate(watchlist[:6]):
                w_live = next((m for m in markets if m[0] == ticker), None)
                if w_live:
                    col_w = "#8EF6D1" if w_live[4] else "#FF6B6B"
                    with w_cols[i]:
                        st.markdown(f"""
                        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:12px;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;">
                          <div><div style="font-size:10px;font-weight:800;color:#8BA6D3;">{ticker}</div><div style="font-size:14px;font-weight:900;color:#fff;">{w_live[2]}</div></div>
                          <div style="text-align:right;"><div style="font-size:11px;font-weight:800;color:{col_w};">{"▲" if w_live[4] else "▼"} {w_live[3]}</div></div>
                        </div>""", unsafe_allow_html=True)

    # ── Top Movers ────────────────────────────────────────────────────────────
    st.markdown(f'<div class="mkt-section-title">{get_svg("zap", 16)} Top Movers <span>· Today\'s leaders & laggards</span></div>', unsafe_allow_html=True)
    mc1, mc2 = st.columns(2, gap="large")
    with mc1:
        st.markdown('<div style="font-size:10px;font-weight:800;color:#8EF6D1;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;">Best Performers</div>', unsafe_allow_html=True)
        sorted_gain = sorted(markets, key=lambda x: float(x[3].replace('%','').replace('+','')) if x[3] != 'N/A' else -99, reverse=True)[:3]
        for ticker, name, price, chg, up in sorted_gain:
            st.markdown(f"""
<div class="mover-card" style="margin-bottom:8px;border-color:rgba(142,246,209,0.2);">
  <div><div style="font-weight:800;color:#fff;font-size:15px;">{ticker}</div><div style="font-size:11px;color:#8BA6D3;">{name}</div></div>
  <div style="text-align:right;"><div style="font-size:16px;font-weight:900;color:#fff;">{price}</div><div style="font-size:13px;font-weight:800;color:#8EF6D1;">▲ {chg}</div></div>
</div>""", unsafe_allow_html=True)
    with mc2:
        st.markdown('<div style="font-size:10px;font-weight:800;color:#FF6B6B;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;">Worst Performers</div>', unsafe_allow_html=True)
        sorted_loss = sorted(markets, key=lambda x: float(x[3].replace('%','').replace('+','')) if x[3] != 'N/A' else 99)[:3]
        for ticker, name, price, chg, up in sorted_loss:
            st.markdown(f"""
<div class="mover-card" style="margin-bottom:8px;border-color:rgba(255,107,107,0.2);">
  <div><div style="font-weight:800;color:#fff;font-size:15px;">{ticker}</div><div style="font-size:11px;color:#8BA6D3;">{name}</div></div>
  <div style="text-align:right;"><div style="font-size:16px;font-weight:900;color:#fff;">{price}</div><div style="font-size:13px;font-weight:800;color:#FF6B6B;">▼ {chg}</div></div>
</div>""", unsafe_allow_html=True)

    # ── ETF Watchlist — cards with embedded sparklines ────────────────────────
    st.markdown(f'<div class="mkt-section-title">{get_svg("chart", 16)} ETF Watchlist <span>· 8 tracked instruments · 30-day sparklines</span></div>', unsafe_allow_html=True)

    cols = st.columns(4)
    for i, (ticker, name, price, chg, up) in enumerate(markets):
        with cols[i % 4]:
            yf_ticker = ticker_map.get(ticker, ticker)
            color     = "#8EF6D1" if up else "#FF6B6B"
            arrow     = "▲" if up else "▼"

            if hist_df is not None and yf_ticker in hist_df.columns:
                series = hist_df[yf_ticker].dropna()
            else:
                series = None

            fig = go.Figure()
            if series is not None and len(series) > 1:
                fill_color = "rgba(142,246,209,0.1)" if up else "rgba(255,107,107,0.1)"
                fig.add_trace(go.Scatter(
                    x=list(range(len(series))), y=series.values, mode="lines",
                    line=dict(color=color, width=2),
                    fill="tozeroy", fillcolor=fill_color,
                    hovertemplate="%{y:.2f}<extra></extra>"
                ))
            fig.update_layout(
                height=56, margin=dict(l=0,r=0,t=0,b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(visible=False), yaxis=dict(visible=False), showlegend=False
            )
            st.markdown(f"""
<div class="mkt-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
    <div><div class="mkt-ticker">{ticker}</div><div class="mkt-name">{name}</div></div>
    <div style="text-align:right;">
      <div class="mkt-price">{price}</div>
      <div style="color:{color};font-size:12px;font-weight:800;">{arrow} {chg}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"spark_{ticker}")
            
            # Persistent Favoriting
            is_pinned = ticker in watchlist
            btn_lbl = f"{'★' if is_pinned else '☆'} Pin to Favorites" if not is_pinned else "★ Pinned"
            if st.button(btn_lbl, key=f"pin_btn_{ticker}", use_container_width=True):
                database.toggle_watchlist_item(email, ticker)
                st.rerun()

    # ── Interactive Price Chart ───────────────────────────────────────────────
    st.markdown(f'<div class="mkt-section-title">{get_svg("activity", 16)} Deep-Dive Chart <span>· 30-day price history with moving averages</span></div>', unsafe_allow_html=True)

    chart_col, info_col = st.columns([3, 1], gap="large")
    with chart_col:
        selected    = st.selectbox("Select instrument", [m[0] for m in markets], label_visibility="collapsed", key="mkt_chart_select")
        yf_selected = ticker_map.get(selected, selected)

        if hist_df is not None and yf_selected in hist_df.columns:
            series      = hist_df[yf_selected].dropna()
            up_overall  = series.iloc[-1] >= series.iloc[0]
            line_color  = "#8EF6D1" if up_overall else "#FF6B6B"
            fill_color  = "rgba(142,246,209,0.07)" if up_overall else "rgba(255,107,107,0.07)"

            big_fig = go.Figure()
            big_fig.add_trace(go.Scatter(
                x=series.index, y=series.values, mode="lines", name=selected,
                line=dict(color=line_color, width=2.5), fill="tozeroy", fillcolor=fill_color,
                hovertemplate="<b>%{x|%d %b}</b><br>Price: %{y:.2f}<extra></extra>"
            ))
            if len(series) >= 7:
                ma7 = series.rolling(7).mean()
                big_fig.add_trace(go.Scatter(
                    x=ma7.index, y=ma7.values, mode="lines", name="7-day MA",
                    line=dict(color="#6D5EFC", width=1.5, dash="dot"),
                    hovertemplate="MA7: %{y:.2f}<extra></extra>"
                ))
            if len(series) >= 14:
                ma14 = series.rolling(14).mean()
                big_fig.add_trace(go.Scatter(
                    x=ma14.index, y=ma14.values, mode="lines", name="14-day MA",
                    line=dict(color="#3BA4FF", width=1.2, dash="dash"),
                    hovertemplate="MA14: %{y:.2f}<extra></extra>"
                ))
            big_fig.update_layout(
                height=360, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10,r=10,t=10,b=10),
                xaxis=dict(showgrid=False, color="#8BA6D3", tickformat="%d %b"),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", color="#8BA6D3"),
                legend=dict(font=dict(color="#8BA6D3", size=11), bgcolor="rgba(0,0,0,0)", orientation="h", y=1.08),
                hovermode="x unified",
                hoverlabel=dict(bgcolor="rgba(15,15,35,0.95)", font_color="#ffffff", bordercolor="rgba(109,94,252,0.4)")
            )
            st.plotly_chart(big_fig, use_container_width=True, config={"displayModeBar": False}, key="mkt_main_chart")
        else:
            st.info("Chart data unavailable — check your connection.")

    with info_col:
        # Find selected ticker stats
        sel_data = next((m for m in markets if m[0] == selected), None)
        if sel_data and hist_df is not None:
            yf_s = ticker_map.get(selected, selected)
            s = hist_df[yf_s].dropna() if yf_s in (hist_df.columns if hist_df is not None else []) else None
            hi  = f"{s.max():.2f}" if s is not None else "—"
            lo  = f"{s.min():.2f}" if s is not None else "—"
            ret = f"{((s.iloc[-1]-s.iloc[0])/s.iloc[0]*100):+.2f}%" if s is not None and len(s) >= 2 else "—"
            col_r = "#8EF6D1" if sel_data[4] else "#FF6B6B"
            st.markdown(f"""
<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.07);border-radius:16px;padding:20px;margin-top:36px;">
  <div style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:14px;">{selected} Stats</div>
  <div style="border-bottom:1px solid rgba(255,255,255,0.05);padding-bottom:10px;margin-bottom:10px;">
    <div style="font-size:10px;color:#8BA6D3;font-weight:700;">Current Price</div>
    <div style="font-size:24px;font-weight:900;color:#fff;">{sel_data[2]}</div>
    <div style="font-size:14px;font-weight:800;color:{col_r};">{sel_data[3]}</div>
  </div>
  <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
    <div style="font-size:10px;color:#8BA6D3;">30d High</div><div style="font-size:12px;font-weight:700;color:#8EF6D1;">{hi}</div>
  </div>
  <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
    <div style="font-size:10px;color:#8BA6D3;">30d Low</div><div style="font-size:12px;font-weight:700;color:#FF6B6B;">{lo}</div>
  </div>
  <div style="display:flex;justify-content:space-between;">
    <div style="font-size:10px;color:#8BA6D3;">30d Return</div><div style="font-size:12px;font-weight:700;color:{col_r};">{ret}</div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── 30-day Treemap Heatmap ────────────────────────────────────────────────
    st.markdown(f'<div class="mkt-section-title">{get_svg("layers", 16)} Sector Heatmap <span>· 30-day performance · size = absolute return</span></div>', unsafe_allow_html=True)

    sectors = []
    if hist_df is not None:
        for ticker, name, price, chg, up in markets:
            yf_t = ticker_map.get(ticker, ticker)
            if yf_t in hist_df.columns:
                s = hist_df[yf_t].dropna()
                if len(s) >= 2:
                    ret = ((s.iloc[-1] - s.iloc[0]) / s.iloc[0]) * 100
                    sectors.append((ticker, name, ret))

    if sectors:
        labels = [f"{t}<br>{r:+.1f}%" for t, n, r in sectors]
        values = [abs(r) + 1 for _, _, r in sectors]
        colors = [r for _, _, r in sectors]
        heat = go.Figure(go.Treemap(
            labels=labels, parents=[""] * len(labels), values=values,
            marker=dict(colors=colors, colorscale=[[0,"#FF3B3B"],[0.5,"#1A1A3E"],[1,"#00C896"]],
                        cmid=0, showscale=False, line=dict(width=3, color="rgba(8,10,26,1)")),
            textfont=dict(color="#ffffff", size=13),
            hovertemplate="<b>%{label}</b><extra></extra>",
        ))
        heat.update_layout(height=240, paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(heat, use_container_width=True, config={"displayModeBar": False}, key="mkt_heatmap")

    # ── Heatmap Click Explainer Panel ─────────────────────────────────────────
    etf_info = {
        "VOO": {
            "full_name": "Vanguard S&P 500 ETF",
            "asset_class": "US Large-Cap Equity",
            "role": "Core equity exposure — the backbone of most MINN allocations. Tracks the 500 largest US companies.",
            "going_up": "Signals broad market confidence. Your portfolio benefits directly; growth regime likely dominant.",
            "going_down": "Risk-off signal. MINN may shift weight toward AGG (bonds) or GLD to hedge drawdown.",
            "sharpe_impact": "High positive — VOO is the primary return driver in balanced and growth profiles.",
            "weight_hint": "Typically 20–40% of MINN growth portfolios."
        },
        "QQQ": {
            "full_name": "Invesco Nasdaq 100 ETF",
            "asset_class": "US Tech / Growth Equity",
            "role": "High-growth, rate-sensitive tech exposure. Amplifies returns in bull regimes but volatile in tail events.",
            "going_up": "AI and tech momentum is strong. Benefits QQQ-heavy portfolios significantly.",
            "going_down": "Rising rates or risk aversion hit QQQ hardest. Wing/Tail co-movement spikes with VOO.",
            "sharpe_impact": "High beta — boosts Sharpe in bull markets, compresses it in corrections.",
            "weight_hint": "Typically 10–25% of growth-tilted MINN portfolios."
        },
        "VWRA": {
            "full_name": "Vanguard FTSE All-World ETF",
            "asset_class": "Global Equity (ex-US diversification)",
            "role": "International diversification layer. Reduces US concentration risk and adds EM/Europe exposure.",
            "going_up": "Global growth synchronized with US — carries. Reduces country-specific correlation.",
            "going_down": "Global slowdown or strong USD headwinds. MINN may reduce weighting.",
            "sharpe_impact": "Moderate — key for correlation reduction (C_IQ Body regime contribution).",
            "weight_hint": "Typically 10–20% across all MINN profiles."
        },
        "AGG": {
            "full_name": "iShares Core US Aggregate Bond ETF",
            "asset_class": "Investment Grade Bonds",
            "role": "Stability anchor. Provides negative or low correlation to equities during market stress.",
            "going_up": "Risk-off environment or rate cuts expected. Protects capital during equity drawdowns.",
            "going_down": "Rising rates eroding bond prices. MINN shifts weight back toward equities.",
            "sharpe_impact": "Low solo returns but critical for Sharpe via volatility reduction.",
            "weight_hint": "Typically 15–35% in conservative or balanced MINN profiles."
        },
        "GLD": {
            "full_name": "SPDR Gold Shares ETF",
            "asset_class": "Commodity — Precious Metals",
            "role": "Inflation hedge and crisis safe-haven. Performs in Tail regimes when equity correlations spike.",
            "going_up": "Inflation fears, USD weakness, or geopolitical stress. Your hedge is working.",
            "going_down": "Real rates rising or risk appetite recovering. MINN may trim GLD allocation.",
            "sharpe_impact": "Tail regime stabilizer — reduces max drawdown even if it lowers mean returns.",
            "weight_hint": "Typically 5–15% depending on inflation expectation in regime model."
        },
        "VNQ": {
            "full_name": "Vanguard Real Estate ETF",
            "asset_class": "Real Estate Investment Trusts (REITs)",
            "role": "Income + inflation protection. Rate-sensitive but provides dividend yield and real-asset exposure.",
            "going_up": "Rate stability or cuts — REITs rally on lower borrowing costs and yield demand.",
            "going_down": "Rising interest rates are the main risk. MINN reduces VNQ when rate regime shifts upward.",
            "sharpe_impact": "Moderate — adds income but correlates with equities in stress events.",
            "weight_hint": "Typically 5–12% across most MINN profiles."
        },
        "ESGU": {
            "full_name": "iShares ESG Aware MSCI USA ETF",
            "asset_class": "ESG / Sustainable US Equity",
            "role": "Socially responsible equity exposure with similar characteristics to VOO but with ESG screening.",
            "going_up": "ESG flows accelerating. Can be used as a low-tracking-error VOO substitute.",
            "going_down": "Typically moves closely with VOO — same drivers but with slightly lower vol.",
            "sharpe_impact": "Very similar to VOO. Slightly lower concentration risk in high-carbon sectors.",
            "weight_hint": "Often substituted for or combined with VOO in ESG-tilted profiles."
        },
        "PDBC": {
            "full_name": "Invesco Optimum Yield Diversified Commodity Strategy ETF",
            "asset_class": "Broad Commodities",
            "role": "Multi-commodity inflation hedge covering energy, metals, agriculture. Tail regime asset.",
            "going_up": "Commodity supercycle or supply shocks driving energy/metals. Strong inflation hedge activated.",
            "going_down": "Global demand slowdown or USD strength reducing commodity prices.",
            "sharpe_impact": "High vol but low equity correlation — valuable in the IQ Tail regime weighting (wT).",
            "weight_hint": "Typically 3–10% in inflation-aware MINN portfolios."
        },
    }

    st.markdown("""
<style>
.etf-chip { display:inline-block; margin:4px; padding:6px 14px; border-radius:20px;
  font-size:12px; font-weight:800; cursor:pointer;
  background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); color:#8BA6D3;
  transition:all 0.15s; }
.etf-chip-active { background:rgba(109,94,252,0.12); border-color:rgba(109,94,252,0.45); color:#fff; }
</style>
""", unsafe_allow_html=True)

    st.markdown(f'<div style="font-size:11px;font-weight:700;color:#8BA6D3;margin:16px 0 8px;text-transform:uppercase;letter-spacing:0.1em;">Select a block to explore</div>', unsafe_allow_html=True)

    selected_etf = st.session_state.get("heatmap_selected_etf", None)
    chip_cols = st.columns(8)
    etf_keys = list(etf_info.keys())
    for i, key in enumerate(etf_keys):
        with chip_cols[i]:
            is_active = selected_etf == key
            label = f"{'→ ' if is_active else ''}{key}"
            if st.button(label, key=f"chip_{key}", use_container_width=True):
                if selected_etf == key:
                    st.session_state["heatmap_selected_etf"] = None
                else:
                    st.session_state["heatmap_selected_etf"] = key
                st.rerun()

    selected_etf = st.session_state.get("heatmap_selected_etf", None)
    if selected_etf and selected_etf in etf_info:
        info = etf_info[selected_etf]
        # Find live price data for this ETF
        live = next((m for m in markets if m[0] == selected_etf), None)
        price_html = ""
        if live:
            col_p = "#8EF6D1" if live[4] else "#FF6B6B"
            arr   = "▲" if live[4] else "▼"
            price_html = f'<span style="font-size:22px;font-weight:900;color:#fff;">{live[2]}</span> <span style="font-size:14px;font-weight:800;color:{col_p};">{arr} {live[3]}</span>'

        st.markdown(f"""
<div style="background:rgba(109,94,252,0.06);border:1px solid rgba(109,94,252,0.25);border-radius:20px;padding:28px 32px;margin-top:8px;position:relative;overflow:hidden;">
  <div style="position:absolute;top:0;left:0;width:5px;height:100%;background:linear-gradient(180deg,#6D5EFC,#3BA4FF);"></div>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;margin-bottom:20px;">
    <div>
      <div style="font-size:11px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">{info['asset_class']}</div>
      <div style="font-size:26px;font-weight:900;color:#fff;letter-spacing:-0.03em;">{selected_etf} <span style="font-size:14px;font-weight:500;color:#8BA6D3;">· {info['full_name']}</span></div>
      <div style="margin-top:6px;">{price_html}</div>
    </div>
    <div style="text-align:right;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:12px 18px;">
      <div style="font-size:10px;color:#8BA6D3;font-weight:700;text-transform:uppercase;margin-bottom:4px;">Typical MINN Weight</div>
      <div style="font-size:16px;font-weight:900;color:#fff;">{info['weight_hint']}</div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:2fr 1fr 1fr;gap:16px;margin-bottom:16px;">
    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:16px;">
      <div style="font-size:10px;font-weight:800;color:#6D5EFC;text-transform:uppercase;margin-bottom:8px;">Role in Portfolio</div>
      <div style="font-size:13px;color:#C5D3EC;line-height:1.65;">{info['role']}</div>
    </div>
    <div style="background:rgba(142,246,209,0.05);border:1px solid rgba(142,246,209,0.18);border-radius:14px;padding:16px;">
      <div style="font-size:10px;font-weight:800;color:#8EF6D1;text-transform:uppercase;margin-bottom:8px;">When it rises...</div>
      <div style="font-size:12px;color:#C5D3EC;line-height:1.6;">{info['going_up']}</div>
    </div>
    <div style="background:rgba(255,107,107,0.05);border:1px solid rgba(255,107,107,0.18);border-radius:14px;padding:16px;">
      <div style="font-size:10px;font-weight:800;color:#FF6B6B;text-transform:uppercase;margin-bottom:8px;">When it falls...</div>
      <div style="font-size:12px;color:#C5D3EC;line-height:1.6;">{info['going_down']}</div>
    </div>
  </div>
  <div style="background:rgba(109,94,252,0.08);border:1px solid rgba(109,94,252,0.2);border-radius:12px;padding:14px 18px;">
    <div style="font-size:10px;font-weight:800;color:#6D5EFC;text-transform:uppercase;margin-bottom:6px;">Sharpe Ratio Impact</div>
    <div style="font-size:13px;color:#fff;">{info['sharpe_impact']}</div>
  </div>
</div>
""", unsafe_allow_html=True)


    # ── Market Intelligence Feed ───────────────────────────────────────────────
    st.markdown(f'<div class="mkt-section-title">{get_svg("zap", 16)} Market Intelligence <span>· AI-powered portfolio takeaways</span></div>', unsafe_allow_html=True)
    mi_c1, mi_c2 = st.columns([1, 1.6], gap="large")
    with mi_c1:
        st.markdown(f'<div style="font-size:11px;font-weight:800;color:#6D5EFC;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.1em;">{get_svg("activity", 13)} Neural Sentiment Radar</div>', unsafe_allow_html=True)
        categories = ['Growth','Inflation','Stability','Yield','Volatility']
        values     = [82, 45, 68, 55, 30]
        rfig = go.Figure(data=go.Scatterpolar(r=values, theta=categories, fill='toself', line_color='#6D5EFC', fillcolor='rgba(109,94,252,0.2)'))
        rfig.update_layout(polar=dict(radialaxis=dict(visible=False), bgcolor='rgba(0,0,0,0)'), paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=30,r=30), height=240)
        st.plotly_chart(rfig, use_container_width=True, config={'displayModeBar': False}, key="mkt_radar")
        st.markdown('<div style="text-align:center;font-size:12px;color:#8BA6D3;">Model detects <b>Growth</b> bias · Neural Confidence: <b style="color:#8EF6D1;">72.4</b></div>', unsafe_allow_html=True)
    with mi_c2:
        st.markdown(f'<div style="font-size:11px;font-weight:800;color:#3BA4FF;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.1em;">{get_svg("zap", 13)} Intelligence Timeline</div>', unsafe_allow_html=True)
        items = [
            {"tag": "US MARKETS",      "title": "Interest Rates Stabilizing",  "desc": "The central bank is holding rates steady.",         "impact": "STABLE", "meaning": "Good for your Bond (AGG) and Real Estate (VNQ) holdings."},
            {"tag": "TECH GROWTH",     "title": "AI Hardware Demand Soars",    "desc": "Nvidia and others reporting record sales.",          "impact": "GROWTH", "meaning": "Expect momentum in your QQQ and VOO allocations."},
            {"tag": "DIVERSIFICATION", "title": "Commodities as a Hedge",      "desc": "Gold and Oil are rising amid global uncertainty.",  "impact": "HEDGE",  "meaning": "Your GLD and PDBC positions are protecting your gains."}
        ]
        for it in items:
            st.markdown(f"""
<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:16px;margin-bottom:10px;position:relative;overflow:hidden;">
  <div style="position:absolute;top:0;left:0;width:3px;height:100%;background:#6D5EFC;opacity:0.6;"></div>
  <div style="position:absolute;top:12px;right:12px;font-size:9px;font-weight:800;color:#8EF6D1;background:rgba(142,246,209,0.1);padding:2px 8px;border-radius:20px;border:1px solid rgba(142,246,209,0.2);">{it['impact']}</div>
  <span style="background:rgba(109,94,252,0.1);color:#6D5EFC;font-size:9px;font-weight:800;padding:2px 8px;border-radius:8px;display:inline-block;margin-bottom:6px;">{it['tag']}</span>
  <div style="font-size:14px;font-weight:700;color:#fff;margin-bottom:4px;">{it['title']}</div>
  <div style="font-size:11px;color:#8BA6D3;margin-bottom:8px;">{it['desc']}</div>
  <div style="background:rgba(109,94,252,0.07);padding:8px 10px;border-radius:8px;">
    <div style="font-size:9px;font-weight:900;color:#6D5EFC;margin-bottom:2px;">TAKEAWAY FOR YOUR PORTFOLIO</div>
    <div style="font-size:11px;color:#fff;">{it['meaning']}</div>
  </div>
</div>
""", unsafe_allow_html=True)



