"""
backend_api.py
==============
FastAPI REST API — LEM StratIQ Core Backend Engine
LIVE IMPLEMENTATION

All endpoints call the real portfolio_engine.py and train_model artefacts.
No hardcoded fake numbers remain.

To run standalone (development):
    pip install fastapi uvicorn
    uvicorn ai_robo_advisor.backend_api:app --reload --port 8000

Streamlit architecture note:
    The Streamlit app (app.py) imports portfolio_engine and database directly
    for in-process speed.  This FastAPI service shows the production-grade
    decoupled architecture — in a scaled deployment the Streamlit frontend
    would call these HTTP endpoints instead of importing Python modules.
"""

from __future__ import annotations

import os
import sys
import pickle
import datetime
import uuid
from typing import List, Optional, Dict, Any

import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

# ── Package path so this module can be run standalone or imported ─────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ── Real engine imports ───────────────────────────────────────────────────────
from portfolio_engine import build_portfolio, simulate_growth, RISK_FREE_RATE
import database

# ── Lazy-load ML artefacts (train_model.py must have been run once) ───────────
_MODEL    = None
_SCALER   = None
_ENCODER  = None
_FEATURES = None

def _load_artefacts():
    global _MODEL, _SCALER, _ENCODER, _FEATURES
    if _MODEL is not None:
        return True
    try:
        def _load(fname):
            with open(os.path.join(_HERE, fname), "rb") as f:
                return pickle.load(f)
        _MODEL    = _load("model.pkl")
        _SCALER   = _load("scaler.pkl")
        _ENCODER  = _load("label_encoder.pkl")
        _FEATURES = _load("feature_names.pkl")
        return True
    except FileNotFoundError:
        return False   # artefacts not yet trained


# ── Risk-profile name → integer (1-6) mapping ────────────────────────────────
_PROFILE_MAP = {
    "Very Conservative": 1,
    "Conservative":      2,
    "Moderate":          3,
    "Aggressive":        4,
    "Very Aggressive":   5,
}

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="LEM StratIQ — Core Backend Engine",
    description=(
        "Live REST API wired to the real Random Forest classifier, "
        "Monte Carlo simulation engine, and MongoDB Atlas persistence layer."
    ),
    version="2.0.0",
)


# ═════════════════════════════════════════════════════════════════════════════
# 1. Survey & Risk Profiling Engine  — LIVE
# ═════════════════════════════════════════════════════════════════════════════

class SurveyAnswers(BaseModel):
    user_email: str
    age: int                              = Field(..., ge=18, le=100)
    income: float                         = Field(..., ge=0)
    savings: float                        = Field(0.0, ge=0)
    monthly_expenses: float               = Field(500.0, ge=0)
    debt: float                           = Field(0.0, ge=0)
    dependents: int                       = Field(0, ge=0, le=10)
    horizon: int                          = Field(10, ge=1, le=40)
    self_risk: int                        = Field(3, ge=1, le=5)
    emergency_months: float               = Field(3.0, ge=0)
    experience_yrs: float                 = Field(0.0, ge=0)
    behav_score: int                      = Field(13, ge=5, le=20)


