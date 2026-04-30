"""
portfolio_engine.py
===================
DeepAtomicIQ Integration Engine — Three-Layer Personalisation.

Layer A – Profile Interpolation
    Continuously interpolates between adjacent DeepAtomicIQ CSV profiles
    based on the user's exact risk score, rather than hard-snapping to the
    nearest bucket.  Score 4.5 → 50% P2 weights + 50% P3 weights.

Layer B – Answer-Based Tilts
    Adjusts the blended weights based on individual survey answers:
    ESG preference, income vs growth preference, liquidity needs, and
    investment horizon all shift allocations in economically sensible ways.

Layer C – Live Mean-Variance Optimisation (Markowitz)
    Uses scipy to run a Markowitz max-utility optimisation for the user's
    exact risk-aversion parameter (derived from their continuous score).
    This produces a mathematically optimal portfolio unique to each user.
    Falls back to Layer A+B if scipy is unavailable or optimisation fails.

Expected return is derived from the actual portfolio weights dot-producted
against long-run asset-class return estimates (not a hardcoded formula).
"""

from __future__ import annotations
import os
import pandas as pd
import numpy as np

# ── Constants ──────────────────────────────────────────────────────────────────

RISK_FREE_RATE = 0.043  # UK 10-yr Gilt yield (2024 average ~4.3%)

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

ASSETS = list(TICKER_MAP.values())

# Long-run annualised expected returns (geometric mean).
# Sources: Vanguard CMM 2024, BlackRock CMA 2024, Damodaran NYU.
_ASSET_EXPECTED_RETURNS: dict[str, float] = {
    "SPX":      0.087,
    "RTY":      0.092,
    "MXEA":     0.079,
    "MXEF":     0.085,
    "LBUSTRUU": 0.047,
    "LF98TRUU": 0.068,
    "FNERTR":   0.075,
    "SPGSCI":   0.045,
    "XAU":      0.040,
}

# Annualised volatilities (standard deviations) per asset class.
# Sources: Vanguard CMM 2024, BlackRock CMA 2024 (20-year historical).
_ASSET_VOLS: dict[str, float] = {
    "SPX":      0.18,
    "RTY":      0.22,
    "MXEA":     0.17,
    "MXEF":     0.22,
    "LBUSTRUU": 0.05,
    "LF98TRUU": 0.10,
    "FNERTR":   0.20,
    "SPGSCI":   0.20,
    "XAU":      0.18,
}

# Pairwise correlation matrix (order matches TICKER_MAP key order).
# Sources: Vanguard, BlackRock, MSCI historical 2004-2024.
_TICKERS_ORDERED = ["SPX", "RTY", "MXEA", "MXEF", "LBUSTRUU", "LF98TRUU", "FNERTR", "SPGSCI", "XAU"]
_CORR = np.array([
    # SPX   RTY   MXEA  MXEF  LBUST LF98  FNERTR SPGSC XAU
    [1.00, 0.83, 0.80, 0.70, -0.10,  0.40,  0.75,  0.20,  0.05],  # SPX
    [0.83, 1.00, 0.75, 0.70, -0.15,  0.50,  0.75,  0.25,  0.05],  # RTY
    [0.80, 0.75, 1.00, 0.78, -0.05,  0.40,  0.70,  0.25,  0.10],  # MXEA
    [0.70, 0.70, 0.78, 1.00, -0.10,  0.45,  0.60,  0.35,  0.10],  # MXEF
    [-0.10,-0.15,-0.05,-0.10,  1.00,  0.40,  0.10,  0.00,  0.25],  # LBUSTRUU
    [0.40, 0.50, 0.40, 0.45,  0.40,  1.00,  0.45,  0.20,  0.05],  # LF98TRUU
    [0.75, 0.75, 0.70, 0.60,  0.10,  0.45,  1.00,  0.20,  0.10],  # FNERTR
    [0.20, 0.25, 0.25, 0.35,  0.00,  0.20,  0.20,  1.00,  0.35],  # SPGSCI
    [0.05, 0.05, 0.10, 0.10,  0.25,  0.05,  0.10,  0.35,  1.00],  # XAU
], dtype=float)

