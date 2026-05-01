"""
ui/ai_engine.py
===============
Survey questions definition and AI explanation engine.

  - QUESTIONS          : 10-question investor risk survey
  - get_ai_explanation : calls Claude 3.5 Sonnet and returns a
                         plain-English investment strategy note.
                         Falls back gracefully to a rich rule-based note if the
                         API key is absent or the call fails — never surfaces
                         "ERROR" to the user.
"""
from __future__ import annotations

import streamlit as st

# ── Survey questions ──────────────────────────────────────────────────────────

QUESTIONS = [
    {
        "id": "risk_tolerance",
        "text": "How comfortable are you with your investments fluctuating in value?",
        "subtitle": "Risk tolerance shapes the volatility your portfolio can absorb.",
        "options": [
            {"label": "Conservative", "value": 1,
             "desc": "I prefer stability. Losing money worries me significantly."},
            {"label": "Moderate", "value": 2,
             "desc": "Some ups and downs are fine as long as the long-term trend is positive."},
            {"label": "Aggressive", "value": 3,
             "desc": "I accept significant short-term swings in pursuit of higher returns."},
        ],
    },
    {
        "id": "investment_horizon",
        "text": "How long do you plan to keep your money invested?",
        "subtitle": "Longer horizons allow more time to recover from market downturns.",
        "options": [
            {"label": "Short (< 3 years)",  "value": 1, "desc": "I may need this money soon."},
            {"label": "Medium (3–10 years)", "value": 2, "desc": "I'm saving for a mid-term goal."},
            {"label": "Long (10+ years)",    "value": 3, "desc": "This is long-term wealth building."},
        ],
    },
    {
        "id": "diversification",
        "text": "How broadly do you want your portfolio spread across asset classes?",
        "subtitle": "Diversification balances risk across equities, bonds, commodities and more.",
        "options": [
            {"label": "Concentrated", "value": 1, "desc": "Focus on a few high-conviction assets."},
            {"label": "Balanced",     "value": 2, "desc": "A mix across several asset types."},
            {"label": "Broad",        "value": 3,
             "desc": "Wide exposure: multiple sectors, regions and asset types."},
        ],
    },
    {
        "id": "esg_priority",
        "text": "How important are ethical / ESG factors to your investment decisions?",
        "subtitle": "ESG screens can exclude industries like fossil fuels, tobacco or weapons.",
        "options": [
            {"label": "Not important",       "value": 1,
             "desc": "Pure returns matter most — I have no ethical restrictions."},
            {"label": "Somewhat important",  "value": 2,
             "desc": "I prefer some ESG exposure but without strict exclusions."},
            {"label": "Very important",      "value": 3,
             "desc": "Strong ESG alignment is a core requirement."},
        ],
    },
    {
        "id": "sector_preference",
        "text": "Do you have strong views on specific sectors or industries?",
        "subtitle": "Sector tilts can boost returns in favoured areas but increase concentration risk.",
        "options": [
            {"label": "No preference", "value": 1, "desc": "Broad exposure is fine."},
            {"label": "Some views",    "value": 2,
             "desc": "I prefer emphasis on or avoidance of a few sectors."},
            {"label": "Strong views",  "value": 3,
             "desc": "I want specific sectors included or excluded."},
        ],
    },
    {
        "id": "turnover_preference",
        "text": "How often are you comfortable with portfolio rebalancing?",
        "subtitle": "Higher turnover captures short-term opportunities but incurs more costs.",
        "options": [
            {"label": "Minimal (set-and-hold)", "value": 1,
             "desc": "I prefer a stable, long-term strategy."},
            {"label": "Occasional",             "value": 2,
             "desc": "Rebalance when market conditions warrant it."},
            {"label": "Frequent",               "value": 3,
             "desc": "Active rebalancing to stay ahead of markets."},
        ],
    },
    {
        "id": "income_vs_growth",
        "text": "Do you prioritise income (dividends) or capital growth?",
        "subtitle": "This shapes the balance between income-generating and growth-oriented assets.",
        "options": [
            {"label": "Income",          "value": 1, "desc": "Regular dividend income is important to me."},
            {"label": "Balanced",        "value": 2, "desc": "A mix of income and growth."},
            {"label": "Growth",          "value": 3,
             "desc": "I want maximum capital appreciation; I don't need income now."},
        ],
    },
    {
        "id": "loss_reaction",
        "text": "If your portfolio dropped 20% in a month, what would you do?",
        "subtitle": "Your reaction to losses reveals your true risk appetite.",
        "options": [
            {"label": "Sell to protect capital", "value": 1,
             "desc": "I'd reduce exposure to stop further losses."},
            {"label": "Hold and wait",           "value": 2,
             "desc": "I'd stay the course and trust the long-term plan."},
            {"label": "Buy more",                "value": 3,
             "desc": "I'd see it as a buying opportunity and invest more."},
        ],
    },
    {
        "id": "investment_experience",
        "text": "How would you describe your investing experience?",
        "subtitle": "Experience level helps calibrate how complex your portfolio strategy should be.",
        "options": [
            {"label": "Beginner",      "value": 1, "desc": "I'm new to investing."},
            {"label": "Intermediate",  "value": 2, "desc": "I have some experience with markets."},
            {"label": "Experienced",   "value": 3,
             "desc": "I've actively managed investments for several years."},
        ],
    },
    {
        "id": "liquidity_needs",
        "text": "How likely are you to need emergency access to this money?",
        "subtitle": "High liquidity needs favour more cash-like and easily redeemable assets.",
        "options": [
            {"label": "Very likely",   "value": 1,
             "desc": "I might need this money at short notice."},
            {"label": "Possible",      "value": 2,
             "desc": "I could need it but have other savings as a buffer."},
            {"label": "Very unlikely", "value": 3,
             "desc": "This money is fully ring-fenced for investing."},
        ],
    },
]

