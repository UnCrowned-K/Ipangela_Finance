"""
Blueprint package for the Profit Optimizer Flask application.

Each module registers a ``Blueprint`` covering a logical group of routes:

- auth: login, logout, register (+ login rate limiting)
- pages: home, about, contact, profile, exports, saved, imports and downloads
- optimizer: ILP variable management and file import/export
- invoice: invoice CRUD, PDF/email generation
- finance: finance dashboard + JSON API
"""

from .auth import auth_bp
from .pages import pages_bp
from .optimizer import optimizer_bp
from .invoice import invoice_bp
from .finance import finance_bp

__all__ = ['auth_bp', 'pages_bp', 'optimizer_bp', 'invoice_bp', 'finance_bp']