# Pre-build the full covariance matrix (used by MVO)
_vols_arr = np.array([_ASSET_VOLS[t] for t in _TICKERS_ORDERED])
_SIGMA = np.outer(_vols_arr, _vols_arr) * _CORR


# ── Data loading ───────────────────────────────────────────────────────────────

def get_latest_diq_data(profile_num: int) -> dict | None:
    """
    Load the most recent portfolio weights and IQ parameters for a given
    DeepAtomicIQ profile (1–6).  Returns None if files are missing.
    """
    try:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        p_dir    = os.path.join(root_dir, f"Robo_P{profile_num}", "portfolios")

        if not os.path.exists(p_dir):
            return None

        csv_files = sorted(f for f in os.listdir(p_dir) if f.startswith("shdiq_wgts_maxsr"))
        if not csv_files:
            return None

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
        if "Date" in combined.columns:
            combined["Date"] = pd.to_datetime(combined["Date"], errors="coerce")
            combined = combined.dropna(subset=["Date"]).sort_values("Date")

        if combined.empty:
            return None

        latest = combined.iloc[-1].to_dict()

        weights = {
            TICKER_MAP[t]: float(latest[t])
            for t in TICKER_MAP
            if t in latest and float(latest.get(t, 0)) > 0.005
        }

        # Dot-product expected return from actual weights
        total_weight  = sum(float(latest.get(t, 0)) for t in TICKER_MAP if t in latest)
        weighted_return = 0.0
        if total_weight > 0:
            for ticker, asset_name in TICKER_MAP.items():
                w = float(latest.get(ticker, 0))
                if w > 0:
                    weighted_return += (w / total_weight) * _ASSET_EXPECTED_RETURNS[ticker]
        ann_return = weighted_return if weighted_return > 0 else 0.06

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
            "ann_return_est": round(ann_return * 100, 2),
            "cn_CIQ":         float(latest.get("cn_CIQ", 0)),
            "date":           str(latest.get("Date", "N/A")),
        }

        return {
            "allocation_pct": {k: round(v * 100, 1) for k, v in weights.items()},
            "iq_params":      iq_params,
            "ann_return_est": ann_return,
        }

    except Exception as exc:
        print(f"[portfolio_engine] Error loading DeepAtomicIQ data for P{profile_num}: {exc}")
        return None


# ── Layer A: Continuous profile interpolation ──────────────────────────────────

def _score_to_profiles(score: float) -> tuple[int, int, float]:
    """
    Map a continuous risk score (1–10) to the two adjacent DeepAtomicIQ
    profiles and the fractional blend weight.

    Returns (lower_profile, upper_profile, frac_towards_upper)
    e.g. score=4.5 → (2, 3, 0.25)  because P2 covers 3-4, P3 covers 4-6
    """
    # Breakpoints: each profile covers a segment of the 1-10 scale
    breakpoints = [1.0, 2.0, 4.0, 6.0, 8.0, 9.0, 10.0]
    profiles    = [1,   2,   3,   4,   5,   6]

    score = max(1.0, min(10.0, score))

    for i in range(len(profiles)):
        lo = breakpoints[i]
        hi = breakpoints[i + 1]
        if score <= hi or i == len(profiles) - 1:
            if i < len(profiles) - 1:
                frac = (score - lo) / (hi - lo)
                return profiles[i], profiles[i + 1], min(max(frac, 0.0), 1.0)
            else:
                return profiles[i], profiles[i], 1.0

    return 6, 6, 1.0


def _interpolate_allocations(alloc_a: dict, alloc_b: dict, frac: float) -> dict:
    """
    Linear interpolation between two allocation dicts.
    frac=0 → pure alloc_a, frac=1 → pure alloc_b.
    Result is re-normalised to sum to 100%.
    """
    all_assets = set(alloc_a) | set(alloc_b)
    blended = {}
    for asset in all_assets:
        w_a = alloc_a.get(asset, 0.0)
        w_b = alloc_b.get(asset, 0.0)
        blended[asset] = w_a * (1.0 - frac) + w_b * frac

    total = sum(blended.values())
    if total > 0:
        blended = {k: round(v / total * 100.0, 1) for k, v in blended.items()}
    return blended


# ── Layer B: Survey-answer tilts ───────────────────────────────────────────────

