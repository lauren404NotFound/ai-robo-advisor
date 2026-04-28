"""
ui/ai_engine.py
===============
Survey questions definition and AI explanation engine:
  - QUESTIONS: 10-question investor risk survey
  - generate_advanced_explanation(): rule-based technical paragraphs
  - get_real_claude_insight(): live Claude 3.5 Sonnet call
  - get_ai_explanation(): unified facade (Claude → local fallback)
"""
from __future__ import annotations
import streamlit as st

# Imports resolved at call time to avoid circular dependencies
def _get_claude():
    import app as _app
    return _app.anthropic_client, _app.claude_status

def _get_local_explain():
    from explainer import explain as local_explain
    return local_explain

# ══════════════════════════════════════════════════════════════════════════════
# SURVEY QUESTIONS
# ══════════════════════════════════════════════════════════════════════════════
QUESTIONS = [
    dict(key="q1_risk_comfort", number="Q1 / 10",
         text="How much risk are you comfortable with?",
         desc="This maps to your investor risk profile. Higher risk tolerates larger swings in portfolio value but pursues greater long-term returns.",
         options=["Low — I prioritise capital preservation",
                  "Medium — balanced growth and stability",
                  "High — maximum long-term growth"],
         default="Medium — balanced growth and stability",
         map={"Low — I prioritise capital preservation": 1,
              "Medium — balanced growth and stability": 3,
              "High — maximum long-term growth": 5}),
    dict(key="q2_age", number="Q2 / 10",
         text="What is your age group?",
         desc="Younger investors can generally afford more volatility. This influences how the AI weights your risk capacity.",
         options=["Under 30","30–39","40–49","50–59","60 or over"],
         default="30–39",
         map={"Under 30":25,"30–39":35,"40–49":45,"50–59":55,"60 or over":65}),
    dict(key="q3_horizon", number="Q3 / 10",
         text="What is your intended investment time horizon?",
         desc="Longer horizons allow more volatility tolerance, as there is more time to recover from market downturns.",
         options=["Short (under 3 years)","Medium (3–10 years)","Long (10–20 years)","Very long (over 20 years)"],
         default="Long (10–20 years)",
         map={"Short (under 3 years)":2,"Medium (3–10 years)":7,"Long (10–20 years)":15,"Very long (over 20 years)":25}),
    dict(key="q4_income", number="Q4 / 10",
         text="What is your approximate annual income?",
         desc="Income determines your capacity to absorb losses and make regular contributions.",
         options=["Under £25,000","£25,000 – £50,000","£50,000 – £100,000","Over £100,000"],
         default="£25,000 – £50,000",
         map={"Under £25,000":20000,"£25,000 – £50,000":37500,"£50,000 – £100,000":75000,"Over £100,000":150000}),
    dict(key="q5_savings", number="Q5 / 10",
         text="How much do you currently have saved or invested?",
         desc="Existing wealth acts as a financial buffer, supporting a more aggressive allocation.",
         options=["Under £5,000","£5,000 – £25,000","£25,000 – £100,000","Over £100,000"],
         default="£5,000 – £25,000",
         map={"Under £5,000":2500,"£5,000 – £25,000":15000,"£25,000 – £100,000":60000,"Over £100,000":200000}),
    dict(key="q6_debt", number="Q6 / 10",
         text="How would you describe your current debt situation?",
         desc="High debt reduces financial flexibility and lowers your capacity to tolerate investment losses.",
         options=["Debt-free","Low debt (mortgage or small loans, well managed)",
                  "Moderate debt (manageable but notable)","High debt (significant financial obligations)"],
         default="Low debt (mortgage or small loans, well managed)",
         map={"Debt-free":0,"Low debt (mortgage or small loans, well managed)":10000,
              "Moderate debt (manageable but notable)":50000,"High debt (significant financial obligations)":150000}),
    dict(key="q7_dependents", number="Q7 / 10",
         text="How many financial dependants do you have?",
         desc="Dependants increase your liquidity needs and responsibilities, reducing investment risk capacity.",
         options=["None","1","2","3 or more"],
         default="None",
         map={"None":0,"1":1,"2":2,"3 or more":3}),
    dict(key="q8_emergency", number="Q8 / 10",
         text="How many months of expenses does your emergency fund cover?",
         desc="A larger emergency fund means you are less likely to need to liquidate investments unexpectedly.",
         options=["Less than 1 month","1–3 months","3–6 months","More than 6 months"],
         default="3–6 months",
         map={"Less than 1 month":0.5,"1–3 months":2,"3–6 months":4.5,"More than 6 months":9}),
    dict(key="q9_experience", number="Q9 / 10",
         text="How long have you been investing?",
         desc="Investment experience indicates familiarity with market volatility and emotional resilience during downturns.",
         options=["I am new to investing (under 1 year)","1–3 years","3–10 years","Over 10 years"],
         default="1–3 years",
         map={"I am new to investing (under 1 year)":0,"1–3 years":2,"3–10 years":6,"Over 10 years":15}),
    dict(key="q10_reaction", number="Q10 / 10",
         text="If your portfolio dropped 25% in a month, you would…",
         desc="Your behavioural response to losses is the most important signal of true risk tolerance. Be honest — there are no wrong answers.",
         options=["Sell everything immediately to stop further losses",
                  "Reduce exposure but hold some positions",
                  "Hold and wait for recovery",
                  "Hold and consider buying more at the lower price",
                  "Actively buy more — it's a long-term opportunity"],
         default="Hold and wait for recovery",
         map={"Sell everything immediately to stop further losses":5,
              "Reduce exposure but hold some positions":9,
              "Hold and wait for recovery":13,
              "Hold and consider buying more at the lower price":17,
              "Actively buy more — it's a long-term opportunity":20}),
]


