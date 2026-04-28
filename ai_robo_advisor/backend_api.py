"""
backend_api.py
==============
FastAPI REST API — LEM StratIQ Core Backend Engine
LIVE IMPLEMENTATION — Authenticated

Authentication
--------------
All user-specific endpoints require an ``X-Session-ID`` header containing
a valid server-side session ID (opaque random string, stored in MongoDB).

  Authorization: via the ``get_current_user`` FastAPI dependency.
  Source of truth: MongoDB ``sessions`` collection (see session_manager.py).

The caller's identity (email) is ALWAYS taken from the validated session
document — never from a URL parameter or request body the client supplies.
This prevents IDOR (Insecure Direct Object Reference) attacks where one
user could read or modify another user's data by supplying a different email.

Public endpoints (no auth required):
  GET  /api/portfolio/weights       — ETF weights for any risk profile
  GET  /api/market/prices           — Cached ETF prices
  GET  /api/market/intelligence     — Market sentiment signal
  GET  /api/survey/suitability      — Regulatory eligibility check
  POST /api/auth/session/refresh    — Session rotation (self-authenticated)

Protected endpoints (X-Session-ID required):
  POST /api/survey/calculate        — Risk profiling
  GET  /api/survey/history          — Assessment history
  GET  /api/portfolio/current       — Saved portfolio
  PATCH /api/portfolio/config       — IQ parameter override
  GET  /api/user/profile            — User profile
  PATCH /api/user/profile           — Update profile
  PUT  /api/user/preferences        — Sync preferences
  GET  /api/notifications/unread    — Notification feed
  POST /api/support/ticket          — Support request

To run standalone (development):
    pip install fastapi uvicorn
    uvicorn ai_robo_advisor.backend_api:app --reload --port 8000
"""

from __future__ import annotations

import os
import sys
import pickle
import datetime
import uuid
from typing import Optional, Dict, Any

import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from pydantic import BaseModel, Field

# ── Package path so this module can be run standalone or imported ──────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ── Real engine imports ────────────────────────────────────────────────────────
from portfolio_engine import build_portfolio, simulate_growth, RISK_FREE_RATE
import database

# ── Lazy-load ML artefacts (train_model.py must have been run once) ────────────
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

# ── Risk-profile name → integer (1-6) mapping ──────────────────────────────────
_PROFILE_MAP = {
    "Very Conservative": 1,
    "Conservative":      2,
    "Moderate":          3,
    "Aggressive":        4,
    "Very Aggressive":   5,
}

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="LEM StratIQ — Core Backend Engine",
    description=(
        "Live REST API wired to the real Random Forest classifier, "
        "Monte Carlo simulation engine, and MongoDB Atlas persistence layer. "
        "Protected endpoints require a valid X-Session-ID header."
    ),
    version="3.0.0",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Authentication dependency
# ═══════════════════════════════════════════════════════════════════════════════

async def get_current_user(
    x_session_id: str = Header(
        ...,
        alias="X-Session-ID",
        description=(
            "Opaque server-side session ID obtained from the login flow. "
            "The caller's identity is derived from this session — "
            "never from any client-supplied email parameter."
        ),
    )
) -> dict:
    """
    FastAPI dependency: validates X-Session-ID against MongoDB and returns
    the session document.  Raises HTTP 401 if the session is absent,
    expired, or not found.

    Security guarantee: the returned ``email`` field comes from the database
    record, not from anything the HTTP client sent.  No endpoint that uses
    this dependency can be exploited to access another user's data.
    """
    try:
        from session_manager import SessionManager
        sm = SessionManager()
        session_doc = sm.validate(x_session_id)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Session store unavailable: {exc}",
        )

    if not session_doc:
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid or expired session. "
                "Please log in again to obtain a fresh session ID."
            ),
        )
    return session_doc   # contains email, name, provider, expires_at, etc.


# Shorthand type alias used in function signatures below
_Auth = dict   # the session doc returned by get_current_user


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Survey & Risk Profiling Engine  — PROTECTED
# ═══════════════════════════════════════════════════════════════════════════════

