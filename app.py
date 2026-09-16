"""
Profit Optimizer - Flask Web Application

Flask web application for managing invoices, ILP problems, and financial optimizations.
Provides user interfaces for defining variables, setting constraints, running optimizations,
and creating/managing invoices.

Features:
- Invoice creation, editing, and management
- PDF generation for invoices
- Email sending capabilities
- Integer Linear Programming (ILP) optimization
- Clean separation of concerns (web UI, blueprint packages, optimization logic, configuration)

@author: Bongani
@date: 2025-06-14
"""

import threading
import time
import webbrowser

from flask import Flask, redirect, request, session, url_for, flash, render_template
from flask_wtf import CSRFProtect

from config import Config

# Re-exported names imported by the test suite / callers.
from blueprints.auth import MAX_LOGIN_ATTEMPTS, LOGIN_WINDOW_SECONDS, _login_attempts
from blueprints.helpers import export_to_file


ERROR_MESSAGES = {
    400: ("Bad Request", "The request could not be understood by the server."),
    403: ("Access Denied", "You do not have permission to access this resource."),
    404: ("Page Not Found", "The page you are looking for does not exist."),
    405: ("Method Not Allowed", "This method is not allowed for the requested resource."),
    500: ("Internal Server Error", "Something went wrong on our end. Please try again."),
}


def _is_api_request() -> bool:
    """True when the request expects a JSON error response."""
    if request.path.startswith('/api/'):
        return True
    accept = request.headers.get('Accept', '')
    return 'application/json' in accept


def _render_or_json(status: int, error_title: str, error_message: str):
    """Render a consistent HTML error page, or JSON for API requests."""
    payload = {
        'error': error_title,
        'message': error_message,
    }
    if _is_api_request():
        return {'success': False, **payload, 'code': status}, status
    return render_template(
        'error.html',
        error_code=status,
        error_title=error_title,
        error_message=error_message,
    ), status


def _register_error_handlers(app: Flask) -> None:
    """Register consistent error handlers for the whole application."""
    def make_status_handler(status: int):
        def handler(error):
            title, message = ERROR_MESSAGES[status]
            return _render_or_json(status, title, message)
        handler.__name__ = f'handle_{status}'
        return handler

    for status in (400, 403, 404, 405):
        app.register_error_handler(status, make_status_handler(status))

    def handle_server_error(error):
        app.logger.exception("Unhandled exception on %s %s: %s",
                             request.method, request.path, error)
        title, message = ERROR_MESSAGES[500]
        return _render_or_json(500, title, message)

    app.register_error_handler(500, handle_server_error)
    app.register_error_handler(Exception, handle_server_error)


def create_app(config_class=Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    config_class.init_app(app)

    # Configure session
    app.secret_key = app.config.get('SECRET_KEY', 'dev-secret-key')

    # CSRF protection for all state-changing requests.
    csrf = CSRFProtect()
    csrf.init_app(app)

    from blueprints.auth import auth_bp
    from blueprints.pages import pages_bp
    from blueprints.optimizer import optimizer_bp
    from blueprints.invoice import invoice_bp
    from blueprints.finance import finance_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(optimizer_bp)
    app.register_blueprint(invoice_bp)
    app.register_blueprint(finance_bp)

    _register_error_handlers(app)

    @app.before_request
    def require_login():
        """Require authentication for all routes except public endpoints."""
        if request.endpoint is None or request.endpoint in PUBLIC_ENDPOINTS:
            return None
        if 'user_id' in session:
            return None
        if request.path.startswith('/api/'):
            return {'success': False, 'message': 'Authentication required'}, 401
        flash("Please log in to access this page.", "error")
        return redirect(url_for("auth.login"))

    return app


app = create_app()


PUBLIC_ENDPOINTS = {
    'static',
    'pages.home', 'pages.about', 'pages.contact',
    'auth.login', 'auth.logout', 'auth.register',
}


def run_app(port: int = 5000, debug: bool = True):
    """Run the Flask application with browser auto-open."""
    url = f"http://localhost:{port}"
    def open_browser():
        time.sleep(1)
        webbrowser.open(url)

    if not debug:
        threading.Thread(target=open_browser).start()

    app.run(debug=debug, use_reloader=False, port=port)


if __name__ == "__main__":
    run_app()