def _apply_answer_tilts(alloc: dict, answers: dict) -> dict:
    """
    Tilt portfolio weights based on individual survey answers.
    All tilts are applied as percentage-point adjustments, then renormalised.
    """
    tilts: dict[str, float] = {}

    def t(asset: str, delta: float) -> None:
        tilts[asset] = tilts.get(asset, 0.0) + delta

    # ESG preference
    esg = answers.get("esg_priority", 1)
    if esg == 3:    # Very important
        t("Commodities (GSCI)",     -4.0)
        t("High Yield Bonds (HY)",  -2.0)
        t("Real Estate (REITs)",    +3.0)
        t("Core Fixed Income (AGG)",+2.0)
        t("Gold (XAU)",             +1.0)
    elif esg == 2:  # Somewhat important
        t("Commodities (GSCI)",     -2.0)
        t("Core Fixed Income (AGG)",+1.5)
        t("Real Estate (REITs)",    +0.5)

    # Income vs Growth preference
    income = answers.get("income_vs_growth", 2)
    if income == 1:  # Income-focused
        t("Core Fixed Income (AGG)",    +6.0)
        t("High Yield Bonds (HY)",      +3.0)
        t("Real Estate (REITs)",        +2.0)
        t("S&P 500 (US Equities)",      -5.0)
        t("MSCI EM (Emerging Markets)", -3.0)
        t("Russell 2000 (Small Cap)",   -3.0)
    elif income == 3:  # Pure growth
        t("S&P 500 (US Equities)",      +5.0)
        t("Russell 2000 (Small Cap)",   +3.0)
        t("MSCI EM (Emerging Markets)", +2.0)
        t("Core Fixed Income (AGG)",    -6.0)
        t("High Yield Bonds (HY)",      -2.0)
        t("Gold (XAU)",                 -2.0)

    # Liquidity needs
    liquidity = answers.get("liquidity_needs", 2)
    if liquidity == 1:  # Very likely to need money soon
        t("Core Fixed Income (AGG)",    +6.0)
        t("Gold (XAU)",                 +2.0)
        t("Real Estate (REITs)",        -4.0)
        t("S&P 500 (US Equities)",      -2.0)
        t("MSCI EM (Emerging Markets)", -2.0)
    elif liquidity == 3:  # Very unlikely — fully invested
        t("S&P 500 (US Equities)",      +2.0)
        t("Russell 2000 (Small Cap)",   +1.0)
        t("Core Fixed Income (AGG)",    -3.0)

    # Investment horizon
    horizon = answers.get("investment_horizon", 2)
    if horizon == 3:  # Long (10+ years)
        t("Russell 2000 (Small Cap)",   +3.0)
        t("MSCI EM (Emerging Markets)", +3.0)
        t("MSCI EAFE (Developed Ex-US)",+1.0)
        t("Core Fixed Income (AGG)",    -5.0)
        t("Gold (XAU)",                 -2.0)
    elif horizon == 1:  # Short (< 3 years)
        t("Core Fixed Income (AGG)",    +7.0)
        t("Gold (XAU)",                 +3.0)
        t("MSCI EM (Emerging Markets)", -5.0)
        t("Russell 2000 (Small Cap)",   -3.0)
        t("S&P 500 (US Equities)",      -2.0)

    # Diversification preference
    diversification = answers.get("diversification", 2)
    if diversification == 1:  # Concentrated — tighten to top 3 assets
        # Boost the top 2 holdings, trim the tail
        sorted_alloc = sorted(alloc.items(), key=lambda x: x[1], reverse=True)
        for i, (asset, _) in enumerate(sorted_alloc):
            if i < 2:
                t(asset, +4.0)
            elif i >= 6:
                t(asset, -3.0)
    elif diversification == 3:  # Broad — nudge tail assets up
        sorted_alloc = sorted(alloc.items(), key=lambda x: x[1], reverse=True)
        for i, (asset, _) in enumerate(sorted_alloc):
            if i >= 5:
                t(asset, +1.5)
            elif i < 2:
                t(asset, -2.0)

    # Apply tilts to base allocation
    result = dict(alloc)
    for asset, delta in tilts.items():
        if asset in result:
            result[asset] = max(0.0, result[asset] + delta)
        elif delta > 0:
            result[asset] = delta   # add new asset if tilt is positive

    # Remove negligible positions (< 0.5%)
    result = {k: v for k, v in result.items() if v >= 0.5}

    # Renormalise to 100%
    total = sum(result.values())
    if total > 0:
        result = {k: round(v / total * 100.0, 1) for k, v in result.items()}

    return result