class SurveyAnswers(BaseModel):
    """
    Survey inputs.  ``user_email`` is intentionally OMITTED from this model.
    The email is always taken from the authenticated session — the client
    cannot supply or spoof it.
    """
    age:              int   = Field(..., ge=18, le=100)
    income:           float = Field(..., ge=0)
    savings:          float = Field(0.0,  ge=0)
    monthly_expenses: float = Field(500.0, ge=0)
    debt:             float = Field(0.0,  ge=0)
    dependents:       int   = Field(0,    ge=0, le=10)
    horizon:          int   = Field(10,   ge=1, le=40)
    self_risk:        int   = Field(3,    ge=1, le=5)
    emergency_months: float = Field(3.0,  ge=0)
    experience_yrs:   float = Field(0.0,  ge=0)
    behav_score:      int   = Field(13,   ge=5, le=20)


@app.post("/api/survey/calculate", tags=["Profiling Engine"])
async def calculate_risk_profile(
    data: SurveyAnswers,
    background_tasks: BackgroundTasks,
    current_user: _Auth = Depends(get_current_user),
):
    """
    Runs the trained Random Forest classifier on the survey answers and
    returns a risk profile (1-6), class probabilities, and a full
    portfolio object from portfolio_engine.build_portfolio().

    Falls back to the rule-based score if model artefacts are missing.

    **Requires X-Session-ID header.**
    """
    user_email   = current_user["email"]   # ← always from session, never client input
    artefacts_ok = _load_artefacts()

    if artefacts_ok:
        # Build the same feature vector that train_model.py uses
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

        scaled   = _SCALER.transform(feature_vec)
        pred_idx = _MODEL.predict(scaled)[0]
        proba    = _MODEL.predict_proba(scaled)[0]

        category_name = _ENCODER.inverse_transform([pred_idx])[0]
        risk_1_to_6   = _PROFILE_MAP.get(category_name, 3)
        confidence    = float(proba[pred_idx])

        prob_map = {
            _ENCODER.inverse_transform([i])[0]: round(float(p), 4)
            for i, p in enumerate(proba)
        }
    else:
        # Deterministic rule-based fallback (no model.pkl yet)
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
        risk_raw    = float(np.clip(risk_raw, 1, 5))
        risk_1_to_6 = min(6, max(1, round(risk_raw * 6 / 5)))
        confidence  = 0.82
        prob_map    = {}

    portfolio = build_portfolio(risk_score=float(risk_1_to_6) * 10 / 6)

    background_tasks.add_task(
        log_audit_action,
        user_email,
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
async def check_suitability(age: int = 30, income: float = 30000):
    """
    Regulatory suitability check (public — no authentication required).
    UK FCA guidelines: high-risk ETFs require age >= 18 and income >= £17,500.
    No user-specific data is accessed.
    """
    eligible = age >= 18 and income >= 17_500
    reason = (
        "Income and age meet UK FCA suitability thresholds for high-risk ETFs."
        if eligible
        else f"{'Age below 18' if age < 18 else 'Income below £17,500 threshold'}."
    )
    return {"eligible_for_high_risk": eligible, "reason": reason}


@app.get("/api/survey/history", tags=["Profiling Engine"])
async def get_survey_history(current_user: _Auth = Depends(get_current_user)):
    """
    Retrieves all previous assessments from MongoDB for the authenticated user.

    **Requires X-Session-ID header.**
    """
    user_email = current_user["email"]
    try:
        history = database.get_assessment_history(user_email)
        return {"status": "success", "count": len(history), "history": history}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Portfolio & Simulation Engine  — MIXED (weights public, rest protected)
# ═══════════════════════════════════════════════════════════════════════════════

class SimulationParams(BaseModel):
    initial_investment:   float = Field(..., ge=0)
    monthly_contribution: float = Field(0.0,  ge=0)
    time_horizon_years:   int   = Field(..., ge=1, le=50)
    risk_category:        int   = Field(..., ge=1, le=6)
    n_paths:              int   = Field(1000,  ge=100, le=5000)


@app.post("/api/simulation/project", tags=["Investment Engine"])
async def run_monte_carlo_projection(
    params: SimulationParams,
    current_user: _Auth = Depends(get_current_user),
):
    """
    Runs a real stochastic Monte Carlo simulation.
    **Requires X-Session-ID header** (simulation results are user-specific).
    """
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

    rfr_terminal = params.initial_investment * (
        (1 + RISK_FREE_RATE) ** params.time_horizon_years
    )

    return {
        "status":                "success",
        "simulation_engine":     "MonteCarloLogNormal",
        "n_paths":               params.n_paths,
        "annual_return_pct":     round(ret_est * 100, 2),
        "annual_volatility_pct": round(vol_est * 100, 2),
        "p10_worst_case":        round(result["p10"], 2),
        "p25":                   round(result["p25"], 2),
        "median_projection":     round(result["p50"], 2),
        "p75":                   round(result["p75"], 2),
        "p90_best_case":         round(result["p90"], 2),
        "risk_free_benchmark":   round(rfr_terminal, 2),
    }


@app.get("/api/portfolio/current", tags=["Investment Engine"])
async def get_current_portfolio(current_user: _Auth = Depends(get_current_user)):
    """
    Fetches the authenticated user's latest saved assessment from MongoDB.

    **Requires X-Session-ID header.**
    """
    user_email = current_user["email"]
    try:
        saved = database.get_latest_assessment(user_email)
        if not saved:
            raise HTTPException(
                status_code=404,
                detail="No portfolio found. Complete the risk assessment first.",
            )
        port  = saved.get("result", {}).get("portfolio", {})
        stats = port.get("stats", {})
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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/portfolio/weights", tags=["Investment Engine"])
async def get_portfolio_weights(risk_category: int = 3):
    """
    Returns the live DeepAtomicIQ ETF weights for a given risk profile (1-6).
    **Public — no authentication required** (no user-specific data accessed).
    """
    if not (1 <= risk_category <= 6):
        raise HTTPException(status_code=400, detail="risk_category must be 1-6")
    risk_score = float(risk_category) * 10 / 6
    port = build_portfolio(risk_score=risk_score)
    return {
        "status":        "success",
        "risk_category": risk_category,
        "weights":       {k: round(v / 100, 4) for k, v in port["allocation_pct"].items()},
        "iq_params":     port.get("iq_params"),
    }


class PortfolioConfigUpdate(BaseModel):
    delta: Optional[float] = None
    gamma: Optional[float] = None


@app.patch("/api/portfolio/config", tags=["Investment Engine"])
async def update_portfolio_config(
    config: PortfolioConfigUpdate,
    current_user: _Auth = Depends(get_current_user),
):
    """
    Persists manual IQ parameter overrides (delta/gamma) for the authenticated
    user in MongoDB.

    **Requires X-Session-ID header.**
    """
    user_email = current_user["email"]
    updates = config.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")
    try:
        database.update_user_preferences(user_email, updates)
        log_audit_action(user_email, "IQ_CONFIG_UPDATE", updates)
        return {"status": "success", "updated_config": updates}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# 2.5 Market Intelligence  — PUBLIC
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/market/prices", tags=["Market Intelligence"])
async def get_market_prices():
    """Public — serves ETF prices from MongoDB cache. No auth required."""
    try:
        prices = database.get_cached_market_data()
        return {"status": "success", "count": len(prices), "prices": prices}
    except Exception as exc:
        return {"status": "cache_miss", "prices": [], "error": str(exc)}


@app.get("/api/market/intelligence", tags=["Market Intelligence"])
async def get_market_intelligence():
    """
    Public — derives market sentiment from IQ regime weights.
    No user-specific data accessed.
    """
    port    = build_portfolio(risk_score=5.0)
    iq      = port.get("iq_params") or {}
    regimes = iq.get("regimes", {})

    tail_weight = regimes.get("Tail", 0)
    wing_weight = regimes.get("Wing", 0)
    body_weight = regimes.get("Body", 0.7)

    if tail_weight > 0.3:
        sentiment, signal = "High-Volatility Tail Regime Detected", "defensive"
    elif wing_weight > 0.3:
        sentiment, signal = "Asymmetric Wing Regime — Elevated Skew Risk", "cautious"
    elif body_weight > 0.6:
        sentiment, signal = "Normal Body Regime — Efficient Market Conditions", "neutral"
    else:
        sentiment, signal = "Transitional Regime", "neutral"

    return {
        "status":         "success",
        "sentiment":      sentiment,
        "signal":         signal,
        "regime_weights": regimes,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Profile & Identity Management  — PROTECTED
# ═══════════════════════════════════════════════════════════════════════════════

class UserProfileUpdate(BaseModel):
    occupation: Optional[str] = None
    location:   Optional[str] = None


@app.get("/api/user/profile", tags=["Identity"])
async def get_profile(current_user: _Auth = Depends(get_current_user)):
    """
    Retrieves the authenticated user's full profile from MongoDB.

    **Requires X-Session-ID header.**
    """
    user_email = current_user["email"]
    try:
        user = database.get_user(user_email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.patch("/api/user/profile", tags=["Identity"])
async def update_profile(
    updates: UserProfileUpdate,
    current_user: _Auth = Depends(get_current_user),
):
    """
    Persists partial profile updates for the authenticated user to MongoDB.

    **Requires X-Session-ID header.**
    """
    user_email = current_user["email"]
    data = updates.dict(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields provided.")
    try:
        database.update_user_preferences(user_email, data)
        log_audit_action(user_email, "PROFILE_UPDATE", data)
        return {"status": "success", "updated_fields": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Preferences & Notifications  — PROTECTED
# ═══════════════════════════════════════════════════════════════════════════════

class UserPreferences(BaseModel):
    currency:      Optional[str]  = None
    advanced_mode: Optional[bool] = None


@app.put("/api/user/preferences", tags=["Preferences"])
async def sync_preferences(
    prefs: UserPreferences,
    current_user: _Auth = Depends(get_current_user),
):
    """
    Syncs display currency and advanced mode flag for the authenticated user.

    **Requires X-Session-ID header.**
    """
    user_email = current_user["email"]
    data = prefs.dict(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No preferences provided.")
    try:
        database.update_user_preferences(user_email, data)
        return {"status": "synced", "preferences": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/notifications/unread", tags=["Preferences"])
async def intelligence_feed(current_user: _Auth = Depends(get_current_user)):
    """
    Returns unread notifications for the authenticated user from MongoDB.

    **Requires X-Session-ID header.**
    """
    user_email = current_user["email"]
    try:
        notes = database.get_unread_notifications(user_email)
        return {"status": "success", "count": len(notes), "notifications": notes}
    except Exception as exc:
        return {"status": "error", "notifications": [], "error": str(exc)}


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Security & Session Management
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/session/refresh", tags=["Security"])
async def refresh_session_token(
    current_user: _Auth = Depends(get_current_user),
    x_session_id: str = Header(..., alias="X-Session-ID"),
):
    """
    Rotates the current session: creates a new session_id in MongoDB and
    hard-deletes the old one.  Prevents replay attacks.

    **Requires X-Session-ID header** (the session being refreshed).
    The new session_id is returned — the client must store it and use it
    for all subsequent requests.
    """
    try:
        from session_manager import SessionManager
        sm = SessionManager()
        new_sid = sm.rotate(
            old_session_id = x_session_id,
            email          = current_user["email"],
            name           = current_user.get("name", ""),
            provider       = current_user.get("provider", "email"),
            avatar         = current_user.get("avatar"),
        )
        log_audit_action(
            current_user["email"],
            "SESSION_ROTATED",
            {"old_prefix": x_session_id[:8]},
        )
        return {
            "status":     "refreshed",
            "session_id": new_sid,
            "expires_in": 86_400,   # 24 hours in seconds
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class SupportTicket(BaseModel):
    subject: str
    message: str


@app.post("/api/support/ticket", tags=["Support"])
async def create_support_ticket(
    ticket: SupportTicket,
    current_user: _Auth = Depends(get_current_user),
):
    """
    Saves a support ticket to MongoDB for the authenticated user.

    **Requires X-Session-ID header.**
    """
    user_email = current_user["email"]
    ticket_id  = str(uuid.uuid4())
    try:
        database.save_ticket(user_email, ticket.subject, ticket.message)
    except Exception:
        pass   # Don't fail the endpoint if DB write fails
    log_audit_action(user_email, "SUPPORT_TICKET_CREATED", {"ticket_id": ticket_id})
    return {"status": "success", "ticket_id": ticket_id}


# ═══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════

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