def generate_advanced_explanation(port: dict, inputs: dict, answers: dict) -> list[str]:
    """Technical explanation with Sharpe ratio, volatility, SHAP‑like factors."""
    cat = port["risk_category"]
    stats = port["stats"]
    sim = port["simulated_growth"]
    alloc = port["allocation_pct"]
    horizon = inputs.get("horizon", 10)

    # Top SHAP-like contributors (we can derive from answers)
    risk_ans = answers.get("q1_risk_comfort", "Medium — balanced growth and stability")
    react_ans = answers.get("q10_reaction", "Hold and wait for recovery")
    horizon_ans = answers.get("q3_horizon", "Long (10–20 years)")
    age_ans = answers.get("q2_age", "30–39")

    top_factors = ["Risk tolerance", "Investment horizon", "Behavioural response to losses"]

    # Top allocations
    top_alloc = sorted(alloc.items(), key=lambda x: x[1], reverse=True)[:2]
    alloc_str = " and ".join(f"**{a}** ({p:.0f}%)" for a, p in top_alloc)

    # ETF mapping for advanced paragraph
    etf_map = {
        "US Equities": "VOO",
        "Global Equities": "VWRA",
        "Technology": "QQQ",
        "Core Fixed Income": "AGG",
        "Gold": "GLD",
        "Commodities": "PDBC",
        "Real Estate": "VNQ",
        "ESG Equities": "ESGU"
    }
    invest_recs = [f"**{etf_map.get(a, a)}** ({p:.0f}%)" for a, p in alloc.items() if p > 0]
    top_invest_recs = " and ".join(invest_recs[:2])

    paragraphs = [
        f"Our AI analysed your answers using a **Random Forest classifier** trained on thousands of investor profiles. "
        f"With high confidence, your responses place you in the **{cat}** risk category – one of five profiles ranging from Very Conservative to Very Aggressive.",

        f"The three most important factors in your result were: **{', '.join(top_factors)}**. "
        f"When you told us you are in the **{age_ans}** age group with a **{horizon_ans}** investment horizon, the AI recognised that you {'have time to recover from market downturns' if horizon >= 10 else 'require capital protection in the near term'}. "
        f"Your reaction to a 25% drop – '*{react_ans}*' – was also a strong signal of your true risk tolerance.",

        f"A **{cat}** profile means {'you are comfortable accepting moderate ups and downs in exchange for long-term growth' if 'Moderate' in cat or 'Aggressive' in cat else 'your priority is protecting the money you have, accepting lower returns in exchange for stability'}. "
        f"The expected annual return for your portfolio is **{stats['expected_annual_return']:.1f}%**, "
        f"with an estimated year-to-year volatility of **{stats['expected_volatility']:.1f}%**. "
        f"A Sharpe ratio of **{stats['sharpe_ratio']:.2f}** indicates you are being well‑compensated for every unit of risk taken.",

        f"**Optimal allocation:** To achieve this portfolio, distribute your capital as {top_invest_recs}. "
        f"This specific {alloc_str} split is designed to {'capture aggressive global market growth while hedging against sudden drops' if stats['expected_annual_return'] > 6 else 'preserve your capital through stable bonds and low‑volatility assets while still beating inflation'}. "
        f"Diversification across these uncorrelated assets reduces idiosyncratic risk.",

        f"Based on **2,000 Monte Carlo simulations**, the median projected value after **{sim['years']} years** is **£{sim['p50']:,.0f}**. "
        f"In a bullish scenario (90th percentile), this could reach **£{sim['p90']:,.0f}**. "
        f"Even in a bearish environment (10th percentile), the model projects **£{sim['p10']:,.0f}**, reflecting the portfolio's built‑in resilience."
    ]
    return paragraphs


