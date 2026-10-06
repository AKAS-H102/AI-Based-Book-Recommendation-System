"""Registration, login, logout."""
import re
import sqlite3
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from .db import get_db
from .security import clear_attempts, record_failed_attempt, safe_next, too_many_attempts
from .services import all_genres

bp = Blueprint("auth", __name__)
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_registration(username, email, password, confirm):
    errors = []
    if not USERNAME_RE.match(username):
        errors.append("Username must be 3-30 characters: letters, numbers, underscore.")
    if not EMAIL_RE.match(email) or len(email) > 120:
        errors.append("Please enter a valid email address.")
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        errors.append("Password must be at least 8 characters and contain a letter and a number.")
    if password != confirm:
        errors.append("Passwords do not match.")
    return errors


@bp.route("/register", methods=["GET", "POST"])
def register():
    db = get_db()
    genres = all_genres(db)
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        chosen = [g for g in request.form.getlist("genres") if g in genres]
        errors = validate_registration(username, email, password, confirm)
        if not errors:
            try:
                cur = db.execute(
                    "INSERT INTO users(username, email, password_hash, preferred_genres) VALUES (?,?,?,?)",
                    (username, email, generate_password_hash(password), ";".join(chosen)))
                db.commit()
                session.clear()
                session["user_id"] = cur.lastrowid
                session.permanent = True
                flash("Welcome! Your account has been created.", "success")
                return redirect(url_for("main.recommendations") if chosen else url_for("main.home"))
            except sqlite3.IntegrityError:
                errors.append("That username or email is already registered.")
        for e in errors:
            flash(e, "error")
        return render_template("register.html", genres=genres, form=request.form), 400 if errors else 200
    return render_template("register.html", genres=genres, form=request.form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ident = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        key = f"{request.remote_addr}:{ident.lower()}"
        if too_many_attempts(key):
            flash("Too many failed attempts. Please wait a few minutes and try again.", "error")
            return render_template("login.html"), 429
        user = get_db().execute("SELECT * FROM users WHERE username = ? OR email = ?", (ident, ident.lower())).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            clear_attempts(key)
            session.clear()                       # prevents session fixation
            session["user_id"] = user["id"]
            session.permanent = True
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(safe_next(request.args.get("next")))
        record_failed_attempt(key)
        flash("Invalid username/email or password.", "error")
        return render_template("login.html"), 401
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.home"))
