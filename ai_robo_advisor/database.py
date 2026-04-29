"""
database.py
===========
MongoDB persistence layer for LEM StratIQ (powered by DeepAtomicIQ).
Drop-in replacement for the previous SQLite layer.
All function signatures are identical — no changes required in app.py.
"""

import json
import hashlib
import hmac
from datetime import datetime, timedelta

import streamlit as st
from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError
import bcrypt

# ── Connection ──────────────────────────────────────────────────────────────
@st.cache_resource
def _get_client():
    """
    Return a cached MongoClient.
    Tries the URI in st.secrets first; falls back to localhost ONLY for local
    development, and logs a warning so the fallback is never silent.
    """
    import logging
    _log = logging.getLogger("lem_stratiq.database")
    try:
        uri = st.secrets["mongodb"]["uri"]
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        return client
    except KeyError:
        _log.warning(
            "[database] 'mongodb.uri' not found in st.secrets — "
            "falling back to mongodb://localhost:27017/ (local dev only)."
        )
    except Exception as exc:
        _log.warning(
            f"[database] Failed to read secrets.toml: {exc} — "
            "falling back to localhost."
        )
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

def _sessions():
    return _db()["sessions"]

def _verification_codes():
    return _db()["verification_codes"]

def _audit_logs():
    return _db()["audit_logs"]

def _billing():
    return _db()["billing"]

def _market_data_cache():
    return _db()["market_data_cache"]

def _portfolio_history():
    return _db()["portfolio_history"]

def _activity_feed():
    return _db()["activity_feed"]

# ── Init (idempotent) ──────────────────────────────────────────────────────
def init_db():
    """
    Ensure all MongoDB indexes exist.  Safe to call multiple times.

    Error handling:
      - pymongo.OperationFailure with code 85/86 (IndexOptionsConflict /
        IndexKeySpecsConflict) means the index already exists with different
        options — logged as a warning, not fatal.
      - Any other exception (connection failure, auth error, etc.) is logged
        as an ERROR and re-raised so the caller knows initialisation failed.
        The app must NOT silently continue with a broken database.
    """
    import logging
    from pymongo.errors import OperationFailure
    _log = logging.getLogger("lem_stratiq.database")

    index_specs = [
        # (collection_fn, args, kwargs)
        (_users,           (["email"],),             {"unique": True}),
        (_assessments,     ([("user_email", 1), ("created_at", DESCENDING)],), {}),
        (_tickets,         (["user_email"],),          {}),
        (_watchlists,      (["user_email"],),           {"unique": True}),
        (_portfolio_configs, (["user_email"],),         {"unique": True}),
        (_notifications,   ([("user_email", 1), ("created_at", DESCENDING)],), {}),
        # Sessions — TTL auto-expiry + fast lookup
        (_sessions,        (["expires_at"],),           {"expireAfterSeconds": 0}),
        (_sessions,        (["session_id"],),            {"unique": True}),
        (_sessions,        (["email"],),                 {}),
        # OTP — TTL auto-delete
        (_verification_codes, (["expires_at"],),        {"expireAfterSeconds": 0}),
        # Audit / billing
        (_audit_logs,      ([("user_email", 1), ("action", 1)],), {}),
        (_billing,         (["user_email"],),            {"unique": True}),
        # Extra collections
        (_market_data_cache, (["ticker"],),             {"unique": True}),
        (_portfolio_history, ([("user_email", 1), ("date", DESCENDING)],), {}),
        (_activity_feed,   ([("user_email", 1), ("created_at", DESCENDING)],), {}),
        (_activity_feed,   (["is_read"],),               {}),
    ]

    errors = []
    for col_fn, args, kwargs in index_specs:
        try:
            col_fn().create_index(*args, **kwargs)
        except OperationFailure as exc:
            # Codes 85/86: index already exists — harmless on repeated calls
            if exc.code in (85, 86):
                _log.debug(
                    f"[database.init_db] Index already exists on "
                    f"{col_fn.__name__}: {exc}"
                )
            else:
                _log.error(
                    f"[database.init_db] OperationFailure on "
                    f"{col_fn.__name__}: {exc}"
                )
                errors.append(exc)
        except Exception as exc:
            _log.error(
                f"[database.init_db] Unexpected error on "
                f"{col_fn.__name__}: {exc}"
            )
            errors.append(exc)

    if errors:
        raise RuntimeError(
            f"[database.init_db] {len(errors)} index(es) failed to create. "
            f"First error: {errors[0]}"
        )


