"""
Pages blueprint: static informational pages, file listing pages and downloads.
"""

import os

from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, send_file, current_app
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