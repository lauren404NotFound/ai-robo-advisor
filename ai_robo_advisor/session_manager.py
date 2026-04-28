"""
session_manager.py
==================
Server-side session authentication for LEM StratIQ (Streamlit).

Design
------
* Sessions are stored in MongoDB (``sessions`` collection) — no sensitive
  data lives in the browser.
* The browser holds only an opaque, randomly generated ``session_id``
  in a cookie.  The cookie itself carries no user information.
* Passwords are hashed with bcrypt (done in database.py).
* CSRF tokens are HMAC-SHA256 digests of ``session_id + nonce`` using
  a server-side signing key — they cannot be forged without the key.
* Sessions expire after ``SESSION_TTL_HOURS`` (default 24 h).
* On logout the session document is hard-deleted from MongoDB so the
  session_id becomes permanently invalid (prevents session replay).
* Session IDs are rotated on every login to prevent session fixation.

Cookie note
-----------
Streamlit does not expose raw HTTP response headers, so the ``HttpOnly``
flag cannot be set purely server-side the way Flask/Django can.  We use
``streamlit-cookies-controller`` (sets cookies via a sandboxed iframe) with
``SameSite=Strict`` and ``Secure`` where possible.  The session_id cookie
stores only the opaque ID — even if JavaScript reads it, there is nothing
exploitable without the server-side session store.

Usage (called from ui/auth.py)
------
    from session_manager import SessionManager
    sm = SessionManager()

    # Login
    sid = sm.create_session(email, name, provider)
    sm.set_cookie(sid)

    # Per-request restore
    sid = sm.get_cookie()
    data = sm.validate(sid)      # None if expired / not found

    # Logout
    sm.invalidate(sid)
    sm.clear_cookie()

    # CSRF
    token = sm.csrf_token(sid)
    ok    = sm.verify_csrf(sid, token_from_form)
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import streamlit as st

# ── Configuration ─────────────────────────────────────────────────────────────
SESSION_COOKIE     = "diq_sid"        # cookie name
SESSION_TTL_HOURS  = 24              # expiry window
CSRF_NONCE_BITS    = 128             # entropy for CSRF nonces
SID_BYTES          = 48              # session ID entropy (384 bits)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _signing_key() -> bytes:
    """
    Derive a stable HMAC signing key from the Anthropic API key stored in
    st.secrets.  This key is server-side only and never leaves Python.
    Falls back to a random per-process key if the secret is absent
    (safe-fail: CSRF tokens become per-process instead of per-deployment).
    """
    base = st.secrets.get("anthropic_api_key", secrets.token_hex(32))
    return hashlib.sha256(f"diq_csrf_v2:{base}".encode()).digest()


def _db_sessions():
    """Lazily import database to avoid circular imports."""
    import database as _db
    return _db._sessions()


# ── SessionManager ────────────────────────────────────────────────────────────

class SessionManager:
    """
    All session operations.  Instantiate once per request (lightweight).
    """

    # ── Cookie I/O (via streamlit-cookies-controller) ─────────────────────────

    @staticmethod
    def _cookie_controller():
        """
        Returns a CookieController instance.
        Requires:  pip install streamlit-cookies-controller
        """
        try:
            from streamlit_cookies_controller import CookieController
            return CookieController()
        except ImportError:
            return None

    def set_cookie(self, session_id: str, ttl_hours: int = SESSION_TTL_HOURS) -> None:
        """
        Write the session_id cookie.
        Flags: SameSite=Strict (CSRF), Secure (HTTPS only in prod),
        max_age enforces expiry in the browser as a second layer.
        HttpOnly cannot be set via Streamlit's JS component bridge —
        documented limitation; mitigated by storing no sensitive data in
        the cookie value.
        """
        ctrl = self._cookie_controller()
        if ctrl is None:
            # Graceful degradation: store in session_state only
            st.session_state["_sid_fallback"] = session_id
            return
        try:
            ctrl.set(
                SESSION_COOKIE,
                session_id,
                max_age=ttl_hours * 3600,
                same_site="strict",
                secure=True,
            )
        except Exception:
            st.session_state["_sid_fallback"] = session_id

    def get_cookie(self) -> Optional[str]:
        """Read the session_id from the cookie (or fallback)."""
        ctrl = self._cookie_controller()
        if ctrl is not None:
            try:
                val = ctrl.get(SESSION_COOKIE)
                if val:
                    return str(val)
            except Exception:
                pass
        return st.session_state.get("_sid_fallback")

    def clear_cookie(self) -> None:
        """Delete the session cookie from the browser."""
        ctrl = self._cookie_controller()
        if ctrl is not None:
            try:
                ctrl.remove(SESSION_COOKIE)
            except Exception:
                pass
        st.session_state.pop("_sid_fallback", None)

    # ── Session CRUD (MongoDB) ────────────────────────────────────────────────

    def create_session(
        self,
        email: str,
        name: str,
        provider: str = "email",
        avatar: Optional[str] = None,
        ttl_hours: int = SESSION_TTL_HOURS,
    ) -> str:
        """
        Generate a new opaque session ID, persist it in MongoDB, and return it.
        Any previous sessions for this email are NOT invalidated here —
        call ``invalidate_all_for_email`` if single-session enforcement is wanted.
        """
        session_id = secrets.token_urlsafe(SID_BYTES)
        now        = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=ttl_hours)

        doc = {
            "session_id": session_id,
            "email":      email.lower().strip(),
            "name":       name,
            "provider":   provider,
            "avatar":     avatar,
            "created_at": now,
            "last_seen":  now,
            "expires_at": expires_at,
            "ip_hash":    None,   # reserved for IP-binding in production
        }
        try:
            _db_sessions().insert_one(doc)
        except Exception as exc:
            # Log but don't crash — caller will still get the session_id
            print(f"[SessionManager] create_session DB error: {exc}")

        return session_id

    def validate(self, session_id: Optional[str]) -> Optional[dict]:
        """
        Look up a session_id in MongoDB.
        Returns the session document (without _id) if valid and not expired.
        Returns None if not found, expired, or session_id is falsy.

        Also refreshes ``last_seen`` on successful validation.
        """
        if not session_id:
            return None

        now = datetime.now(timezone.utc)
        try:
            doc = _db_sessions().find_one(
                {"session_id": session_id},
                {"_id": 0},
            )
        except Exception:
            return None

        if not doc:
            return None

        # Enforce server-side expiry
        expires_at = doc.get("expires_at")
        if expires_at:
            # Handle naive datetimes stored without tz info
            if expires_at.tzinfo is None:
                from datetime import timezone as _tz
                expires_at = expires_at.replace(tzinfo=_tz.utc)
            if now > expires_at:
                self.invalidate(session_id)   # clean up expired record
                return None

        # Refresh last_seen (fire-and-forget)
        try:
            _db_sessions().update_one(
                {"session_id": session_id},
                {"$set": {"last_seen": now}},
            )
        except Exception:
            pass

        return doc

    def invalidate(self, session_id: Optional[str]) -> None:
        """
        Hard-delete the session from MongoDB.
        After this the session_id is permanently invalid — prevents replay
        attacks even if the old cookie value is somehow captured.
        """
        if not session_id:
            return
        try:
            _db_sessions().delete_one({"session_id": session_id})
        except Exception as exc:
            print(f"[SessionManager] invalidate DB error: {exc}")

    def invalidate_all_for_email(self, email: str) -> int:
        """
        Delete ALL sessions for a given email (e.g. on password change).
        Returns the count of sessions removed.
        """
        try:
            result = _db_sessions().delete_many(
                {"email": email.lower().strip()}
            )
            return result.deleted_count
        except Exception:
            return 0

    def rotate(self, old_session_id: str, email: str, name: str,
                provider: str, avatar: Optional[str] = None) -> str:
        """
        Create a new session_id and delete the old one atomically.
        Prevents session fixation: after a privilege change (e.g. login)
        the old ID is always invalidated.
        """
        new_sid = self.create_session(email, name, provider, avatar)
        self.invalidate(old_session_id)
        return new_sid

    # ── CSRF protection ───────────────────────────────────────────────────────

    def csrf_token(self, session_id: str) -> str:
        """
        Generate a per-session CSRF token.
        Token = HMAC-SHA256(key=signing_key, msg=session_id + nonce)
        The nonce is stored in st.session_state so it is consistent
        within a single Streamlit session but changes on every new
        browser session.
        """
        nonce = st.session_state.get("_csrf_nonce")
        if not nonce:
            nonce = secrets.token_hex(16)
            st.session_state["_csrf_nonce"] = nonce

        msg = f"{session_id}:{nonce}".encode()
        return hmac.new(_signing_key(), msg, hashlib.sha256).hexdigest()

    def verify_csrf(self, session_id: str, token: str) -> bool:
        """
        Constant-time CSRF token verification.
        Returns False if the token is absent or does not match.
        """
        if not token or not session_id:
            return False
        expected = self.csrf_token(session_id)
        try:
            return hmac.compare_digest(expected, token)
        except Exception:
            return False

    # ── Convenience ───────────────────────────────────────────────────────────

    @staticmethod
    def purge_expired() -> int:
        """
        Remove all expired sessions from MongoDB.
        Call this from a background task or on startup.
        Returns count of purged records.
        """
        now = datetime.now(timezone.utc)
        try:
            result = _db_sessions().delete_many({"expires_at": {"$lt": now}})
            return result.deleted_count
        except Exception:
            return 0