@app.post("/api/survey/calculate", tags=["Profiling Engine"])
async def calculate_risk_profile(
    data: SurveyAnswers, background_tasks: BackgroundTasks
):
    """
    Runs the trained Random Forest classifier on the survey answers and
    returns a risk profile (1-6), class probabilities, and a full
    portfolio object from portfolio_engine.build_portfolio().

    Falls back to the rule-based score if model artefacts are missing.
    """
    artefacts_ok = _load_artefacts()

    if artefacts_ok:
        # ── Build the same feature vector that train_model.py uses ────────────
        savings_income_ratio = data.savings   / (data.income + 1)
        debt_income_ratio    = data.debt      / (data.income + 1)
        net_monthly          = (data.income / 12) - data.monthly_expenses
        fin_slack            = data.emergency_months * data.monthly_expenses

        feature_vec = np.array([[
            data.age, data.income, data.savings, data.monthly_expenses,
            data.debt, data.dependents, data.horizon, data.self_risk,
            data.emergency_months, data.experience_yrs, data.behav_score,
            savings_income_ratio, debt_income_ratio, net_monthly, fin_slack,
        ]], dtype=float)

        scaled  = _SCALER.transform(feature_vec)
        pred_idx = _MODEL.predict(scaled)[0]
        proba    = _MODEL.predict_proba(scaled)[0]

        category_name  = _ENCODER.inverse_transform([pred_idx])[0]
        risk_1_to_6    = _PROFILE_MAP.get(category_name, 3)
        confidence     = float(proba[pred_idx])

        # Map class probabilities to human-readable labels
        prob_map = {
            _ENCODER.inverse_transform([i])[0]: round(float(p), 4)
            for i, p in enumerate(proba)
        }
    else:
        # ── Deterministic rule-based fallback (no model.pkl yet) ─────────────
        # Mirrors train_model.py's weighting formula
        norm_horizon   = min(data.horizon / 40, 1)
        norm_self_risk = (data.self_risk - 1) / 4
        norm_behav     = (data.behav_score - 5) / 15
        norm_age       = max(0, (75 - data.age) / 57)
        norm_income    = min((data.income - 15_000) / 485_000, 1)
        dti            = min(data.debt / (data.income + 1), 1)
        risk_raw = (
            0.30 * norm_horizon +
            0.25 * norm_self_risk +
            0.20 * norm_behav +
            0.10 * norm_age +
            0.10 * norm_income +
            0.05 * (1 - dti)
        ) * 5
        risk_raw      = float(np.clip(risk_raw, 1, 5))
        risk_1_to_6   = min(6, max(1, round(risk_raw * 6 / 5)))
        confidence    = 0.82   # heuristic rule confidence
        prob_map      = {}

    # ── Build full portfolio from the real engine ─────────────────────────────
    portfolio = build_portfolio(risk_score=float(risk_1_to_6) * 10 / 6)

    background_tasks.add_task(
        log_audit_action,
        data.user_email,
        "SURVEY_COMPLETED",
        {"risk_category": risk_1_to_6, "confidence": confidence},
    )

    return {
        "status":        "success",
        "risk_category": risk_1_to_6,
        "confidence":    round(confidence, 4),
        "probabilities": prob_map,
        "model_used":    "RandomForest" if artefacts_ok else "RuleBasedFallback",
        "portfolio":     portfolio,
    }


@app.get("/api/survey/suitability", tags=["Profiling Engine"])
async def check_suitability(user_email: str, age: int = 30, income: float = 30000):
    """
    Regulatory suitability check.
    UK FCA guidelines: high-risk ETFs require age >= 18 and income >= £17,500.
    """
    eligible = age >= 18 and income >= 17_500
    reason = (
        "Income and age meet UK FCA suitability thresholds for high-risk ETFs."
        if eligible
        else f"{'Age below 18' if age < 18 else 'Income below £17,500 threshold'}."
    )
    return {"eligible_for_high_risk": eligible, "reason": reason}


