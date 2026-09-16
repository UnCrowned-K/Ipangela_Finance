"""
Pages blueprint: static informational pages, file listing pages and downloads.
"""

import os
from datetime import datetime

from flask import (
    Blueprint, render_template, request, flash, redirect, url_for,
    send_file, current_app, session, jsonify
)

from .helpers import _safe_filepath

pages_bp = Blueprint('pages', __name__)


def _list_files(folder_name: str, config_key: str) -> list:
    folder = current_app.config.get(config_key, folder_name)
    files = []
    if os.path.exists(folder):
        for f in os.listdir(folder):
            filepath = os.path.join(folder, f)
            if os.path.isfile(filepath):
                files.append({
                    'name': f,
                    'size': os.path.getsize(filepath),
                    'path': filepath
                })
    return files


@pages_bp.route("/", methods=["GET"])
def home():
    """Home page."""
    return render_template("home.html")


@pages_bp.route("/about", methods=["GET"])
def about():
    """About page."""
    return render_template("about.html")


@pages_bp.route("/contact", methods=["GET"])
def contact():
    """Contact page."""
    return render_template("contact.html")


@pages_bp.route("/profile", methods=["GET"])
def profile():
    """Profile page."""
    return render_template("profile.html")


@pages_bp.route("/exports", methods=["GET"])
def exports():
    """Show exports folder contents."""
    files = _list_files('exports', 'EXPORT_FOLDER')
    export_folder = current_app.config.get('EXPORT_FOLDER', 'exports')
    return render_template("exports.html", files=files, export_folder=export_folder)


@pages_bp.route("/saved", methods=["GET"])
def saved():
    """Show saved folder contents."""
    files = _list_files('saved', 'SAVED_FOLDER')
    saved_folder = current_app.config.get('SAVED_FOLDER', 'saved')
    return render_template("saved.html", files=files, saved_folder=saved_folder)


@pages_bp.route("/imports", methods=["GET"])
def imports():
    """Show uploaded files."""
    files = _list_files('uploads', 'UPLOAD_FOLDER')
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    return render_template("imports.html", files=files, upload_folder=upload_folder)


@pages_bp.route("/download_uploaded/<filename>", methods=["GET"])
def download_uploaded_file(filename):
    """Download a file from the uploads folder."""
    folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    filepath = _safe_filepath(folder, filename)
    if filepath and os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))
    flash("File not found", "error")
    return redirect(url_for("pages.imports"))


@pages_bp.route("/download_file/<filename>", methods=["GET"])
def download_file(filename):
    """Download a file from the exports folder."""
    folder = current_app.config.get('EXPORT_FOLDER', 'exports')
    filepath = _safe_filepath(folder, filename)
    if filepath and os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))
    flash("File not found", "error")
    return redirect(url_for("pages.exports"))


@pages_bp.route("/download_saved/<filename>", methods=["GET"])
def download_saved_file(filename):
    """Download a file from the saved folder."""
    folder = current_app.config.get('SAVED_FOLDER', 'saved')
    filepath = _safe_filepath(folder, filename)
    if filepath and os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))
    flash("File not found", "error")
    return redirect(url_for("pages.saved"))


@pages_bp.route("/api/profile", methods=["GET"])
def api_profile_get():
    """Return profile data and real stats for the current user."""
    user_id = session.get('user_id')
    if not user_id:
        return {'success': False, 'message': 'Authentication required'}, 401

    from finance_core import UserManager, DataStorage
    import threading
    um = UserManager(DataStorage())
    user = um.get_user(user_id)
    if not user:
        return {'success': False, 'message': 'User not found'}, 404

    profile = um.get_profile(user_id)

    # --- Real stats --------------------------------------------------------
    # Invoices created: count JSON files in this user's invoice directory
    invoice_root = current_app.config.get(
        'INVOICE_STORAGE_FOLDER',
        os.path.join(current_app.root_path, 'invoices')
    )
    invoice_dir = os.path.join(invoice_root, str(user_id))
    invoice_count = 0
    if os.path.isdir(invoice_dir):
        invoice_count = sum(
            1 for f in os.listdir(invoice_dir) if f.endswith('.json')
        )

    # Optimizations run: from per-user optimizer state
    from . import optimizer_state as _opt_state
    optimizations_run = _opt_state.get_optimizations_run()

    # Months active
    try:
        created = datetime.fromisoformat(user['created_at'])
        now = datetime.now()
        months = (now.year - created.year) * 12 + (now.month - created.month)
    except (KeyError, ValueError):
        months = 0

    return {
        'success': True,
        'data': {
            'username': user.get('username', ''),
            'email': user.get('email', '') or '',
            'name': profile.get('name', ''),
            'company': profile.get('company', ''),
            'preferences': {
                'email_notifications': bool(profile.get('email_notifications', True)),
                'dark_mode': bool(profile.get('dark_mode', False)),
                'auto_save': bool(profile.get('auto_save', True)),
                'two_factor': bool(profile.get('two_factor', False)),
            },
            'stats': {
                'invoices': invoice_count,
                'optimizations': optimizations_run,
                'months_active': max(months, 0),
            },
            'created_at': user.get('created_at', ''),
        }
    }


@pages_bp.route("/api/profile", methods=["POST"])
def api_profile_post():
    """Update profile data for the current user."""
    user_id = session.get('user_id')
    if not user_id:
        return {'success': False, 'message': 'Authentication required'}, 401

    data = request.get_json() or {}
    from finance_core import UserManager, DataStorage
    um = UserManager(DataStorage())
    try:
        updated = um.update_profile(
            user_id,
            name=data.get('name', ''),
            company=data.get('company', ''),
            email_notifications=data.get('email_notifications'),
            dark_mode=data.get('dark_mode'),
            auto_save=data.get('auto_save'),
            two_factor=data.get('two_factor'),
        )
        return {'success': True, 'profile': updated}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400