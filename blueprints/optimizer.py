"""
Optimizer blueprint: ILP variable management, optimization and file import/export.
"""

import json
import os

from flask import (
    Blueprint, render_template, request, flash, redirect, url_for,
    send_file, session, current_app
)
import pandas as pd

from config import Config
from optimizer_core import IntegerVariable, create_integer_variable, optimize, OptimizationError
from .helpers import parse_variable_form, handle_file_operation, safe_filename
from . import optimizer_state

optimizer_bp = Blueprint('optimizer', __name__)


@optimizer_bp.route("/optimizer.html", methods=["GET", "POST"])
def optimizer():
    """Handle main page and form submissions."""
    # Get data from server-side storage
    state = optimizer_state.load_state_for(session.get('user_id'))
    budget = state['budget'] if state['budget'] is not None else Config.DEFAULT_BUDGET
    variables_dicts = state['variables']
    variables = [IntegerVariable.from_dict(d) for d in variables_dicts]

    max_profit = None
    result = {}

    if request.method == "POST":
        if "update_budget" in request.form:
            try:
                new_budget = int(request.form["budget"])
                if new_budget <= 0:
                    raise ValueError("Budget must be positive")
                budget = new_budget
                optimizer_state.set_budget(new_budget)
                flash("Budget updated successfully!", "success")
            except ValueError as e:
                flash(f"Invalid budget value: {str(e)}", "error")

        elif "add_variable" in request.form:
            data, valid = parse_variable_form()
            if valid:
                try:
                    var = create_integer_variable(**data)
                    variables_dicts = optimizer_state.get_variables()
                    variables_dicts.append(var.to_dict())
                    optimizer_state.set_variables(variables_dicts)
                    variables = [IntegerVariable.from_dict(d) for d in variables_dicts]
                    flash("Variable added successfully!", "success")
                except OptimizationError as e:
                    flash(str(e), "error")

        elif "optimize" in request.form:
            if not variables:
                flash("No items to optimize. Add items first.", "error")
            else:
                try:
                    max_profit, result = optimize(variables, budget)
                    optimizer_state.increment_optimizations()
                    flash("Optimization completed successfully!", "success")
                except OptimizationError as e:
                    flash(f"Optimization failed: {str(e)}", "error")

    return render_template("optimizer.html", variables=variables, max_profit=max_profit, result=result, budget=budget)


@optimizer_bp.route("/export", methods=["POST"])
def export_variables():
    """Export variables to a file in the exports folder."""
    try:
        filename = request.form.get("filename", "variables")
        format_type = request.form.get("format", "csv")
        # Ensure filename has correct extension
        if not filename.endswith(f".{format_type}"):
            filename = f"{filename}.{format_type}"
        filepath = os.path.join(current_app.config['EXPORT_FOLDER'], filename)
        handle_file_operation('save', filepath)
        flash(f"Table exported successfully as {format_type.upper()}!", "success")
    except Exception as e:
        flash(f"Export failed: {str(e)}", "error")
    return redirect(url_for("optimizer.optimizer"))


@optimizer_bp.route("/import", methods=["POST"])
def import_variables():
    """Import variables from an uploaded JSON file."""
    if "file" not in request.files:
        flash("No file selected for importing.", "error")
        return redirect(url_for("optimizer.optimizer"))

    file = request.files["file"]
    if not file.filename:
        flash("No file selected for importing.", "error")
        return redirect(url_for("optimizer.optimizer"))

    try:
        filename = safe_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        handle_file_operation('load', filepath)
        flash("Variables imported successfully!", "success")
    except Exception as e:
        flash(f"Import failed: {str(e)}", "error")

    return redirect(url_for("optimizer.optimizer"))


@optimizer_bp.route("/download", methods=["POST"])
def download_variables():
    """Download variables as a file in the selected format."""
    try:
        filename = request.form.get("filename", "variables").strip()
        format_type = request.form.get("format", "csv")
        # Ensure filename has correct extension
        if not filename.endswith(f".{format_type}"):
            filename = f"{filename}.{format_type}"
        filepath = os.path.join(current_app.config['EXPORT_FOLDER'], filename)
        handle_file_operation('save', filepath)
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        flash(f"Download failed: {str(e)}", "error")
        return redirect(url_for("optimizer.optimizer"))