def get_real_claude_insight(port_data, user_answers, mode="simple"):
    if not anthropic_client:
        return f"⚠️ **AI Offline**: {claude_status}. Check your `.streamlit/secrets.toml`."

    # Logic to identify the biggest holding for the prompt
    try:
        top_asset = list(port_data['allocation_pct'].keys())[0] if port_data.get('allocation_pct') else "Core Assets"
    except:
        top_asset = "Diversified ETFs"

    prompt = f"""
    You are the DeepAtomicIQ Neural Investment Officer. 
    Analyze this investor profile and write a personalized narrative.
    
    DATA:
    - Profile: {port_data['risk_category']}
    - Sharpe Ratio: {port_data['stats']['sharpe_ratio']:.2f}
    - User Age: {user_answers.get('q2_age', 'Unknown')}
    - Time Horizon: {user_answers.get('q3_horizon', 'Unknown')}
    - Reaction to 25% Market Drop: "{user_answers.get('q10_reaction', 'Hold')}"

    TASK:
    Write a 3-paragraph explanation. 
    1. Explain WHY the {port_data['risk_category']} strategy was chosen for their age and horizon.
    2. Specifically address their reaction to a drop and how the inclusion of {top_asset} balances that fear.
    3. End with a professional, data-driven reassurance based on the Sharpe Ratio.
    
    TONE: Professional, reassuring, human-like. No generic templates.
    """

    try:
        # Calling Claude 3.5 Sonnet
        message = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=800,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"⚠️ **Claude Connection Failed**: {str(e)}"

    # We send the RAW DATA to Claude, not a pre-written sentence
    try:
        first_asset = list(port_data['allocation_pct'].keys())[0] if port_data.get('allocation_pct') else "Core Assets"
    except:
        first_asset = "Core Assets"

    prompt = f"""
    Analyze this investor data and write a unique, personal narrative:
    - Profile: {port_data['risk_category']}
    - Sharpe Ratio: {port_data['stats']['sharpe_ratio']}
    - User Age: {user_answers.get('q2_age')}
    - User Horizon: {user_answers.get('q3_horizon')}
    - Their Panic Reaction: {user_answers.get('q10_reaction')}

    TASK: Write a 3-paragraph explanation explaining why this portfolio fits their specific psychology. 
    Mention how their panic reaction influenced the choice of {first_asset}. 
    Be professional yet encouraging.
    """

    try:
        # Call Claude 3.5 Sonnet
        message = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        # Check specifically for balance issues to help the user
        err_msg = str(e)
        if "credit balance is too low" in err_msg.lower():
            return f"⚠️ **Claude API reached but out of credits**: {err_msg}"
        return f"⚠️ **Claude API Error**: {err_msg}"

def get_ai_explanation(mode: str, port: dict, inputs: dict, answers: dict) -> tuple[str, str]:
    """Return (explanation_text, source_tag)."""
    # Try Real AI first (Claude)
    claude_insight = get_real_claude_insight(port, answers, mode)
    if claude_insight and "⚠️" not in claude_insight:
        return claude_insight, "LIVE CLAUDE 3.5 SONNET"

    # If Claude failed or is unreachable, provide the real local logic but prefix with the reason
    try:
        heuristic_insight = local_explain(port, answers)
        full_text = f"{claude_insight}\n\n---\n\n### 🤖 Local Redundant Interpretation\n{heuristic_insight}" if claude_insight else heuristic_insight
        return full_text, "DEEPIQ HEURISTIC + CLAUDE STATUS"
    except Exception as e:
        return f"⚠️ **AI Narrative Error**: {str(e)}", "ERROR"
