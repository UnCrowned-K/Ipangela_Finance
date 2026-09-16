"""
Shared helpers used across the Profit Optimizer blueprints.
"""

import json
import os
from functools import wraps
from typing import Tuple, Dict, Any, Optional

from flask import request, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
import pandas as pd

from optimizer_core import IntegerVariable
from utils import ValidationUtils
from . import optimizer_state


def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return {'success': False, 'message': 'Authentication required'}, 401
            flash("Please log in to access this page.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def safe_filename(filename: str) -> str:
    """Generate a secure filename and ensure valid extension."""
    filename = secure_filename(filename)
    # Allow .json, .csv, .xlsx extensions
    allowed_extensions = ['.json', '.csv', '.xlsx']
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        filename += '.json'
    return filename


def _safe_filepath(folder: str, filename: str) -> Optional[str]:
    """Return an absolute path inside `folder` or None if the filename isn't safe."""
    safe = secure_filename(filename)
    if not safe:
        return None
    allowed = ('.json', '.csv', '.xlsx')
    if not safe.lower().endswith(allowed):
        return None
    resolved = os.path.realpath(os.path.join(folder, safe))
    if resolved.startswith(os.path.realpath(folder)):
        return resolved
    return None


def parse_file(filepath: str) -> list:
    """
    Parse CSV, Excel, or JSON files and return list of variable dictionaries.

    Args:
        filepath: Path to the file to parse

    Returns:
        List of dictionaries representing IntegerVariable data
    """
    ext = filepath.lower().split('.')[-1]

    if ext == 'json':
        with open(filepath, 'r') as f:
            return json.load(f)
    elif ext == 'csv':
        df = pd.read_csv(filepath)
        # Convert DataFrame to list of dicts, handling NaN values
        data = df.to_dict('records')
        # Clean up None/NaN values for optional fields
        for item in data:
            if 'upperBound' in item and (pd.isna(item['upperBound']) or item['upperBound'] == 'None' or item['upperBound'] == ''):
                item['upperBound'] = None
            elif 'upperBound' in item and item['upperBound'] is not None:
                item['upperBound'] = int(item['upperBound'])
            if 'lowerBound' in item and pd.isna(item['lowerBound']):
                item['lowerBound'] = 0
            if 'multiplier' in item and pd.isna(item['multiplier']):
                item['multiplier'] = 1
        return data
    elif ext in ['xlsx', 'xls']:
        df = pd.read_excel(filepath)
        # Convert DataFrame to list of dicts, handling NaN values
        data = df.to_dict('records')
        # Clean up None/NaN values for optional fields
        for item in data:
            if 'upperBound' in item and (pd.isna(item['upperBound']) or item['upperBound'] == 'None' or item['upperBound'] == ''):
                item['upperBound'] = None
            elif 'upperBound' in item and item['upperBound'] is not None:
                item['upperBound'] = int(item['upperBound'])
            if 'lowerBound' in item and pd.isna(item['lowerBound']):
                item['lowerBound'] = 0
            if 'multiplier' in item and pd.isna(item['multiplier']):
                item['multiplier'] = 1
        return data
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def export_to_file(variables: list, filepath: str) -> None:
    """
    Export variables to JSON, CSV, or Excel file.

    Args:
        variables: List of IntegerVariable objects
        filepath: Path to save the file
    """
    ext = filepath.lower().split('.')[-1]
    data = [var.to_dict() for var in variables]

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    if ext == 'json':
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
    elif ext in ('csv', 'xlsx', 'xls'):
        df = pd.DataFrame(data)
        for col in df.columns:
            df[col] = df[col].map(ValidationUtils.sanitize_csv_value)
        if ext == 'csv':
            df.to_csv(filepath, index=False)
        else:
            df.to_excel(filepath, index=False)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def handle_file_operation(operation: str, filepath: str, variables: Optional[list] = None) -> None:
    """Handle file operations with error checking for serverless environment."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        if operation == 'save':
            if variables is None:
                variables_dicts = optimizer_state.get_variables()
                variables = [IntegerVariable.from_dict(d) for d in variables_dicts]
            export_to_file(variables, filepath)
        elif operation == 'load':
            if not os.path.exists(filepath):
                raise IOError(f"File not found: {filepath}")
            data = parse_file(filepath)
            variables = []
            for item in data:
                var = IntegerVariable.from_dict(item)
                var.validate()
                variables.append(var)
            optimizer_state.set_variables([v.to_dict() for v in variables])
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