# ── Profile metadata ──────────────────────────────────────────────────────────

PROFILE_META = {
    1: {
        "name": "Capital Preservation",
        "tagline": "Safety-first, low volatility, income-oriented",
        "assets": "Short-duration bonds, money-market funds, investment-grade corporate debt, dividend equities",
        "expected_return": "3–5% p.a.",
        "max_drawdown": "~5%",
        "suitable_for": "investors with short horizons or low risk tolerance",
    },
    2: {
        "name": "Balanced Growth",
        "tagline": "Moderate risk, diversified across equities and bonds",
        "assets": "Global equities (60%), investment-grade bonds (30%), commodities/REITs (10%)",
        "expected_return": "6–8% p.a.",
        "max_drawdown": "~15%",
        "suitable_for": "medium-horizon investors seeking steady compound growth",
    },
    3: {
        "name": "High-Alpha Equity",
        "tagline": "Aggressive growth, sector-concentrated, high turnover",
        "assets": "US large-cap growth, tech/healthcare sector ETFs, small-cap equities, momentum factors",
        "expected_return": "9–13% p.a.",
        "max_drawdown": "~30%",
        "suitable_for": "experienced investors with long horizons and high loss tolerance",
    },
    4: {
        "name": "ESG Impact",
        "tagline": "Broad diversification with strong ethical screening",
        "assets": "ESG-screened global equities, green bonds, clean-energy ETFs, sustainable REITs",
        "expected_return": "6–9% p.a.",
        "max_drawdown": "~18%",
        "suitable_for": "values-driven investors who want market-rate returns with ethical alignment",
    },
    5: {
        "name": "Thematic Concentrated",
        "tagline": "High-conviction sector bets, lower diversification",
        "assets": "Technology, biotech, emerging markets, thematic megatrend ETFs",
        "expected_return": "8–14% p.a.",
        "max_drawdown": "~35%",
        "suitable_for": "investors with strong sector convictions and high risk appetite",
    },
    6: {
        "name": "Risk Parity",
        "tagline": "Systematic, broadly diversified, volatility-balanced",
        "assets": "Global equities, long-duration bonds, gold, commodities — weighted by inverse volatility",
        "expected_return": "5–8% p.a.",
        "max_drawdown": "~12%",
        "suitable_for": "systematic investors who want smooth returns across market regimes",
    },
}

# ── Claude API call ───────────────────────────────────────────────────────────

