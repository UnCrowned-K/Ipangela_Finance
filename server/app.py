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
- Clean separation of concerns (web UI, optimization logic, configuration)

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


# ============================================================================
# MAIN ROUTES
# ============================================================================

@app.route("/", methods=["GET"])
def home():
    """Home page."""
    return render_template("home.html")


@app.route("/finance", methods=["GET"])
def finance():
    """Finance page."""
    return render_template("finance.html")


@app.route("/about", methods=["GET"])
def about():
    """About page."""
    return render_template("about.html")


@app.route("/contact", methods=["GET"])
def contact():
    """Contact page."""
    return render_template("contact.html")


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

    return render_template("optimizer.html", variables=variables_list, max_profit=max_profit, result=result, budget=budget)


# ============================================================================
# INVOICE MANAGEMENT ROUTES
# ============================================================================

@app.route("/invoice", methods=["GET", "POST"])
def invoice():
    """Invoice maker main page."""
    from datetime import date
    today = date.today().isoformat()
    return render_template("invoice.html", today_date=today)


@app.route("/save_invoice", methods=["POST"])
def save_invoice():
    """Save or update an invoice."""
    from invoice_core import InvoiceCore
    import json
    
    try:
        data = json.loads(request.form.get('invoice_data', '{}'))
        
        # Initialize invoice core
        invoice_core = InvoiceCore()
        
        # Prepare client data
        client_data = {
            "name": data.get('client', {}).get('name', ''),
            "email": data.get('client', {}).get('email', ''),
            "phone": data.get('client', {}).get('phone', ''),
            "address": data.get('client', {}).get('address', ''),
            "company": data.get('client', {}).get('company', ''),
            "tax_id": data.get('client', {}).get('tax_id', '')
        }
        
        # Check if updating existing invoice
        if data.get('invoice_id'):
            invoice, message = invoice_core.update_invoice(
                invoice_id=data['invoice_id'],
                client_data=client_data,
                line_items_data=data.get('line_items', []),
                currency=data.get('currency', 'ZAR'),
                due_date=data.get('due_date', ''),
                notes=data.get('notes', ''),
                terms=data.get('terms', ''),
                business_name=data.get('business', {}).get('name', ''),
                business_email=data.get('business', {}).get('email', ''),
                business_phone=data.get('business', {}).get('phone', ''),
                business_address=data.get('business', {}).get('address', ''),
                payment_instructions=data.get('payment_instructions', ''),
                status=data.get('status', 'draft')
            )
        else:
            invoice, message = invoice_core.create_invoice(
                client_data=client_data,
                line_items_data=data.get('line_items', []),
                currency=data.get('currency', 'ZAR'),
                due_date=data.get('due_date', ''),
                notes=data.get('notes', ''),
                terms=data.get('terms', ''),
                business_name=data.get('business', {}).get('name', ''),
                business_email=data.get('business', {}).get('email', ''),
                business_phone=data.get('business', {}).get('phone', ''),
                business_address=data.get('business', {}).get('address', ''),
                payment_instructions=data.get('payment_instructions', '')
            )
        
        if invoice:
            return {'success': True, 'message': message, 'invoice_id': invoice.invoice_id, 'invoice_number': invoice.invoice_number}
        else:
            return {'success': False, 'message': message}, 400
            
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/get_invoice", methods=["GET"])
def get_invoice():
    """Get invoice by ID."""
    from invoice_core import InvoiceCore
    
    try:
        invoice_id = request.args.get('id')
        if not invoice_id:
            return {'success': False, 'message': 'Invoice ID required'}, 400
        
        invoice_core = InvoiceCore()
        invoice, message = invoice_core.get_invoice(invoice_id)
        
        if invoice:
            return {'success': True, 'invoice': invoice.to_dict()}
        else:
            return {'success': False, 'message': message}, 404
            
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/list_invoices", methods=["GET"])
def list_invoices():
    """List all invoices."""
    from invoice_core import InvoiceCore
    
    try:
        invoice_core = InvoiceCore()
        invoices = invoice_core.list_invoices()
        return {'success': True, 'invoices': invoices}
        
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/delete_invoice", methods=["POST"])
def delete_invoice():
    """Delete an invoice."""
    from invoice_core import InvoiceCore
    
    try:
        invoice_id = request.form.get('invoice_id')
        if not invoice_id:
            return {'success': False, 'message': 'Invoice ID required'}, 400
        
        invoice_core = InvoiceCore()
        success, message = invoice_core.delete_invoice(invoice_id)
        
        if success:
            return {'success': True, 'message': message}
        else:
            return {'success': False, 'message': message}, 400
            
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/send_invoice_email", methods=["POST"])
def send_invoice_email():
    """Send invoice via email."""
    from invoice_core import InvoiceEmailSender
    import json
    
    try:
        data = json.loads(request.form.get('invoice_data', '{}'))
        to_email = request.form.get('to_email', '')
        subject = request.form.get('subject', '')
        email_body = request.form.get('email_body', '')
        
        if not to_email:
            return {'success': False, 'message': 'Recipient email required'}, 400
        
        # Create a minimal invoice object for email sending
        class MinimalInvoice:
            def __init__(self, data):
                self.invoice_id = data.get('invoice_id', '')
                self.invoice_number = data.get('invoice_number', '')
                self.client = type('Client', (), {
                    'name': data.get('client', {}).get('name', ''),
                    'email': data.get('client', {}).get('email', '')
                })()
                self.currency = data.get('currency', 'ZAR')
                self.currency_info = {'symbol': 'R'}
                self.business_name = data.get('business', {}).get('name', '')
                self.issue_date = data.get('issue_date', '')
                self.due_date = data.get('due_date', '')
                self.grand_total = data.get('totals', {}).get('grand_total', 0)
                self.payment_instructions = data.get('payment_instructions', '')
        
        invoice = MinimalInvoice(data)
        
        # Initialize email sender
        email_sender = InvoiceEmailSender(
            from_email=data.get('business', {}).get('email', 'noreply@example.com'),
            from_name=data.get('business', {}).get('name', 'Invoice System')
        )
        
        # Send email
        success, message = email_sender.send_invoice_email(
            invoice=invoice,
            to_email=to_email,
            subject=subject,
            body=email_body,
            pdf_path=None
        )
        
        if success:
            return {'success': True, 'message': message}
        else:
            return {'success': False, 'message': message}, 400
            
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/generate_invoice_pdf/<invoice_id>", methods=["GET"])
def generate_invoice_pdf(invoice_id):
    """Generate PDF for an invoice."""
    from invoice_core import InvoiceCore, InvoicePDFGenerator
    import os
    
    try:
        invoice_core = InvoiceCore()
        invoice, message = invoice_core.get_invoice(invoice_id)
        
        if not invoice:
            return {'success': False, 'message': message}, 404
        
        # Generate PDF
        pdf_generator = InvoicePDFGenerator()
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'invoice_{invoice_id}.pdf')
        
        success, message = pdf_generator.generate_pdf(invoice, output_path)
        
        if success:
            return send_file(output_path, as_attachment=True, download_name=f'Invoice-{invoice.invoice_number}.pdf')
        else:
            return {'success': False, 'message': message}, 500
            
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/preview_invoice/<invoice_id>", methods=["GET"])
def preview_invoice(invoice_id):
    """Preview invoice as HTML."""
    from invoice_core import InvoiceCore, InvoicePDFGenerator
    
    try:
        invoice_core = InvoiceCore()
        invoice, message = invoice_core.get_invoice(invoice_id)
        
        if not invoice:
            return {'success': False, 'message': message}, 404
        
        pdf_generator = InvoicePDFGenerator()
        html = pdf_generator.generate_html_preview(invoice)
        
        return {'success': True, 'html': html}
        
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/mark_invoice_paid/<invoice_id>", methods=["POST"])
def mark_invoice_paid(invoice_id):
    """Mark invoice as paid."""
    from invoice_core import InvoiceCore
    
    try:
        invoice_core = InvoiceCore()
        invoice, message = invoice_core.mark_as_paid(invoice_id)
        
        if invoice:
            return {'success': True, 'message': message}
        else:
            return {'success': False, 'message': message}, 400
            
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/mark_invoice_sent/<invoice_id>", methods=["POST"])
def mark_invoice_sent(invoice_id):
    """Mark invoice as sent."""
    from invoice_core import InvoiceCore
    
    try:
        invoice_core = InvoiceCore()
        invoice, message = invoice_core.mark_as_sent(invoice_id)
        
        if invoice:
            return {'success': True, 'message': message}
        else:
            return {'success': False, 'message': message}, 400
            
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


