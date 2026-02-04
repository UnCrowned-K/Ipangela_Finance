"""
1B-PuLP-B-flask/app.py

Flask web application for managing and solving integer linear programming (ILP) problems.
Provides a user interface for defining variables, setting constraints, and running optimizations.

Features:
- Add, import, export, and download optimization variables.
- Set budget constraints and maximize profit.
- Clean separation of concerns (web UI, optimization logic, configuration).

@author: Bongani
@date: 2025-06-14
"""

import os
import json
import threading
import time
import webbrowser
from typing import Tuple, Dict, Any, Optional
from flask import Flask, render_template, request, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from optimizer_core import (
    IntegerVariable, create_integer_variable, optimize, variables_list,
    clear_variables, OptimizationError
)
from config import Config

def create_app(config_class=Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    return app

app = create_app()
budget = Config.DEFAULT_BUDGET

def safe_filename(filename: str) -> str:
    """Generate a secure filename and ensure .json extension."""
    filename = secure_filename(filename)
    if not filename.endswith('.json'):
        filename += '.json'
    return filename

def handle_file_operation(operation: str, filepath: str, variables: Optional[list] = None) -> None:
    """Handle file operations with error checking for serverless environment."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        if operation == 'save':
            with open(filepath, 'w') as f:
                json.dump([var.to_dict() for var in variables or variables_list], f, indent=4)
        elif operation == 'load':
            if not os.path.exists(filepath):
                raise IOError(f"File not found: {filepath}")
            with open(filepath, 'r') as f:
                data = json.load(f)
                clear_variables()
                for item in data:
                    var = IntegerVariable.from_dict(item)
                    var.validate()
                    variables_list.append(var)
    except Exception as e:
        error_msg = f"Error {operation}ing variables: {str(e)}"
        if 'VERCEL' in os.environ:
            error_msg += " (Serverless filesystem may be ephemeral)"
        raise IOError(error_msg)

def parse_variable_form() -> Tuple[Dict[str, Any], bool]:
    """Parse and validate variable form data."""
    try:
        data = {
            'name': request.form['name'],
            'lowerBound': int(request.form['lowerBound']) if request.form['lowerBound'] else 0,
            'upperBound': int(request.form['upperBound']) if request.form['upperBound'] else None,
            'cost': float(request.form['cost']),
            'profit': float(request.form['profit']),
            'multiplier': int(request.form['multiplier'])
        }
        return data, True
    except ValueError as e:
        flash(f"Invalid input: {str(e)}", "error")
        return {}, False

# Routes
@app.route("/optimizer.html", methods=["GET", "POST"])
def optimizer():
    """Handle main page and form submissions."""
    global budget
    max_profit = None
    result = {}

    if request.method == "POST":
        if "update_budget" in request.form:
            try:
                new_budget = int(request.form["budget"])
                if new_budget <= 0:
                    raise ValueError("Budget must be positive")
                budget = new_budget
                flash("Budget updated successfully!", "success")
            except ValueError as e:
                flash(f"Invalid budget value: {str(e)}", "error")
        
        elif "add_variable" in request.form:
            data, valid = parse_variable_form()
            if valid:
                try:
                    create_integer_variable(**data)
                    flash("Variable added successfully!", "success")
                except OptimizationError as e:
                    flash(str(e), "error")
        
        elif "optimize" in request.form:
            if not variables_list:
                flash("No items to optimize. Add items first.", "error")
            else:
                try:
                    max_profit, result = optimize(variables_list, budget)
                    flash("Optimization completed successfully!", "success")
                except OptimizationError as e:
                    flash(f"Optimization failed: {str(e)}", "error")

    return render_template("optimizer.html",variables=variables_list, max_profit=max_profit, result=result, budget=budget)

@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")

@app.route("/finance", methods=["GET"])
def finance():
    return render_template("finance.html")

@app.route("/invoice",methods=["GET"])
def invoice():
    return render_template("invoice.html")

@app.route("/about", methods=["GET"])
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET"])
def contact():
    return render_template("contact.html")

@app.route("/export", methods=["POST"])
def export_variables():
    """Export variables to a JSON file in the exports folder."""
    try:
        filename = safe_filename(request.form.get("filename", "variables.json"))
        filepath = os.path.join(app.config['EXPORT_FOLDER'], filename)
        handle_file_operation('save', filepath)
        flash(f"Table exported successfully!", "success")
        # return send_file(filepath, as_attachment=True, export_name=filename)
    except Exception as e:
        flash(f"Export failed: {str(e)}", "error")
    return redirect(url_for("optimizer"))

@app.route("/import", methods=["POST"])
def import_variables():
    """Import variables from an uploaded JSON file."""
    if "file" not in request.files:
        flash("No file selected for importing.", "error")
        return redirect(url_for("optimizer"))

    file = request.files["file"]
    if not file.filename:
        flash("No file selected for importing.", "error")
        return redirect(url_for("optimizer"))

    try:
        filename = safe_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        handle_file_operation('load', filepath)
        flash("Variables imported successfully!", "success")
    except Exception as e:
        flash(f"Import failed: {str(e)}", "error")
    
    return redirect(url_for("optimizer"))

@app.route("/download", methods=["POST"])
def download_variables():
    """Download variables as a JSON file."""
    try:
        filename = safe_filename(request.form.get("filename", "variables.json").strip())
        filepath = os.path.join(app.config['EXPORT_FOLDER'], filename)
        handle_file_operation('save', filepath)
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        flash(f"Download failed: {str(e)}", "error")
        return redirect(url_for("optimizer"))

@app.route("/delete_variable/<name>", methods=["POST"])
def delete_variable(name):
    """Delete a variable by its name."""
    global variables_list
    try:
        # Find and remove the variable with the given name
        variables_list = [var for var in variables_list if var.name != name]
        flash(f"Variable '{name}' deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting variable: {str(e)}", "error")
    
    return redirect(url_for("optimizer"))

@app.route("/update_variable", methods=["POST"])
def update_variable():
    """Update an existing variable."""
    global variables_list
    try:
        old_name = request.form.get('old_name')
        if not old_name:
            return {'status': 'error', 'message': 'Original variable name is required'}, 400

        # Find the variable we're updating
        old_var = next((var for var in variables_list if var.name == old_name), None)
        if not old_var:
            return {'status': 'error', 'message': f'Variable {old_name} not found'}, 404

        data, valid = parse_variable_form()
        if not valid:
            return {'status': 'error', 'message': 'Invalid input data'}, 400

        # If we're not changing the name, or if the new name is available
        if data['name'] == old_name or not any(var.name == data['name'] for var in variables_list if var.name != old_name):
            # Create new variable instance to validate before removing old one
            new_var = IntegerVariable(**data)
            new_var.validate()
            
            # Remove the old variable first
            variables_list = [var for var in variables_list if var.name != old_name]
            # Add the new variable
            variables_list.append(new_var)
            flash("Item updated successfully!", "success")
            return {'status': 'success'}, 200
        else:
            return {'status': 'error', 'message': f'An item named {data["name"]} already exists'}, 400
        
    except ValueError as e:
        return {'status': 'error', 'message': f'Invalid value: {str(e)}'}, 400
    except Exception as e:
        flash(f"Error updating variable: {str(e)}", "error")
        return {'status': 'error', 'message': str(e)}, 500

def run_app(port: int = 5000, debug: bool = True):
    """Run the Flask application with browser auto-open."""
    url = f"http://localhost:{port}"
    def open_browser():
        time.sleep(1)
        webbrowser.open(url)
    
    if not debug:
        threading.Thread(target=open_browser).start()
    
    app.run(debug=debug, use_reloader=False, port=port)

# Vercel Serverless Function Entry Point
def vercel_serverless(request):
    """
    Entry point for Vercel serverless function.
    Handles the request and returns a response compatible with Vercel's serverless environment.
    """
    from flask import Request
    
    # Create a Flask request object from the Vercel request
    if isinstance(request, dict):
        # Handle Vercel HTTP request format
        environ = {
            'REQUEST_METHOD': request.get('method', 'GET'),
            'PATH_INFO': request.get('path', '/'),
            'QUERY_STRING': request.get('query', ''),
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '80',
            'wsgi.input': request.get('body', b''),
            'CONTENT_TYPE': request.get('headers', {}).get('content-type', ''),
            'CONTENT_LENGTH': str(len(request.get('body', b'')))
        }
        # Add headers to environ
        for key, value in request.get('headers', {}).items():
            if key.upper().startswith('HTTP_'):
                environ[key.upper()] = value
        
        flask_request = Request(environ)
    else:
        # Handle direct Flask request (for testing)
        flask_request = request
    
    # Process the request through the Flask app
    with app.test_request_context(
        path=flask_request.path,
        method=flask_request.method,
        headers=flask_request.headers,
        data=flask_request.data,
        query_string=flask_request.query_string
    ):
        # Dispatch the request to the appropriate route
        response = app.full_dispatch_request()
        
        # Convert Flask response to Vercel-compatible format
        return {
            'statusCode': response.status_code,
            'headers': dict(response.headers),
            'body': response.get_data(as_text=True)
        }

if __name__ == "__main__":
    run_app()