def _build_prompt(answers: dict, portfolio_stats: dict, iq_params: dict | None = None) -> str:
    """Build a prompt for Claude using the user's live computed portfolio data."""

    answer_lines = []
    for q in QUESTIONS:
        val = answers.get(q["id"])
        if val is not None:
            for opt in q["options"]:
                if opt["value"] == val:
                    answer_lines.append(f"  \u2022 {q['text']}\n    \u2192 {opt['label']}: {opt['desc']}")
                    break
    answers_text = "\n".join(answer_lines) if answer_lines else "  (no answers recorded)"

    exp_ret  = portfolio_stats.get("expected_annual_return", 7.0)
    vol      = portfolio_stats.get("expected_volatility", 10.0)
    sharpe   = portfolio_stats.get("sharpe_ratio", 0.6)
    risk_cat = portfolio_stats.get("risk_category", "balanced")
    assets   = portfolio_stats.get("top_assets", [])
    assets_text = ", ".join(f"{a} ({w:.0f}%)" for a, w in assets[:6]) if assets else "a diversified mix of assets"

    iq_text = ""
    if iq_params:
        iq_text = "\n\nDeepAtomicIQ model parameters:\n" + "\n".join(
            f"  \u2022 {k}: {v}" for k, v in iq_params.items() if v is not None
        )

    return f"""You are DeepAtomicIQ, an expert AI investment strategist for LEM StratIQ.

A user has completed their investor risk-profiling survey. Our AI engine has computed a personalised {risk_cat} portfolio with these LIVE characteristics:

  \u2022 Expected annual return: {exp_ret:.1f}%
  \u2022 Annual volatility: {vol:.1f}%
  \u2022 Sharpe ratio: {sharpe:.2f}
  \u2022 Top holdings: {assets_text}

User survey answers:
{answers_text}{iq_text}

Write a personalised, plain-English investment strategy note. Use ONLY the live figures above. Do NOT invent profile names or reference internal profile numbers (e.g. "Profile 2"). Structure it as:

1. **Why this portfolio fits you** (2-3 sentences linking their answers to the computed portfolio)
2. **What we invest in** (mention the top holdings and why they suit this person)
3. **What to expect** (use the EXACT figures: {exp_ret:.1f}% return, {vol:.1f}% volatility, Sharpe {sharpe:.2f} - explain in plain English)
4. **Key risks to be aware of** (2-3 specific risks based on the actual holdings)
5. **Our recommendation** (1-2 actionable sentences)

Tone: professional but warm, jargon-free, UK English. Do NOT say "as an AI" or "I cannot provide financial advice". Keep under 450 words."""

def get_ai_explanation(
    answers: dict,
    portfolio_stats: dict,
    iq_params: dict | None = None,
) -> tuple[str, bool]:
    """
    Returns (explanation_text, used_claude: bool).
    portfolio_stats: live computed dict with keys:
      expected_annual_return, expected_volatility, sharpe_ratio,
      risk_category, top_assets [(name, weight%), ...]
    """
    try:
        import anthropic as _anthropic
        import os as _os
        _key = _os.environ.get("ANTHROPIC_API_KEY", "")
        client = _anthropic.Anthropic(api_key=_key) if _key else None
    except Exception:
        client = None

    if client:
        try:
            prompt = _build_prompt(answers, portfolio_stats, iq_params)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip(), True
        except Exception as exc:
            print(f"[ai_engine] Claude call failed: {exc}")

    return _local_explanation(answers, portfolio_stats), False

# ── Local fallback (no API key needed) ───────────────────────────────────────