# ============================================================================
# VARIABLE MANAGEMENT ROUTES
# ============================================================================

@app.route("/export", methods=["POST"])
def export_variables():
    """Export variables to a JSON file in the exports folder."""
    try:
        filename = safe_filename(request.form.get("filename", "variables.json"))
        filepath = os.path.join(app.config['EXPORT_FOLDER'], filename)
        handle_file_operation('save', filepath)
        flash(f"Table exported successfully!", "success")
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

        old_var = next((var for var in variables_list if var.name == old_name), None)
        if not old_var:
            return {'status': 'error', 'message': f'Variable {old_name} not found'}, 404

        data, valid = parse_variable_form()
        if not valid:
            return {'status': 'error', 'message': 'Invalid input data'}, 400

        if data['name'] == old_name or not any(var.name == data['name'] for var in variables_list if var.name != old_name):
            new_var = IntegerVariable(**data)
            new_var.validate()
            
            variables_list = [var for var in variables_list if var.name != old_name]
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


# ============================================================================
# APPLICATION RUNNER
# ============================================================================

def run_app(port: int = 5000, debug: bool = True):
    """Run the Flask application with browser auto-open."""
    url = f"http://localhost:{port}"
    def open_browser():
        time.sleep(1)
        webbrowser.open(url)
    
    if not debug:
        threading.Thread(target=open_browser).start()
    
    app.run(debug=debug, use_reloader=False, port=port)