def db_health_check() -> dict:
    """
    Probe the MongoDB connection and return a status dict.
    Call this from app.py on startup to surface connection problems
    immediately rather than discovering them on the first user request.

    Returns:
        {"status": "ok",      "latency_ms": float}   on success
        {"status": "error",   "detail":     str}      on failure
    """
    import logging, time
    _log = logging.getLogger("lem_stratiq.database")
    try:
        t0 = time.monotonic()
        # server_info() forces a real network round-trip
        _get_client().server_info()
        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        _log.info(f"[database.db_health_check] MongoDB OK — {latency_ms} ms")
        return {"status": "ok", "latency_ms": latency_ms}
    except Exception as exc:
        _log.error(f"[database.db_health_check] MongoDB unreachable: {exc}")
        return {"status": "error", "detail": str(exc)}



# ── Helpers ──────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hash a password using bcrypt for high security."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


# ── Users ────────────────────────────────────────────────────────────────────
def create_user(email: str, name: str, password: str, dob: str, provider: str = "email", phone_number: str = None) -> bool:
    try:
        now = datetime.utcnow()
        _users().insert_one({
            "email":         email.lower().strip(),
            "name":          name,
            "password_hash": hash_password(password),
            "dob":           dob,
            "provider":      provider,
            "phone_number":  phone_number,
            "oauth_id":      None,
            "is_verified":   True, # We only run this function after successful OTP/social verification
            "preferences":   {},
            "created_at":    now,
            "last_login":    now,
        })
        return True
    except DuplicateKeyError:
        return False


def create_user_oauth(email: str, name: str, provider: str, oauth_id: str = None) -> bool:
    try:
        now = datetime.utcnow()
        _users().insert_one({
            "email":         email,
            "name":          name,
            "password_hash": "OAUTH_BYPASS",
            "dob":           None,
            "provider":      provider,
            "phone_number":  None,
            "oauth_id":      oauth_id,
            "is_verified":   True,
            "preferences":   {},
            "created_at":    now,
            "last_login":    now,
        })
        return True
    except DuplicateKeyError:
        return False


def get_user(email: str):
    doc = _users().find_one({"email": email.lower().strip()}, {"_id": 0})
    if not doc:
        return None
    # Normalise preferences to JSON string so app.py code doesn't break
    prefs = doc.get("preferences", {})
    doc["preferences_json"] = json.dumps(prefs) if isinstance(prefs, dict) else prefs
    return doc


def update_user_preferences(email: str, preferences: dict):
    _users().update_one(
        {"email": email.lower().strip()},
        {"$set": {"preferences": preferences, "preferences_json": json.dumps(preferences)}}
    )


def update_user_name(email: str, new_name: str) -> bool:
    _users().update_one(
        {"email": email.lower().strip()},
        {"$set": {"name": new_name}}
    )
    return True

def update_password(email: str, new_password: str) -> bool:
    _users().update_one(
        {"email": email.lower().strip()},
        {"$set": {"password_hash": hash_password(new_password)}}
    )
    return True

# ── Verification Codes ───────────────────────────────────────────────────────
def save_verification_code(identifier: str, code: str, minutes_valid: int = 15):
    """
    Persist a new OTP code for ``identifier``, replacing any existing one.
    ``expires_at`` is stored explicitly so verify_code() can enforce expiry
    at the application layer — independent of MongoDB TTL sweep timing.
    """
    now = datetime.utcnow()
    _verification_codes().update_one(
        {"identifier": identifier},
        {
            "$set": {
                "code":       code,
                "created_at": now,
                "expires_at": now + timedelta(minutes=minutes_valid),
                "attempts":   0,   # reset brute-force counter on new code
            }
        },
        upsert=True,
    )

def verify_code(identifier: str, code: str) -> bool:
    """
    Verify an OTP code with all three security checks:

    1. Existence   — document must be present in MongoDB.
    2. Expiry      — ``expires_at`` is checked in Python, NOT delegated to
                     the MongoDB TTL index.  The TTL sweep runs on a ~60-second
                     background task; relying on it alone means a code could
                     remain valid for up to 60 seconds past its stated expiry.
    3. Value       — constant-time ``hmac.compare_digest`` prevents timing
                     side-channel attacks that could leak partial-match info.

    Additionally:
    - A failed attempt increments ``attempts`` on the document.  After
      ``MAX_ATTEMPTS`` failures the document is deleted, forcing the user
      to request a new code (brute-force mitigation).
    - A successful verification deletes the document immediately (single-use).
    """
    MAX_ATTEMPTS = 5

    doc = _verification_codes().find_one({"identifier": identifier})
    if not doc:
        return False

    # --- 1. Application-level expiry (do not trust TTL timing alone) ----------
    expires_at = doc.get("expires_at")
    if expires_at is None or datetime.utcnow() > expires_at:
        # Code has expired — delete it now so TTL is never the safety net
        _verification_codes().delete_one({"_id": doc["_id"]})
        return False

    # --- 2. Brute-force guard --------------------------------------------------
    attempts = doc.get("attempts", 0)
    if attempts >= MAX_ATTEMPTS:
        _verification_codes().delete_one({"_id": doc["_id"]})
        return False

    # --- 3. Constant-time value comparison ------------------------------------
    if hmac.compare_digest(str(doc.get("code", "")), str(code)):
        # Correct code — delete immediately (single-use)
        _verification_codes().delete_one({"_id": doc["_id"]})
        return True

    # Wrong code — increment attempt counter
    _verification_codes().update_one(
        {"_id": doc["_id"]},
        {"$inc": {"attempts": 1}},
    )
    return False


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
        "user_email": email.lower().strip(),
        "answers":    answers,
        "result":     result,
        "created_at": datetime.utcnow(),
    })