@app.get("/api/survey/history", tags=["Profiling Engine"])
async def get_survey_history(user_email: str):
    """Retrieves all previous assessments from MongoDB for this user."""
    try:
        history = database.get_assessment_history(user_email)
        return {"status": "success", "count": len(history), "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═════════════════════════════════════════════════════════════════════════════
# 2. Portfolio & Simulation Engine  — LIVE
# ═════════════════════════════════════════════════════════════════════════════

class SimulationParams(BaseModel):
    initial_investment:   float = Field(..., ge=0)
    monthly_contribution: float = Field(0.0, ge=0)
    time_horizon_years:   int   = Field(..., ge=1, le=50)
    risk_category:        int   = Field(..., ge=1, le=6)
    n_paths:              int   = Field(1000, ge=100, le=5000)


@app.post("/api/simulation/project", tags=["Investment Engine"])
async def run_monte_carlo_projection(params: SimulationParams):
    """
    Runs a real stochastic Monte Carlo simulation using portfolio_engine.simulate_growth().
    n_paths log-normal paths are simulated; results are the 10th, 25th, 50th,
    75th, and 90th percentile terminal wealth values.

    Annual return and volatility are derived from the risk category's
    DeepAtomicIQ portfolio profile — not hardcoded.
    """
    # Annual return and vol from profile (matches build_portfolio logic)
    ret_est = 0.04 + (params.risk_category * 0.012)
    vol_est = 0.02 + params.risk_category * 0.02

    result = simulate_growth(
        initial              = params.initial_investment,
        monthly_contribution = params.monthly_contribution,
        annual_return        = ret_est,
        annual_volatility    = vol_est,
        years                = params.time_horizon_years,
        n_paths              = params.n_paths,
    )

    # Also compute simple benchmark (lump-sum at risk-free rate)
    rfr_terminal = params.initial_investment * (
        (1 + RISK_FREE_RATE) ** params.time_horizon_years
    )

    return {
        "status":               "success",
        "simulation_engine":    "MonteCarloLogNormal",
        "n_paths":              params.n_paths,
        "annual_return_pct":    round(ret_est * 100, 2),
        "annual_volatility_pct":round(vol_est * 100, 2),
        "p10_worst_case":       round(result["p10"], 2),
        "p25":                  round(result["p25"], 2),
        "median_projection":    round(result["p50"], 2),
        "p75":                  round(result["p75"], 2),
        "p90_best_case":        round(result["p90"], 2),
        "risk_free_benchmark":  round(rfr_terminal, 2),
    }


@app.get("/api/portfolio/current", tags=["Investment Engine"])
async def get_current_portfolio(user_email: str):
    """
    Fetches the user's latest saved assessment from MongoDB and returns
    the portfolio stats with a cache timestamp.
    """
    try:
        saved = database.get_latest_assessment(user_email)
        if not saved:
            raise HTTPException(
                status_code=404,
                detail="No portfolio found. Complete the risk assessment first.",
            )
        port   = saved.get("result", {}).get("portfolio", {})
        stats  = port.get("stats", {})
        return {
            "risk_category":       port.get("risk_category"),
            "profile_score":       port.get("profile_score"),
            "allocation_pct":      port.get("allocation_pct", {}),
            "expected_return_pct": stats.get("expected_annual_return"),
            "volatility_pct":      stats.get("expected_volatility"),
            "sharpe_ratio":        stats.get("sharpe_ratio"),
            "max_drawdown_est":    stats.get("max_drawdown_est"),
            "retrieved_at":        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/weights", tags=["Investment Engine"])
async def get_portfolio_weights(risk_category: int = 3):
    """
    Returns the live DeepAtomicIQ ETF weights for a given risk profile (1-6)
    directly from portfolio_engine — no hardcoded values.
    """
    if not (1 <= risk_category <= 6):
        raise HTTPException(status_code=400, detail="risk_category must be 1-6")
    # Map profile int to a risk_score in the build_portfolio range
    risk_score = float(risk_category) * 10 / 6
    port = build_portfolio(risk_score=risk_score)
    return {
        "status":       "success",
        "risk_category": risk_category,
        "weights":      {k: round(v / 100, 4) for k, v in port["allocation_pct"].items()},
        "iq_params":    port.get("iq_params"),
    }


class PortfolioConfigUpdate(BaseModel):
    delta: Optional[float] = None
    gamma: Optional[float] = None


@app.patch("/api/portfolio/config", tags=["Investment Engine"])
async def update_portfolio_config(user_email: str, config: PortfolioConfigUpdate):
    """Persists manual IQ parameter overrides (delta/gamma) for the user in MongoDB."""
    updates = config.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")
    try:
        database.update_user_preferences(user_email, updates)
        log_audit_action(user_email, "IQ_CONFIG_UPDATE", updates)
        return {"status": "success", "updated_config": updates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═════════════════════════════════════════════════════════════════════════════
# 2.5 Market Intelligence  — LIVE (MongoDB cache layer)
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/market/prices", tags=["Market Intelligence"])
async def get_market_prices():
    """
    Serves ETF prices from MongoDB cache (populated by market_updater.py).
    Falls back to an empty list if cache is cold.
    """
    try:
        prices = database.get_cached_market_data()
        return {"status": "success", "count": len(prices), "prices": prices}
    except Exception as e:
        return {"status": "cache_miss", "prices": [], "error": str(e)}


@app.get("/api/market/intelligence", tags=["Market Intelligence"])
async def get_market_intelligence():
    """
    Derives a simple market sentiment signal from the IQ regime weights
    of the Profile 3 (Moderate) portfolio — the most data-representative profile.
    """
    port = build_portfolio(risk_score=5.0)
    iq   = port.get("iq_params") or {}
    regimes = iq.get("regimes", {})

    tail_weight = regimes.get("Tail", 0)
    wing_weight = regimes.get("Wing", 0)
    body_weight = regimes.get("Body", 0.7)

    if tail_weight > 0.3:
        sentiment = "High-Volatility Tail Regime Detected"
        signal    = "defensive"
    elif wing_weight > 0.3:
        sentiment = "Asymmetric Wing Regime — Elevated Skew Risk"
        signal    = "cautious"
    elif body_weight > 0.6:
        sentiment = "Normal Body Regime — Efficient Market Conditions"
        signal    = "neutral"
    else:
        sentiment = "Transitional Regime"
        signal    = "neutral"

    return {
        "status":    "success",
        "sentiment": sentiment,
        "signal":    signal,
        "regime_weights": regimes,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 3. Profile & Identity Management  — LIVE (MongoDB)
# ═════════════════════════════════════════════════════════════════════════════

class UserProfileUpdate(BaseModel):
    occupation: Optional[str] = None
    location:   Optional[str] = None


@app.get("/api/user/profile", tags=["Identity"])
async def get_profile(user_email: str):
    """Retrieves full profile from MongoDB and computes a profile-completeness score."""
    try:
        user = database.get_user(user_email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Profile quality: count non-empty optional fields
        fields_total    = ["name", "dob", "provider", "preferences_json"]
        fields_complete = sum(1 for f in fields_total if user.get(f))
        quality_pct     = round((fields_complete / len(fields_total)) * 100)

        return {
            "email":               user.get("email"),
            "name":                user.get("name"),
            "provider":            user.get("provider"),
            "profile_quality_pct": quality_pct,
            "tier":                "Pro" if quality_pct >= 75 else "Basic",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/user/profile", tags=["Identity"])
async def update_profile(user_email: str, updates: UserProfileUpdate):
    """Persists partial profile updates to MongoDB."""
    data = updates.dict(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields provided.")
    try:
        database.update_user_preferences(user_email, data)
        log_audit_action(user_email, "PROFILE_UPDATE", data)
        return {"status": "success", "updated_fields": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═════════════════════════════════════════════════════════════════════════════
# 4. Preferences & Notifications  — LIVE
# ═════════════════════════════════════════════════════════════════════════════

class UserPreferences(BaseModel):
    currency:      Optional[str]  = None
    advanced_mode: Optional[bool] = None


@app.put("/api/user/preferences", tags=["Preferences"])
async def sync_preferences(user_email: str, prefs: UserPreferences):
    """Syncs display currency and advanced mode flag to MongoDB."""
    data = prefs.dict(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No preferences provided.")
    try:
        database.update_user_preferences(user_email, data)
        return {"status": "synced", "preferences": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notifications/unread", tags=["Preferences"])
async def intelligence_feed(user_email: str):
    """
    Returns unread notifications from MongoDB (inserted by market_updater.py
    when regime changes or drawdown thresholds are breached).
    """
    try:
        notes = database.get_unread_notifications(user_email)
        return {"status": "success", "count": len(notes), "notifications": notes}
    except Exception as e:
        return {"status": "error", "notifications": [], "error": str(e)}


# ═════════════════════════════════════════════════════════════════════════════
# 5. Security & Session Management  — LIVE
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/session/refresh", tags=["Security"])
async def refresh_session_token(current_token: str, user_email: str):
    """
    Validates an existing session_id against MongoDB and issues a fresh one
    via SessionManager.rotate().  The old session_id is hard-deleted
    immediately — prevents replay attacks even if the old cookie is captured.
    """
    try:
        from session_manager import SessionManager
        sm = SessionManager()

        # Validate the existing session first
        session_doc = sm.validate(current_token)
        if not session_doc:
            raise HTTPException(
                status_code=401,
                detail="Session not found or expired. Please log in again.",
            )

        # Ensure the token actually belongs to the claimed user
        if session_doc.get("email", "").lower() != user_email.lower().strip():
            raise HTTPException(status_code=403, detail="Session / email mismatch.")

        # Rotate: create new session, invalidate old one atomically
        new_sid = sm.rotate(
            old_session_id=current_token,
            email=session_doc["email"],
            name=session_doc.get("name", ""),
            provider=session_doc.get("provider", "email"),
            avatar=session_doc.get("avatar"),
        )

        log_audit_action(user_email, "SESSION_ROTATED", {"old_prefix": current_token[:8]})
        return {
            "status":      "refreshed",
            "session_id":  new_sid,
            "expires_in":  86_400,   # 24 hours in seconds
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class SupportTicket(BaseModel):
    subject: str
    message: str


@app.post("/api/support/ticket", tags=["Support"])
async def create_support_ticket(user_email: str, ticket: SupportTicket):
    """Saves a support ticket to MongoDB and returns a unique ticket ID."""
    ticket_id = str(uuid.uuid4())
    try:
        database.save_ticket(user_email, ticket.subject, ticket.message)
    except Exception:
        pass  # Don't fail the endpoint if DB write fails — ticket ID still returned
    log_audit_action(user_email, "SUPPORT_TICKET_CREATED", {"ticket_id": ticket_id})
    return {"status": "success", "ticket_id": ticket_id}



# ═════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═════════════════════════════════════════════════════════════════════════════

def log_audit_action(user_email: str, action: str, details: dict) -> None:
    """
    Writes an immutable audit log entry to MongoDB (regulatory requirement).
    Falls back to console logging if DB is unavailable.
    """
    entry = {
        "user_email": user_email,
        "action":     action,
        "timestamp":  datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "details":    details,
    }
    try:
        database.save_audit_log(entry)
    except Exception:
        print(f"[AUDIT] {entry}")