# ============================================================================
# FINANCE MANAGEMENT ROUTES
# ============================================================================

@app.route("/api/finance/data", methods=["GET"])
def get_finance_data():
    """Get all finance data for the frontend."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core()
        data = finance.get_dashboard_data()
        return {
            'success': True,
            'data': {
                'accounts': [a.to_dict() for a in finance.account_manager.accounts],
                'categories': [c.to_dict() for c in finance.category_manager.categories],
                'transactions': [t.to_dict() for t in finance.transaction_manager.transactions],
                'budgets': [b.to_dict() for b in finance.budget_manager.budgets],
                'dashboard': data
            }
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/api/finance/transaction", methods=["POST"])
def create_transaction():
    """Create a new transaction."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core()
        transaction = finance.transaction_manager.create_transaction(
            account_id=data['account_id'],
            type_str=data['type'],
            amount=data['amount'],
            category_id=data.get('category_id'),
            description=data.get('description', ''),
            date_str=data.get('date'),
            payee=data.get('payee', ''),
            notes=data.get('notes', '')
        )
        return {'success': True, 'transaction': transaction.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@app.route("/api/finance/transaction/<transaction_id>", methods=["GET"])
def get_transaction(transaction_id):
    """Get a specific transaction."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core()
        transaction = finance.transaction_manager.get_transaction(transaction_id)
        if transaction:
            return {'success': True, 'transaction': transaction.to_dict()}
        return {'success': False, 'message': 'Transaction not found'}, 404
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/api/finance/transaction/<transaction_id>", methods=["PUT"])
def update_transaction(transaction_id):
    """Update a transaction."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core()
        transaction = finance.transaction_manager.update_transaction(transaction_id, **data)
        return {'success': True, 'transaction': transaction.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@app.route("/api/finance/transaction/<transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id):
    """Delete a transaction."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core()
        success = finance.transaction_manager.delete_transaction(transaction_id)
        return {'success': success, 'message': 'Transaction deleted'}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@app.route("/api/finance/account", methods=["POST"])
def create_account():
    """Create a new account."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core()
        account = finance.account_manager.create_account(
            name=data['name'],
            type_str=data['type'],
            balance=data.get('balance', 0),
            currency=data.get('currency', 'ZAR'),
            institution=data.get('institution', ''),
            account_number=data.get('account_number', ''),
            notes=data.get('notes', '')
        )
        return {'success': True, 'account': account.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@app.route("/api/finance/account/<account_id>", methods=["GET"])
def get_account(account_id):
    """Get a specific account."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core()
        account = finance.account_manager.get_account(account_id)
        if account:
            return {'success': True, 'account': account.to_dict()}
        return {'success': False, 'message': 'Account not found'}, 404
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/api/finance/account/<account_id>", methods=["PUT"])
def update_account(account_id):
    """Update an account."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core()
        account = finance.account_manager.update_account(account_id, **data)
        return {'success': True, 'account': account.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@app.route("/api/finance/account/<account_id>", methods=["DELETE"])
def delete_account(account_id):
    """Delete an account."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core()
        success = finance.account_manager.delete_account(account_id)
        return {'success': success, 'message': 'Account deleted'}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@app.route("/api/finance/budget", methods=["POST"])
def create_budget():
    """Create a new budget."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core()
        budget = finance.budget_manager.create_budget(
            name=data['name'],
            category_id=data['category_id'],
            amount=data['amount'],
            period=data.get('period', 'monthly'),
            alert_threshold=data.get('alert_threshold', 80)
        )
        return {'success': True, 'budget': budget.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@app.route("/api/finance/budget/<budget_id>", methods=["GET"])
def get_budget(budget_id):
    """Get a specific budget."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core()
        budget = finance.budget_manager.get_budget(budget_id)
        if budget:
            return {'success': True, 'budget': budget.to_dict()}
        return {'success': False, 'message': 'Budget not found'}, 404
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/api/finance/budget/<budget_id>", methods=["PUT"])
def update_budget(budget_id):
    """Update a budget."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core()
        budget = finance.budget_manager.update_budget(budget_id, **data)
        return {'success': True, 'budget': budget.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@app.route("/api/finance/budget/<budget_id>", methods=["DELETE"])
def delete_budget(budget_id):
    """Delete a budget."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core()
        success = finance.budget_manager.delete_budget(budget_id)
        return {'success': success, 'message': 'Budget deleted'}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@app.route("/api/finance/report", methods=["POST"])
def generate_report():
    """Generate a financial report."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core()
        report = finance.generate_report(
            report_type=data.get('type', 'summary'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            account_id=data.get('account_id')
        )
        return {'success': True, 'data': report}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@app.route("/api/finance/export", methods=["POST"])
def export_finance_data():
    """Export all financial data."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        format_type = data.get('format', 'json')
        finance = create_finance_core()
        export_data = finance.export_data(format_type)
        return {'success': True, 'data': export_data['data']}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/api/finance/export/csv", methods=["POST"])
def export_transactions_csv():
    """Export transactions as CSV."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core()
        csv_data = finance.export_transactions_csv(
            start_date=data.get('start_date'),
            end_date=data.get('end_date')
        )
        return {'success': True, 'data': csv_data}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route("/api/finance/import", methods=["POST"])
def import_finance_data():
    """Import financial data."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core()
        results = finance.import_data(data)
        return {'success': True, 'data': results}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


# ============================================================================
# VERCEL SERVERLESS
# ============================================================================

# from werkzeug.wrappers import Response

# class VercelResponse(Response):
#     """Response class for Vercel serverless compatibility."""
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.headers['Access-Control-Allow-Origin'] = '*'
#         self.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH'
#         self.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'


# @app.route('/api/vercel-test')
# def vercel_test():
#     """Test endpoint to verify Vercel serverless is working."""
#     return {'status': 'ok', 'message': 'Vercel serverless is working!'}


# def handler(request):
#     """
#     Vercel serverless handler function.
#     This is the entry point for Vercel's Python runtime.
#     """
#     return app.full_dispatch_request()


# if __name__ == "__main__":
#     run_app()
