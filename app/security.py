"""Authentication helpers, CSRF protection and a tiny login rate-limiter."""
import secrets
import time
from functools import wraps
from flask import abort, current_app, g, jsonify, redirect, request, session, url_for
from .db import get_db


def load_user():
    g.user = None
    uid = session.get("user_id")
    if uid:
        g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if g.user is None:
            session.clear()


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify(error="Authentication required"), 401
            return redirect(url_for("auth.login", next=request.path))
        return view(*a, **kw)
    return wrapped


def safe_next(target):
    """Prevent open-redirect attacks: only allow local paths."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("main.home")


# ---------------- CSRF ----------------
def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def check_csrf():
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
            if request.path.startswith("/api/"):
                return jsonify(error="Invalid or missing CSRF token"), 400
            abort(400, "Invalid or missing CSRF token. Please refresh the page and try again.")


# ---------------- login throttling (per application instance, in memory) ----------------
def _attempts():
    return current_app.extensions.setdefault("login_attempts", {})


def too_many_attempts(key):
    now = time.time()
    recent = [t for t in _attempts().get(key, []) if now - t < 300]
    _attempts()[key] = recent
    return len(recent) >= current_app.config["MAX_LOGIN_ATTEMPTS"]


def record_failed_attempt(key):
    _attempts().setdefault(key, []).append(time.time())


def clear_attempts(key):
    _attempts().pop(key, None)
