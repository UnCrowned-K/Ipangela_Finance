"""
Authentication blueprint: login, logout, register and login rate limiting.
"""

import time
from collections import defaultdict, deque

from flask import Blueprint, render_template, request, flash, redirect, url_for, session

auth_bp = Blueprint('auth', __name__)


# Login rate limiting. Kept in memory for the running process but seeded from
# storage on first use and written through on every change, so a restart does
# not hand an attacker a fresh budget.
# shortcut: seeding happens once per process - separate worker processes keep
# their own view until they restart.
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300  # 5 minutes
_login_attempts = defaultdict(deque)  # client key -> timestamps of failures
_attempts_loaded = False


def _prune(attempts: deque) -> None:
    now = time.time()
    while attempts and now - attempts[0] > LOGIN_WINDOW_SECONDS:
        attempts.popleft()


def _seed_from_storage(storage) -> None:
    global _attempts_loaded
    if _attempts_loaded:
        return
    for key, stamps in storage.get_login_attempts().items():
        _login_attempts[key] = deque(stamps)
    _attempts_loaded = True


def _persist(storage) -> None:
    for attempts in _login_attempts.values():
        _prune(attempts)
    storage.save_login_attempts(
        {key: list(v) for key, v in _login_attempts.items() if v}
    )


def _is_login_rate_limited(client_key: str, storage) -> bool:
    """Return True if the client has exceeded the login attempt window."""
    _seed_from_storage(storage)
    attempts = _login_attempts.get(client_key)
    if not attempts:
        return False
    _prune(attempts)
    return len(attempts) >= MAX_LOGIN_ATTEMPTS


def _record_login_failure(client_key: str, storage) -> None:
    _login_attempts[client_key].append(time.time())
    _persist(storage)


def _clear_login_attempts(client_key: str, storage) -> None:
    _login_attempts.pop(client_key, None)
    _persist(storage)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    if request.method == "POST":
        from finance_core import UserManager, DataStorage
        storage = DataStorage()
        client_key = request.remote_addr or 'unknown'
        if _is_login_rate_limited(client_key, storage):
            flash("Too many failed login attempts. Please try again later.", "error")
            return render_template("login.html"), 429

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user_manager = UserManager(storage)
        user = user_manager.authenticate(username, password)
        if user:
            _clear_login_attempts(client_key, storage)
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Logged in successfully!", "success")
            return redirect(url_for("finance.finance"))
        else:
            _record_login_failure(client_key, storage)
            flash("Invalid username or password", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Logout and clear session."""
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("pages.home"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Registration page."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password:
            flash("Username and password are required", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("register.html")

        from finance_core import UserManager, DataStorage
        storage = DataStorage()
        user_manager = UserManager(storage)

        try:
            user = user_manager.register(username, password)
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash(str(e), "error")

    return render_template("register.html")