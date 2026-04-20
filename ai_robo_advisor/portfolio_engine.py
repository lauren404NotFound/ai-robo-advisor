"""
portfolio_engine.py
===================
DeepAtomicIQ Integration Engine.

Maps user risk scores to pre-calculated DeepAtomicIQ portfolios (Robo_P1 to P6)
and extracts interpretable IQ parameters for the AI explanation layer.
"""

from __future__ import annotations
import os
import pandas as pd
import numpy as np

# Mapping of tickers in CSVs to human-readable names
TICKER_MAP = {
    "SPX":      "S&P 500 (US Equities)",
    "RTY":      "Russell 2000 (Small Cap)",
    "MXEA":     "MSCI EAFE (Developed Ex-US)",
    "MXEF":     "MSCI EM (Emerging Markets)",
    "LBUSTRUU": "Core Fixed Income (AGG)",
    "LF98TRUU": "High Yield Bonds (HY)",
    "FNERTR":   "Real Estate (REITs)",
    "SPGSCI":   "Commodities (GSCI)",
    "XAU":      "Gold (XAU)",
}

def get_latest_diq_data(profile_num: int) -> dict | None:
    """
    Looks into Robo_Pn/portfolios/ to find the latest learned weights and IQ parameters.
    """
    try:
        # Construct path to the portfolio directory for this specific profile
        # app.py runs in ai_robo_advisor/ which is a sibling to Robo_P1 etc in the root
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        p_dir = os.path.join(root_dir, f"Robo_P{profile_num}", "portfolios")
        
        if not os.path.exists(p_dir):
            return None
        
        # Find all shdiq_wgts files
        files = [f for f in os.listdir(p_dir) if f.startswith("shdiq_wgts_maxsr")]
        if not files:
            return None
        
        # Sort and take the latest (by date in name if possible, or just the first)
        df = pd.read_csv(os.path.join(p_dir, files[0]))
        if df.empty:
            return None
        
        # Get the very latest row
        latest = df.iloc[-1].to_dict()
        
        # Extract weights (tickers matching the TICKER_MAP)
        weights = {TICKER_MAP[t]: float(latest[t]) for t in TICKER_MAP.keys() if t in latest}
        
        # Extract IQ Parameters
        iq_params = {
            "delta":   float(latest.get("delta", 0)),
            "gamma":   float(latest.get("gamma", 0)),
            "epsilon": float(latest.get("epsilon", 0)),
            "regimes": {
                "Body":     float(latest.get("wB", 0.7)),
                "Wing":     float(latest.get("wW", 0.1)),
                "Tail":     float(latest.get("wT", 0.1)),
                "Identity": float(latest.get("wI", 0.1)),
            },
            "ann_vol": float(latest.get("ann_port_vol_val", 0)),
            "date":    str(latest.get("Date", "N/A"))
        }
        
        return {"allocation_pct": {k: round(v*100, 1) for k, v in weights.items() if v > 0.005}, "iq_params": iq_params}
    except Exception as e:
        print(f"Error loading DeepAtomicIQ data for P{profile_num}: {e}")
        return None

def simulate_growth(initial, monthly_contribution, annual_return, annual_volatility, years, n_paths=1000):
    rng = np.random.default_rng(42)
    months = years * 12
    m_r = annual_return / 12
    m_v = annual_volatility / np.sqrt(12)
    
    paths = []
    for _ in range(n_paths):
        val = initial
        for _ in range(months):
            val = val * (1 + rng.normal(m_r, m_v)) + monthly_contribution
        paths.append(max(val, 0))
    
    paths = np.array(paths)
    return {
        "p10": float(np.percentile(paths, 10)),
        "p25": float(np.percentile(paths, 25)),
        "p50": float(np.percentile(paths, 50)),
        "p75": float(np.percentile(paths, 75)),
        "p90": float(np.percentile(paths, 90)),
        "years": years
    }

def growth_curve(initial, monthly_contribution, annual_return, years):
    vals = []
    val = initial
    for m in range(years * 12 + 1):
        vals.append(val)
        val = val * (1 + annual_return/12) + monthly_contribution
    return {"x": [m/12 for m in range(years*12+1)], "y": vals}

def build_portfolio(risk_score: float, initial=10000, monthly=500, years=20) -> dict:
    """
    Main entry point. Maps risk_score (1-10) to DIQ Profile 1-6.
    """
    p_num = 1
    if risk_score <= 2: p_num = 1
    elif risk_score <= 4: p_num = 2
    elif risk_score <= 6: p_num = 3
    elif risk_score <= 8: p_num = 4
    elif risk_score <= 9: p_num = 5
    else: p_num = 6
    
    diq_data = get_latest_diq_data(p_num)
    
    if not diq_data:
        # Fallback to internal simulated data if CSVs missing
        alloc = {"S&P 500 (US Equities)": 40.0, "Core Fixed Income (AGG)": 60.0}
        ret_est = 0.06
        vol_est = 0.08
        iq_params = None
    else:
        alloc = diq_data["allocation_pct"]
        iq_params = diq_data["iq_params"]
        ret_est = 0.04 + (p_num * 0.012)
        vol_est = diq_data["iq_params"]["ann_vol"] / 100 if diq_data["iq_params"]["ann_vol"] > 0 else 0.02 + p_num*0.02

    sim = simulate_growth(initial, monthly, ret_est, vol_est, years)
    curve = growth_curve(initial, monthly, ret_est, years)
    
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    return {
        "risk_category": f"DeepIQ Profile {p_num}",
        "profile_score": p_num,
        "allocation_pct": alloc,
        "iq_params": iq_params,
        "stats": {
            "expected_annual_return": round(ret_est * 100, 2),
            "expected_volatility": round(vol_est * 100, 2),
            "sharpe_ratio": round((ret_est - 0.04) / vol_est, 2) if vol_est > 0 else 0,
            "max_drawdown_est": round(vol_est * 200, 2)
        },
        "simulated_growth": sim,
        "growth_curve": curve,
        "date": today_str  # Use current date for simulation realism
    }

ASSETS = list(TICKER_MAP.values())
