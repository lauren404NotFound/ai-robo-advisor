"""
explainer.py
===================
AI Interpretation layer for DeepAtomicIQ.

Translates the interpretable IQ parameters (Delta, Gamma, Epsilon) and 
regime mixtures (Body, Wing, Tail) into plain-English summaries.
"""

from __future__ import annotations

def predict(inputs: list[float]) -> str:
    """Mock prediction to satisfy app.py dependencies."""
    return "Handled by portfolio_engine.get_latest_diq_data"

def explain(inputs: list[float]) -> list[dict]:
    """Mock explanation to satisfy app.py dependencies."""
    return []

class DeepIQInterpreter:
    @staticmethod
    def get_summary(params: dict) -> str:
        if not params:
            return "IQ analytics are currently unavailable for this profile."
        
        delta = params.get("delta", 0)
        gamma = params.get("gamma", 0)
        regimes = params.get("regimes", {})
        
        # Interpret Delta (Threshold)
        d_str = (
            "The model has set a **high threshold (δ)**, meaning it is currently focusing on "
            "significant co-movements and filtering out smaller market noise." if delta > 1.2 else
            "The model is using a **sensitive threshold (δ)**, reacting to even subtle shifts "
            "in asset correlations to capture emerging trends."
        )
        
        # Interpret Gamma (Memory)
        if gamma > 0:
            g_str = "The system is **Recency-Biased (γ > 0)**, prioritizing the latest market data to keep the portfolio agile."
        elif gamma < 0:
            g_str = "The system is **History-Biased (γ < 0)**, emphasizing long-term historical co-movements for stability."
        else:
            g_str = "The system is **Neutral-Weighted**, treating old and new data with equal importance."
            
        # Interpret Regimes
        top_regime = max(regimes, key=regimes.get)
        r_desc = {
            "Body": "The market is in a **Normal Regime (Body)**, where assets are behaving according to their historical averages.",
            "Wing": "An **Asymmetric Regime (Wing)** has been detected, suggesting assets are starting to move in unusual pairs.",
            "Tail": "The model has detected a **Tail Event regime**, indicating extreme co-movements (market stress) and triggering defensive allocations.",
            "Identity": "The market shows **Idiosyncratic moves (Identity)**, where individual asset risks outweigh general market trends."
        }
        
        summary = f"""
### 🧠 DeepIQ AI Strategy Note
Analysis Date: **{params.get('date', 'N/A')}**

1. **Market Sensitivity**: {d_str}
2. **Temporal Logic**: {g_str}
3. **Detected Regime**: {r_desc.get(top_regime, "")}

**Why this matters**: Based on these parameters, the Markowitz-Informed Neural Network (MINN) has optimized your weights to maximize the Sharpe Ratio while balancing these specific co-movement risks.
"""
        return summary
