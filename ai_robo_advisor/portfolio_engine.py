"""
portfolio_engine.py
===================
DeepAtomicIQ Integration Engine.

Maps user risk scores to pre-calculated DeepAtomicIQ portfolios (Robo_P1–P6)
and extracts interpretable IQ parameters for the AI explanation layer.

Fixes applied (2026-04-29):
  1. get_latest_diq_data() now correctly sorts all matching CSVs by the date
     embedded in the last row before selecting the most recent one, rather
     than using files[0] from an unsorted os.listdir() call.
  2. Expected annual return is now derived from the portfolio's actual weights
     dotted against long-run asset-class expected returns, rather than a
     hardcoded formula (0.04 + p_num * 0.012).
"""

from __future__ import annotations
import os
import pandas as pd
import numpy as np

# ── Constants ──────────────────────────────────────────────────────────────────

# Risk-free rate: UK 10-year Gilt yield (2024 average ~4.3 %).
RISK_FREE_RATE = 0.043

# Ticker → human-readable name map (must match CSV column headers).
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

# Long-run annualised expected returns by asset class (geometric mean, real).
# Sources: Vanguard Capital Markets Model 2024, BlackRock Capital Market
# Assumptions 2024, and Damodaran NYU dataset (10-yr historical 2014-2024).
# These are used to derive a data-driven expected return from the actual
# portfolio weights, replacing the previous hardcoded formula.
_ASSET_EXPECTED_RETURNS: dict[str, float] = {
    "SPX":      0.087,   # S&P 500 — 8.7 % (Vanguard CMM 2024 central estimate)
    "RTY":      0.092,   # Russell 2000 small cap — slight premium over large cap
    "MXEA":     0.079,   # Developed ex-US — valuation support, lower than US
    "MXEF":     0.085,   # Emerging markets — higher growth premium, higher risk
    "LBUSTRUU": 0.047,   # Core fixed income — approximately current yield-to-worst
    "LF98TRUU": 0.068,   # High yield bonds — spread over IG + default adj.
    "FNERTR":   0.075,   # REITs — income + modest capital appreciation
    "SPGSCI":   0.045,   # Broad commodities — inflation hedge, low real return
    "XAU":      0.040,   # Gold — long-run real return close to zero; ~4 % nominal
}

ASSETS = list(TICKER_MAP.values())


# ── Data loading ───────────────────────────────────────────────────────────────

def get_latest_diq_data(profile_num: int) -> dict | None:
    """
    Load the most recent portfolio weights and IQ parameters for the given
    DeepAtomicIQ profile number (1–6).

    Fix: Previously used ``files[0]`` from an unsorted ``os.listdir()`` call,
    which could return any file depending on filesystem ordering.  Now all
    matching CSVs are read, concatenated, sorted by their ``Date`` column, and
    the single most-recent row is selected — guaranteeing the latest weights
    are used regardless of file naming or directory order.
    """
    try:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        p_dir    = os.path.join(root_dir, f"Robo_P{profile_num}", "portfolios")

        if not os.path.exists(p_dir):
            return None

        csv_files = sorted(
            f for f in os.listdir(p_dir) if f.startswith("shdiq_wgts_maxsr")
        )
        if not csv_files:
            return None

        # ── Read ALL matching CSVs and concatenate ────────────────────────────
        # This ensures we never miss later rows that sit in a different file.
        dfs = []
        for fname in csv_files:
            try:
                df = pd.read_csv(os.path.join(p_dir, fname))
                if not df.empty:
                    dfs.append(df)
            except Exception as read_err:
                print(f"[portfolio_engine] Warning: could not read {fname}: {read_err}")

        if not dfs:
            return None

        combined = pd.concat(dfs, ignore_index=True)

        # ── Sort by Date column and take the single latest row ─────────────
        if "Date" in combined.columns:
            combined["Date"] = pd.to_datetime(combined["Date"], errors="coerce")
            combined = combined.dropna(subset=["Date"]).sort_values("Date")
        # If no parseable Date column, fall back to row order (concat order = file order)

        if combined.empty:
            return None

        latest = combined.iloc[-1].to_dict()

        # ── Extract ticker weights ─────────────────────────────────────────
        weights = {
            TICKER_MAP[t]: float(latest[t])
            for t in TICKER_MAP
            if t in latest and float(latest.get(t, 0)) > 0.005
        }

        # ── Derive data-driven expected return ─────────────────────────────
        # Dot-product of actual portfolio weights with long-run asset returns.
        # This replaces the previous formula (0.04 + p_num * 0.012) which was
        # independent of what the model actually allocated.
        total_weight  = sum(float(latest.get(t, 0)) for t in TICKER_MAP if t in latest)
        weighted_return = 0.0
        if total_weight > 0:
            for ticker, asset_name in TICKER_MAP.items():
                w = float(latest.get(ticker, 0))
                if w > 0:
                    weighted_return += (w / total_weight) * _ASSET_EXPECTED_RETURNS[ticker]
        # Fall back to a conservative 6 % if weights are all zero (shouldn't happen)
        ann_return = weighted_return if weighted_return > 0 else 0.06

        # ── Extract IQ parameters ──────────────────────────────────────────
        iq_params = {
            "delta":    float(latest.get("delta",   0)),
            "gamma":    float(latest.get("gamma",   0)),
            "epsilon":  float(latest.get("epsilon", 0)),
            "regimes": {
                "Body":     float(latest.get("wB", 0.7)),
                "Wing":     float(latest.get("wW", 0.1)),
                "Tail":     float(latest.get("wT", 0.1)),
                "Identity": float(latest.get("wI", 0.1)),
            },
            "ann_vol":        float(latest.get("ann_port_vol_val", 0)),
            "ann_return_est": round(ann_return * 100, 2),   # store for transparency
            "cn_CIQ":         float(latest.get("cn_CIQ", 0)),
            "date":           str(latest.get("Date", "N/A")),
        }

        return {
            "allocation_pct": {k: round(v * 100, 1) for k, v in weights.items()},
            "iq_params":      iq_params,
            "ann_return_est": ann_return,   # surfaced to build_portfolio()
        }

    except Exception as exc:
        print(f"[portfolio_engine] Error loading DeepAtomicIQ data for P{profile_num}: {exc}")
        return None