@optimizer_bp.route("/save", methods=["POST"])
def save_variables():
    """Save variables to the saved folder without downloading."""
    try:
        filename = request.form.get("filename", "variables").strip()
        format_type = request.form.get("format", "csv")
        # Ensure filename has correct extension
        if not filename.endswith(f".{format_type}"):
            filename = f"{filename}.{format_type}"
        filepath = os.path.join(current_app.config['SAVED_FOLDER'], filename)
        handle_file_operation('save', filepath)
        flash(f"File '{filename}' saved successfully to saved folder!", "success")
    except Exception as e:
        flash(f"Save failed: {str(e)}", "error")
    return redirect(url_for("pages.saved"))


@optimizer_bp.route("/save_results", methods=["POST"])
def save_results():
    """Save optimization results to the saved folder."""
    try:
        filename = request.form.get("filename", "results").strip()
        format_type = request.form.get("format", "csv")
        data_json = request.form.get("data", "[]")

        # Parse the JSON data
        data = json.loads(data_json)

        # Ensure filename has correct extension
        if not filename.endswith(f".{format_type}"):
            filename = f"{filename}.{format_type}"

        filepath = os.path.join(current_app.config['SAVED_FOLDER'], filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Create DataFrame from the data
        df = pd.DataFrame(data)

        # Save to file based on format
        if format_type == 'csv':
            df.to_csv(filepath, index=False)
        elif format_type in ['xlsx', 'xls']:
            df.to_excel(filepath, index=False)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

        return {'success': True, 'message': f"Results saved as '{filename}'"}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@optimizer_bp.route("/delete_variable/<name>", methods=["POST"])
def delete_variable(name):
    """Delete a variable by its name."""
    try:
        variables_dicts = optimizer_state.get_variables()
        variables_dicts = [d for d in variables_dicts if d.get('name') != name]
        optimizer_state.set_variables(variables_dicts)
        flash(f"Variable '{name}' deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting variable: {str(e)}", "error")

    return redirect(url_for("optimizer.optimizer"))


@optimizer_bp.route("/clear_variables", methods=["POST"])
def clear_all_variables():
    """Clear all variables from the optimizer state."""
    try:
        optimizer_state.clear_state()
        flash("All items cleared successfully!", "success")
    except Exception as e:
        flash(f"Error clearing items: {str(e)}", "error")

    return redirect(url_for("optimizer.optimizer"))


@optimizer_bp.route("/update_variable", methods=["POST"])
def update_variable():
    """Update an existing variable."""
    try:
        old_name = request.form.get('old_name')
        if not old_name:
            return {'status': 'error', 'message': 'Original variable name is required'}, 400

        variables_dicts = optimizer_state.get_variables()
        # Find the old variable
        old_var_dict = next((d for d in variables_dicts if d.get('name') == old_name), None)
        if not old_var_dict:
            return {'status': 'error', 'message': f'Variable {old_name} not found'}, 404

        data, valid = parse_variable_form()
        if not valid:
            return {'status': 'error', 'message': 'Invalid input data'}, 400

        # Check if new name is unique (excluding the old variable)
        if data['name'] != old_name:
            if any(d.get('name') == data['name'] for d in variables_dicts if d.get('name') != old_name):
                return {'status': 'error', 'message': f'An item named {data["name"]} already exists'}, 400

        # Create new variable
        new_var = create_integer_variable(**data)
        # Remove old variable, add new one
        variables_dicts = [d for d in variables_dicts if d.get('name') != old_name]
        variables_dicts.append(new_var.to_dict())
        optimizer_state.set_variables(variables_dicts)
        flash("Item updated successfully!", "success")
        return {'status': 'success'}, 200

    except ValueError as e:
        return {'status': 'error', 'message': f'Invalid value: {str(e)}'}, 400
    except Exception as e:
        flash(f"Error updating variable: {str(e)}", "error")
        return {'status': 'error', 'message': str(e)}, 500