def _local_explanation(answers: dict, portfolio_stats: dict) -> str:
    """Fallback explanation using live portfolio stats — no hardcoded profile names."""
    exp_ret  = portfolio_stats.get("expected_annual_return", 7.0)
    vol      = portfolio_stats.get("expected_volatility", 10.0)
    sharpe   = portfolio_stats.get("sharpe_ratio", 0.6)
    risk_cat = portfolio_stats.get("risk_category", "balanced")
    assets   = portfolio_stats.get("top_assets", [])
    assets_text = (", ".join(f"{a} ({w:.0f}%)" for a, w in assets[:5])
                   if assets else "a diversified selection of global assets")

    risk_val    = answers.get("risk_tolerance", 2)
    horizon_val = answers.get("investment_horizon", 2)
    esg_val     = answers.get("esg_priority", 1)
    income_val  = answers.get("income_vs_growth", 2)

    risk_label    = {1: "conservative", 2: "moderate", 3: "growth-oriented"}.get(risk_val, "moderate")
    horizon_label = {1: "short", 2: "medium", 3: "long"}.get(horizon_val, "medium")
    income_label  = {1: "income-focused", 2: "balanced income/growth", 3: "pure growth"}.get(income_val, "balanced")

    esg_note = (
        " With strong ESG alignment, every holding is screened against environmental, social and governance criteria."
        if esg_val == 3 else
        " We apply light ESG screening, tilting away from the most controversial industries."
        if esg_val == 2 else ""
    )

    limited = " limited" if horizon_val == 1 else ""
    lumpsum = (
        "Start with a lump-sum investment and consider topping up monthly via a direct debit to benefit from pound-cost averaging."
        if horizon_val >= 2 else
        "Given your shorter horizon, consider phasing your investment over 3-6 months to reduce timing risk."
    )

    return f"""**Why this portfolio fits you**

Based on your {risk_label} risk tolerance and {horizon_label} investment horizon, our AI engine has built you a personalised {risk_cat} portfolio targeting **{exp_ret:.1f}% annual growth** with a Sharpe ratio of **{sharpe:.2f}**.{esg_note} Your {income_label} preference shapes the income/growth split.

**What we invest in**

Your portfolio is spread across: {assets_text}. Each position is weighted to maximise risk-adjusted returns for your specific circumstances, rebalanced systematically as markets move.

**What to expect**

The engine projects **{exp_ret:.1f}% annual return** with typical year-to-year swings of around **\u00b1{vol:.1f}%**. The Sharpe ratio of {sharpe:.2f} means you're receiving {sharpe:.2f} units of return for every unit of risk (above 0.5 is solid). For a {horizon_label}-horizon investor, there is{limited} time to ride out short-term dips.

**Key risks to be aware of**

- **Market risk:** Global markets can fall sharply during recessions or geopolitical shocks.
- **Inflation risk:** If inflation exceeds portfolio returns, real purchasing power can erode.
- **Volatility risk:** With \u00b1{vol:.1f}% annual swings expected, some years will feel uncomfortable — staying invested is key.

**Our recommendation**

{lumpsum} Review your profile annually or whenever your financial circumstances change significantly."""


def render_actionable_advice(answers: dict, profile_num: int, iq_params: dict | None = None):
    """Render the Claude AI Investment Strategy section in Streamlit."""
    with st.spinner("Generating your personalised investment strategy…"):
        explanation, used_claude = get_ai_explanation(answers, profile_num, iq_params)

    source_label = "Claude 3.5 Sonnet" if used_claude else "DeepAtomicIQ Strategy Engine"
    source_color = "#6D5EFC" if used_claude else "#3BA4FF"

    st.markdown(
        f"""
        <div style="
            background: rgba(109,94,252,0.06);
            border: 1px solid rgba(109,94,252,0.25);
            border-left: 4px solid {source_color};
            border-radius: 14px;
            padding: 24px 28px;
            margin: 24px 0;
        ">
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:16px;">
            <div style="
                width:36px; height:36px; border-radius:10px;
                background: linear-gradient(135deg, #6D5EFC, #3BA4FF);
                display:flex; align-items:center; justify-content:center;
                font-size:18px;
            ">{"🤖" if used_claude else "🧠"}</div>
            <div>
              <div style="font-size:15px; font-weight:700; color:#ffffff;">
                {"Claude AI Investment Strategy" if used_claude else "DeepAtomicIQ Investment Strategy"}
              </div>
              <div style="font-size:11px; color:rgba(255,255,255,0.45); margin-top:2px;">
                Powered by {source_label}
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render the markdown body (Claude returns markdown; local fallback also uses markdown)
    st.markdown(explanation)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺  Refresh Strategy Note", key="refresh_ai_note"):
            # Clear any cached explanation and rerun
            for k in list(st.session_state.keys()):
                if k.startswith("ai_explanation"):
                    del st.session_state[k]
            st.rerun()
    with col2:
        st.button("✉  Email Results", key="email_ai_note")


# ── Legacy shim kept for any callers that import the old name ─────────────────

def generate_advanced_explanation(answers: dict, profile_num: int) -> str:
    """Backwards-compatible wrapper — returns the local fallback text."""
    return _local_explanation(answers, profile_num)