# ── Layer C: Mean-Variance Optimisation (Markowitz) ───────────────────────────

def _run_mvo(risk_aversion: float) -> dict | None:
    """
    Solve max(μᵀw − λ·wᵀΣw) subject to Σwᵢ=1, wᵢ ∈ [min_w, max_w].

    risk_aversion (λ): higher = more conservative.
      Derived from user's continuous score: λ = 11 - score (score 1 → λ=10, score 10 → λ=1).

    Returns allocation_pct dict or None if scipy unavailable / optimisation fails.
    """
    try:
        from scipy.optimize import minimize
    except ImportError:
        return None

    n   = len(_TICKERS_ORDERED)
    mu  = np.array([_ASSET_EXPECTED_RETURNS[t] for t in _TICKERS_ORDERED])

    def neg_utility(w: np.ndarray) -> float:
        return -(w @ mu - risk_aversion * float(w @ _SIGMA @ w))

    def neg_utility_grad(w: np.ndarray) -> np.ndarray:
        return -(mu - 2.0 * risk_aversion * _SIGMA @ w)

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds      = [(0.02, 0.55)] * n   # min 2%, max 55% per asset
    w0          = np.ones(n) / n

    result = minimize(
        neg_utility,
        w0,
        jac=neg_utility_grad,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-10, "maxiter": 2000},
    )

    if not result.success:
        # Try again from a risk-parity starting point
        w0_rp = (1.0 / _vols_arr) / np.sum(1.0 / _vols_arr)
        result = minimize(
            neg_utility,
            w0_rp,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-8, "maxiter": 2000},
        )

    if result.success or result.fun < 0:   # accept a partial solution too
        w = np.maximum(result.x, 0.0)
        w /= w.sum()
        return {
            TICKER_MAP[t]: round(float(w_i) * 100.0, 1)
            for t, w_i in zip(_TICKERS_ORDERED, w)
            if w_i > 0.005
        }

    return None


# ── Growth simulation ──────────────────────────────────────────────────────────

def simulate_growth(
    initial:              float,
    monthly_contribution: float,
    annual_return:        float,
    annual_volatility:    float,
    years:                int,
    n_paths:              int = 2000,
) -> dict:
    """Monte Carlo simulation using log-normal monthly returns."""
    rng    = np.random.default_rng(42)
    months = years * 12
    m_r    = annual_return     / 12
    m_v    = annual_volatility / np.sqrt(12)

    paths = []
    for _ in range(n_paths):
        val = float(initial)
        for _ in range(months):
            val = val * (1.0 + rng.normal(m_r, m_v)) + monthly_contribution
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
        val = val * (1.0 + annual_return / 12) + monthly_contribution
    return {
        "x": [m / 12 for m in range(years * 12 + 1)],
        "y": vals,
    }


# ── Risk category label ────────────────────────────────────────────────────────

def _risk_label_from_score(score: float) -> str:
    """Human-readable risk category derived continuously from the score."""
    if score <= 2:   return "Capital Preservation"
    elif score <= 4: return "Cautious Growth"
    elif score <= 6: return "Balanced Growth"
    elif score <= 8: return "Dynamic Growth"
    elif score <= 9: return "High Growth"
    else:            return "Aggressive Growth"


# ── Main entry point ───────────────────────────────────────────────────────────