def get_latest_assessment(email: str):
    doc = _assessments().find_one(
        {"user_email": email.lower().strip()},
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


# ── Market Data Cache ─────────────────────────────────────────────────────────
def update_market_cache(ticker: str, last_price: float, change_pct: float, sparkline_data: list):
    _market_data_cache().update_one(
        {"ticker": ticker},
        {
            "$set": {
                "last_price": last_price,
                "change_pct": change_pct,
                "sparkline_data": sparkline_data,
                "last_updated": datetime.utcnow()
            }
        },
        upsert=True
    )

def get_market_cache(ticker: str):
    return _market_data_cache().find_one({"ticker": ticker}, {"_id": 0})

def get_all_market_cache():
    return list(_market_data_cache().find({}, {"_id": 0}))


# ── Portfolio Historical Performance ──────────────────────────────────────────
def add_portfolio_history(email: str, total_value: float, daily_profit_loss: float, deposited_amount: float):
    _portfolio_history().insert_one({
        "user_email": email,
        "date": datetime.utcnow(),
        "total_value": total_value,
        "daily_profit_loss": daily_profit_loss,
        "deposited_amount": deposited_amount
    })

def get_portfolio_history(email: str, limit: int = 30) -> list:
    cursor = _portfolio_history().find(
        {"user_email": email},
        {"_id": 0}
    ).sort("date", DESCENDING).limit(limit)
    return list(cursor)


# ── User Activity Feed ────────────────────────────────────────────────────────
def add_activity_feed_event(email: str, event_type: str, message: str):
    _activity_feed().insert_one({
        "user_email": email,
        "event_type": event_type,
        "message": message,
        "is_read": False,
        "created_at": datetime.utcnow()
    })

def get_activity_feed(email: str, limit: int = 20) -> list:
    cursor = _activity_feed().find(
        {"user_email": email},
        {"_id": 0}
    ).sort("created_at", DESCENDING).limit(limit)
    return list(cursor)

def mark_activity_feed_read(email: str):
    _activity_feed().update_many(
        {"user_email": email, "is_read": False},
        {"$set": {"is_read": True}}
    )


# ── backend_api.py support functions ─────────────────────────────────────────

def get_assessment_history(email: str) -> list:
    """All past assessments for a user, newest first (used by /api/survey/history)."""
    cursor = _assessments().find(
        {"user_email": email},
        {"_id": 0}
    ).sort("created_at", DESCENDING)
    return list(cursor)


def get_cached_market_data() -> list:
    """Return all tickers from the market data cache (used by /api/market/prices)."""
    cursor = _market_data_cache().find({}, {"_id": 0})
    return list(cursor)


def get_unread_notifications(email: str) -> list:
    """Return unread notifications for a user (used by /api/notifications/unread)."""
    cursor = _notifications().find(
        {"user_email": email, "is_read": False},
        {"_id": 0}
    ).sort("created_at", DESCENDING).limit(20)
    return list(cursor)


def save_audit_log(entry: dict) -> None:
    """Persist an immutable audit log entry (used by backend_api.log_audit_action)."""
    _audit_logs().insert_one(entry)


def save_support_ticket(email: str, subject: str, message: str, ticket_id: str) -> None:
    """Save a support ticket to MongoDB (used by /api/support/ticket)."""
    import datetime as _dt
    _tickets().insert_one({
        "user_email": email,
        "ticket_id":  ticket_id,
        "subject":    subject,
        "message":    message,
        "status":     "open",
        "created_at": _dt.datetime.utcnow(),
    })


# ── Init on import ────────────────────────────────────────────────────────────
init_db()

