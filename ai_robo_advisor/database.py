"""
database.py
===========
MongoDB persistence layer for LEM StratIQ (powered by DeepAtomicIQ).
Drop-in replacement for the previous SQLite layer.
All function signatures are identical — no changes required in app.py.
"""

import json
import hashlib
from datetime import datetime

import streamlit as st
from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError

# ── Connection ──────────────────────────────────────────────────────────────
@st.cache_resource
def _get_client():
    """Return a cached MongoClient using the URI stored in st.secrets."""
    try:
        uri = st.secrets["mongodb"]["uri"]
        return MongoClient(uri, serverSelectionTimeoutMS=5000)
    except Exception:
        # Fallback for local testing if secrets aren't loaded
        return MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)

def _db():
    return _get_client()["lem_stratiq"]

def _users():
    return _db()["users"]

def _assessments():
    return _db()["assessments"]

def _tickets():
    return _db()["tickets"]

def _watchlists():
    return _db()["watchlists"]

def _portfolio_configs():
    return _db()["portfolio_configs"]

def _notifications():
    return _db()["notifications"]


# ── Init (idempotent) ───────────────────────────────────────────────────────
def init_db():
    """Ensure indexes exist. Safe to call multiple times."""
    try:
        _users().create_index("email", unique=True)
        _assessments().create_index([("user_email", 1), ("created_at", DESCENDING)])
        _tickets().create_index("user_email")
        _watchlists().create_index("user_email", unique=True)
        _portfolio_configs().create_index("user_email", unique=True)
        _notifications().create_index([("user_email", 1), ("created_at", DESCENDING)])
    except Exception:
        pass 


# ── Helpers ──────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── Users ────────────────────────────────────────────────────────────────────
def create_user(email: str, name: str, password: str, dob: str, provider: str = "email") -> bool:
    try:
        _users().insert_one({
            "email":         email,
            "name":          name,
            "password_hash": hash_password(password),
            "dob":           dob,
            "provider":      provider,
            "preferences":   {},
            "created_at":    datetime.utcnow(),
        })
        return True
    except DuplicateKeyError:
        return False


def create_user_oauth(email: str, name: str, provider: str) -> bool:
    try:
        _users().insert_one({
            "email":         email,
            "name":          name,
            "password_hash": "OAUTH_BYPASS",
            "dob":           None,
            "provider":      provider,
            "preferences":   {},
            "created_at":    datetime.utcnow(),
        })
        return True
    except DuplicateKeyError:
        return False


def get_user(email: str):
    doc = _users().find_one({"email": email}, {"_id": 0})
    if not doc:
        return None
    # Normalise preferences to JSON string so app.py code doesn't break
    prefs = doc.get("preferences", {})
    doc["preferences_json"] = json.dumps(prefs) if isinstance(prefs, dict) else prefs
    return doc


def update_user_preferences(email: str, preferences: dict):
    _users().update_one(
        {"email": email},
        {"$set": {"preferences": preferences, "preferences_json": json.dumps(preferences)}}
    )


def update_password(email: str, new_password: str) -> bool:
    _users().update_one(
        {"email": email},
        {"$set": {"password_hash": hash_password(new_password)}}
    )
    return True


# ── Watchlist Management ──────────────────────────────────────────────────────
def get_watchlist(email: str) -> list:
    doc = _watchlists().find_one({"user_email": email})
    return doc.get("etfs", []) if doc else []

def update_watchlist(email: str, etf_list: list):
    _watchlists().update_one(
        {"user_email": email},
        {"$set": {"etfs": etf_list, "updated_at": datetime.utcnow()}},
        upsert=True
    )

def toggle_watchlist_item(email: str, ticker: str):
    current = get_watchlist(email)
    if ticker in current:
        current.remove(ticker)
    else:
        current.append(ticker)
    update_watchlist(email, current)


# ── Portfolio Configuration (Persistence for sliders) ─────────────────────────
def save_portfolio_config(email: str, config: dict):
    _portfolio_configs().update_one(
        {"user_email": email},
        {"$set": {"config": config, "updated_at": datetime.utcnow()}},
        upsert=True
    )

def get_portfolio_config(email: str) -> dict:
    doc = _portfolio_configs().find_one({"user_email": email})
    return doc.get("config", {}) if doc else {}


# ── Notifications Persistence ─────────────────────────────────────────────────
def add_notification(email: str, title: str, message: str, level: str = "info"):
    _notifications().insert_one({
        "user_email": email,
        "title":      title,
        "message":    message,
        "level":      level,
        "is_read":    False,
        "created_at": datetime.utcnow()
    })

def get_notifications(email: str, limit: int = 20) -> list:
    cursor = _notifications().find(
        {"user_email": email},
        {"_id": 0}
    ).sort("created_at", DESCENDING).limit(limit)
    return list(cursor)


# ── Assessments ───────────────────────────────────────────────────────────────
def save_assessment(email: str, answers: dict, result: dict):
    _assessments().insert_one({
        "user_email": email,
        "answers":    answers,
        "result":     result,
        "created_at": datetime.utcnow(),
    })


def get_latest_assessment(email: str):
    doc = _assessments().find_one(
        {"user_email": email},
        sort=[("created_at", DESCENDING)]
    )
    if doc:
        return {"answers": doc["answers"], "result": doc["result"]}
    return None


# ── Support Tickets ───────────────────────────────────────────────────────────
def save_ticket(email: str, subject: str, message: str):
    _tickets().insert_one({
        "user_email": email,
        "subject":    subject,
        "message":    message,
        "status":     "pending",
        "created_at": datetime.utcnow(),
    })


# ── Init on import ────────────────────────────────────────────────────────────
init_db()