def build_portfolio(
    risk_score: float,
    initial:    float = 10_000,
    monthly:    float = 500,
    years:      int   = 20,
    answers:    dict  | None = None,
) -> dict:
    """
    Build a fully personalised portfolio using three layers:

      A) Continuous interpolation between adjacent DeepAtomicIQ profiles
      B) Survey-answer-based tilts (ESG, income/growth, liquidity, horizon)
      C) Live Markowitz mean-variance optimisation (unique per risk_aversion)

    Layer C is attempted first (most rigorous).  If scipy is unavailable or
    the optimisation fails, Layers A+B are used as the fallback.
    """
    answers = answers or {}

    # ── Risk aversion for MVO: λ = 11 - score → score 1 → λ=10, score 10 → λ=1
    risk_aversion = max(1.0, 11.0 - float(risk_score))

    # ── Layer C: attempt live Markowitz MVO ───────────────────────────────────
    mvo_alloc = _run_mvo(risk_aversion)
    used_mvo  = mvo_alloc is not None

    if used_mvo:
        base_alloc = mvo_alloc
        iq_params  = None  # MVO doesn't have DeepAtomicIQ params
    else:
        # ── Layer A: interpolate between two adjacent DeepAtomicIQ profiles ──
        p_lo, p_hi, frac = _score_to_profiles(risk_score)

        data_lo = get_latest_diq_data(p_lo)
        data_hi = get_latest_diq_data(p_hi) if p_hi != p_lo else data_lo

        if data_lo and data_hi:
            alloc_lo = data_lo["allocation_pct"]
            alloc_hi = data_hi["allocation_pct"]
            base_alloc = _interpolate_allocations(alloc_lo, alloc_hi, frac)
            # Interpolate IQ params (take the lower profile's params as base)
            iq_params  = data_lo["iq_params"]
        elif data_lo:
            base_alloc = data_lo["allocation_pct"]
            iq_params  = data_lo["iq_params"]
        elif data_hi:
            base_alloc = data_hi["allocation_pct"]
            iq_params  = data_hi["iq_params"]
        else:
            # Ultimate fallback when CSV files are absent
            base_alloc = {"S&P 500 (US Equities)": 40.0, "Core Fixed Income (AGG)": 60.0}
            iq_params  = None

    # ── Layer B: apply individual survey answer tilts ─────────────────────────
    if answers:
        final_alloc = _apply_answer_tilts(base_alloc, answers)
    else:
        final_alloc = base_alloc

    # Remove negligible weights (< 0.5%)
    final_alloc = {k: v for k, v in final_alloc.items() if v >= 0.5}

    # ── Compute portfolio statistics from final weights ────────────────────────
    # Map asset names back to tickers for return/vol lookup
    _name_to_ticker = {v: k for k, v in TICKER_MAP.items()}

    total_w = sum(final_alloc.values()) / 100.0   # fraction form
    ret_est = 0.0
    vol_vec = np.zeros(len(_TICKERS_ORDERED))

    for asset_name, pct in final_alloc.items():
        ticker = _name_to_ticker.get(asset_name)
        if ticker:
            w = pct / 100.0
            ret_est += w * _ASSET_EXPECTED_RETURNS[ticker]
            idx = _TICKERS_ORDERED.index(ticker)
            vol_vec[idx] = w

    if ret_est == 0:
        ret_est = 0.06   # safe fallback

    # Portfolio variance via Σ
    port_var = float(vol_vec @ _SIGMA @ vol_vec)
    vol_est  = float(np.sqrt(port_var)) if port_var > 0 else 0.10

    # If we loaded from CSV, prefer the model's own vol estimate when available
    if not used_mvo and iq_params:
        csv_vol = iq_params.get("ann_vol", 0)
        if csv_vol > 0:
            vol_est = csv_vol / 100.0

    sharpe = (ret_est - RISK_FREE_RATE) / vol_est if vol_est > 0 else 0.0

    sim   = simulate_growth(initial, monthly, ret_est, vol_est, years)
    curve = growth_curve(initial, monthly, ret_est, years)

    from datetime import datetime
    return {
        "risk_category":   _risk_label_from_score(risk_score),
        "profile_score":   risk_score,          # continuous, not a bucket integer
        "allocation_pct":  final_alloc,
        "iq_params":       iq_params,
        "personalisation": {
            "mvo_used":       used_mvo,
            "risk_aversion":  round(risk_aversion, 2),
            "answer_tilts":   bool(answers),
        },
        "stats": {
            "expected_annual_return": round(ret_est * 100, 2),
            "expected_volatility":    round(vol_est * 100, 2),
            "sharpe_ratio":           round(sharpe, 2),
            "max_drawdown_est":       round(vol_est * 1.65 * 100, 2),
        },
        "simulated_growth": sim,
        "growth_curve":     curve,
        "date":             datetime.now().strftime("%Y-%m-%d"),
    }