# ── Growth simulation ──────────────────────────────────────────────────────────

def simulate_growth(
    initial:              float,
    monthly_contribution: float,
    annual_return:        float,
    annual_volatility:    float,
    years:                int,
    n_paths:              int = 1000,
) -> dict:
    """
    Monte Carlo simulation using log-normal monthly returns.
    Fixed random seed (42) ensures reproducible percentiles across reruns.
    """
    rng    = np.random.default_rng(42)
    months = years * 12
    m_r    = annual_return    / 12
    m_v    = annual_volatility / np.sqrt(12)

    paths = []
    for _ in range(n_paths):
        val = float(initial)
        for _ in range(months):
            val = val * (1 + rng.normal(m_r, m_v)) + monthly_contribution
        paths.append(max(val, 0.0))

    arr = np.array(paths)
    return {
        "p10":   float(np.percentile(arr, 10)),
        "p25":   float(np.percentile(arr, 25)),
        "p50":   float(np.percentile(arr, 50)),
        "p75":   float(np.percentile(arr, 75)),
        "p90":   float(np.percentile(arr, 90)),
        "years": years,
    }


def growth_curve(
    initial:              float,
    monthly_contribution: float,
    annual_return:        float,
    years:                int,
) -> dict:
    """Deterministic compound-growth curve for chart display."""
    vals = []
    val  = float(initial)
    for _ in range(years * 12 + 1):
        vals.append(val)
        val = val * (1 + annual_return / 12) + monthly_contribution
    return {
        "x": [m / 12 for m in range(years * 12 + 1)],
        "y": vals,
    }


# ── Main entry point ───────────────────────────────────────────────────────────

def build_portfolio(risk_score: float, initial: float = 10_000,
                    monthly: float = 500, years: int = 20) -> dict:
    """
    Map risk_score (1–10 scale) to DeepIQ Profile 1–6, load the latest model
    weights, and build a full portfolio object including simulation results.

    Expected return is derived from actual portfolio weights × long-run
    asset-class expected returns (see ``_ASSET_EXPECTED_RETURNS``), not from
    a hardcoded formula.
    """
    if   risk_score <= 2: p_num = 1
    elif risk_score <= 4: p_num = 2
    elif risk_score <= 6: p_num = 3
    elif risk_score <= 8: p_num = 4
    elif risk_score <= 9: p_num = 5
    else:                 p_num = 6

    diq_data = get_latest_diq_data(p_num)

    if not diq_data:
        # ── Fallback: CSVs missing (e.g. first-run / stripped repo) ──────────
        alloc     = {"S&P 500 (US Equities)": 40.0, "Core Fixed Income (AGG)": 60.0}
        ret_est   = 0.06
        vol_est   = 0.08
        iq_params = None
    else:
        alloc     = diq_data["allocation_pct"]
        iq_params = diq_data["iq_params"]

        # ── Return: weight-derived (data-driven), NOT formula-based ──────────
        ret_est = diq_data["ann_return_est"]

        # ── Volatility: from model's ann_port_vol_val (%), converted to ratio
        raw_vol = diq_data["iq_params"]["ann_vol"]
        vol_est = raw_vol / 100.0 if raw_vol > 0 else max(0.04, 0.02 + p_num * 0.015)

    sim   = simulate_growth(initial, monthly, ret_est, vol_est, years)
    curve = growth_curve(initial, monthly, ret_est, years)

    from datetime import datetime
    return {
        "risk_category":   f"DeepIQ Profile {p_num}",
        "profile_score":   p_num,
        "allocation_pct":  alloc,
        "iq_params":       iq_params,
        "stats": {
            "expected_annual_return": round(ret_est * 100, 2),
            "expected_volatility":    round(vol_est * 100, 2),
            # Sharpe ratio: excess return above risk-free rate per unit of vol.
            # Risk-free rate: RISK_FREE_RATE constant (UK 10-yr Gilt, 2024 avg).
            "sharpe_ratio":     round((ret_est - RISK_FREE_RATE) / vol_est, 2)
                                if vol_est > 0 else 0,
            # Max drawdown approximation: 1.65σ (95th percentile 1-yr loss).
            # A full path-dependent MDD requires recording per-step portfolio
            # values — the Monte Carlo paths above use terminal values only.
            "max_drawdown_est": round(vol_est * 1.65 * 100, 2),
        },
        "simulated_growth": sim,
        "growth_curve":     curve,
        "date":             datetime.now().strftime("%Y-%m-%d"),
    }
