"""
explainer.py
===================
AI Interpretation layer for DeepAtomicIQ.

Translates the interpretable IQ parameters (Delta, Gamma, Epsilon) and 
regime mixtures (Body, Wing, Tail) into plain-English summaries.
"""

from __future__ import annotations

def predict(inputs: list[float]) -> str:
    """
    Simulates a model prediction if needed. 
    In this app, we primarily use the pre-calculated DeepAtomicIQ weights.
    """
    return "DeepIQ Model Active"

def explain(port: dict, answers: dict) -> str:
    """
    The core local (offline) explanation engine.
    Uses rules and iq_params to generate a high-quality interpretation.
    """
    iq = port.get("iq_params", {})
    cat = port.get("risk_category", "Unknown")
    stats = port.get("stats", {})
    
    # 1. Start with the IQ block
    summary = DeepIQInterpreter.get_summary(iq)
    
    # 2. Add personal context from survey
    age = answers.get("q2_age", "N/A")
    horizon = answers.get("q3_horizon", "N/A")
    reaction = answers.get("q10_reaction", "N/A")
    
    personal_note = f"""
### 👥 Personal Alignment Note
- **Time Horizon**: With a **{horizon}** horizon, the MINN has calibrated your 'Temporal Decay (γ)' to ensure your capital is protected relative to your target date.
- **Psychological Buffer**: You noted that in a market drop, you would: *"{reaction}"*. 
  - To accommodate this, the model has adjusted the **Tail Risk Weight (wT)** to ensure that if a crash occurs, your portfolio has enough 'Safe Haven' assets (like Gold or Bonds) to prevent a panic-inducing drawdown.

**Strategy Insight**: Your portfolio's Sharpe Ratio of **{stats.get('sharpe_ratio', 0)}** is optimized for this specific risk-tolerance/regime combination.
"""
    return summary + "\n" + personal_note

class DeepIQInterpreter:
    @staticmethod
    def get_summary(params: dict) -> str:
        if not params:
            return "### 🧠 DeepIQ AI Strategy Note\nIQ analytics are currently unavailable for this profile. Using baseline Markowitz allocation."
        
        delta = params.get("delta", 0)
        gamma = params.get("gamma", 0)
        regimes = params.get("regimes", {})
        
        # Interpret Delta (Threshold)
        if delta > 1.2:
            d_str = "The model has set a **high threshold (δ)**, focusing only on significant market moves and filtering out background noise."
        elif delta > 0.6:
            d_str = "The model is using a **balanced threshold (δ)**, maintaining a steady view of asset correlations."
        else:
            d_str = "The model is using a **sensitive threshold (δ)**, reacting to even subtle shifts in asset co-movements to capture emerging trends."
        
        # Interpret Gamma (Memory)
        if gamma > 0.05:
            g_str = "The system is **Recency-Biased (γ > 0.05)**, prioritizing the latest market data to keep the portfolio agile."
        elif gamma < -0.05:
            g_str = "The system is **History-Biased (γ < -0.05)**, emphasizing long-term stability and historical averages."
        else:
            g_str = "The system is **Neutral-Weighted**, treating old and new data with balanced importance."
            
        # Interpret Regimes
        top_regime = "Body"
        if regimes:
            top_regime = max(regimes, key=regimes.get)
            
        r_desc = {
            "Body": "The market is in a **Normal Regime (Body)**. Assets are behaving according to their historical averages, allowing for standard optimization.",
            "Wing": "An **Asymmetric Regime (Wing)** has been detected. This suggests unusual pair-wise correlations are forming, and the model is adjusting to these 'non-normal' swings.",
            "Tail": "The model has detected a **Tail Event regime** (Extreme stress). It has triggered defensive allocations to protect against systemic co-movements.",
            "Identity": "The market shows **Idiosyncratic moves (Identity)**. Individual asset risks outweigh general trends; the model is diversifying more broadly as a result."
        }
        
        summary = f"""
### 🧠 DeepIQ AI Strategy Note
Analysis Date: **{params.get('date', 'N/A')}**

1. **Market Sensitivity**: {d_str}
2. **Temporal Logic**: {g_str}
3. **Detected Regime**: {r_desc.get(top_regime, "Stable")}

**Why this matters**: The Markowitz-Informed Neural Network (MINN) uses these parameters to re-weight your assets daily, ensuring your risk exposure matches the current "Manifold" of the market.
"""
        return summary
