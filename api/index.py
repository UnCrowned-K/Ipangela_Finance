"""
Profit Optimizer API - Vercel Serverless Entry Point

This module provides both API endpoints and HTML page serving for Vercel deployment.
"""

import sys
import os

# Add server/ to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

from flask import Flask, jsonify, request, send_file, render_template
from flask_cors import CORS

app = Flask(__name__, template_folder='../server/templates', static_folder='../server/static')
CORS(app)

# Import core modules
try:
    from optimizer_core import (
        IntegerVariable, create_integer_variable, optimize, 
        variables_list, clear_variables, OptimizationError
    )
    OPTIMIZER_AVAILABLE = True
except ImportError as e:
    OPTIMIZER_AVAILABLE = False
    OPTIMIZER_ERROR = str(e)

try:
    from finance_core import create_finance_core, FinanceCore
    FINANCE_AVAILABLE = True
except ImportError as e:
    FINANCE_AVAILABLE = False
    FINANCE_ERROR = str(e)

try:
    from invoice_core import InvoiceCore
    INVOICE_AVAILABLE = True
except ImportError as e:
    INVOICE_AVAILABLE = False
    INVOICE_ERROR = str(e)


# =============================================================================
# HTML PAGE ROUTES (for Vercel static serving)
# =============================================================================

@app.route("/")
def home():
    """Home page."""
    return render_template("home.html")


@app.route("/optimizer.html")
def optimizer_page():
    """Optimizer page."""
    return render_template("optimizer.html")


@app.route("/finance")
def finance_page():
    """Finance page."""
    return render_template("finance.html")


@app.route("/invoice")
def invoice_page():
    """Invoice page."""
    from datetime import date
    today = date.today().isoformat()
    return render_template("invoice.html", today_date=today)


@app.route("/about")
def about_page():
    """About page."""
    return render_template("about.html")


@app.route("/contact")
def contact_page():
    """Contact page."""
    return render_template("contact.html")


# =============================================================================
# STATIC FILES
# =============================================================================

@app.route("/static/<path:filename>")
def static_files(filename):
    """Serve static files."""
    return send_file(f"../server/static/{filename}")


# =============================================================================
# API HEALTH CHECK
# =============================================================================

@app.route("/api")
def api_info():
    """API information endpoint."""
    return jsonify({
        "status": "ok",
        "message": "Profit Optimizer API",
        "version": "1.0.0",
        "modules": {
            "optimizer": "available" if OPTIMIZER_AVAILABLE else "error",
            "finance": "available" if FINANCE_AVAILABLE else "error",
            "invoice": "available" if INVOICE_AVAILABLE else "error"
        },
        "endpoints": {
            "health": "/api",
            "optimizer": "/api/optimizer/*",
            "finance": "/api/finance/*",
            "invoice": "/api/invoice/*"
        }
    })


# =============================================================================
# OPTIMIZER API
# =============================================================================

@app.route("/api/optimizer/variables", methods=["GET"])
def get_variables():
    """Get all optimization variables."""
    if not OPTIMIZER_AVAILABLE:
        return jsonify({"success": False, "error": OPTIMIZER_ERROR}), 500
    
    return jsonify({
        "success": True,
        "variables": [var.to_dict() for var in variables_list]
    })


@app.route("/api/optimizer/variable", methods=["POST"])
def add_variable():
    """Add a new optimization variable."""
    if not OPTIMIZER_AVAILABLE:
        return jsonify({"success": False, "error": OPTIMIZER_ERROR}), 500
    
    try:
        data = request.get_json()
        create_integer_variable(
            name=data['name'],
            lowerBound=data.get('lowerBound', 0),
            upperBound=data.get('upperBound'),
            cost=float(data['cost']),
            profit=float(data['profit']),
            multiplier=int(data.get('multiplier', 1))
        )
        return jsonify({"success": True, "message": "Variable added successfully"})
    except OptimizationError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route("/api/optimizer/variable/<name>", methods=["DELETE"])
def delete_variable(name):
    """Delete an optimization variable."""
    if not OPTIMIZER_AVAILABLE:
        return jsonify({"success": False, "error": OPTIMIZER_ERROR}), 500
    
    global variables_list
    try:
        variables_list = [var for var in variables_list if var.name != name]
        return jsonify({"success": True, "message": f"Variable '{name}' deleted"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/optimizer/clear", methods=["POST"])
def clear_all_variables():
    """Clear all optimization variables."""
    if not OPTIMIZER_AVAILABLE:
        return jsonify({"success": False, "error": OPTIMIZER_ERROR}), 500
    
    clear_variables()
    return jsonify({"success": True, "message": "All variables cleared"})


@app.route("/api/optimizer/run", methods=["POST"])
def run_optimization():
    """Run optimization with current variables and budget."""
    if not OPTIMIZER_AVAILABLE:
        return jsonify({"success": False, "error": OPTIMIZER_ERROR}), 500
    
    try:
        data = request.get_json()
        budget = float(data.get('budget', 0))
        
        if not variables_list:
            return jsonify({"success": False, "message": "No variables to optimize"}), 400
        
        max_profit, result = optimize(variables_list, budget)
        
        return jsonify({
            "success": True,
            "max_profit": max_profit,
            "result": result,
            "variables": [var.to_dict() for var in variables_list]
        })
    except OptimizationError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================================================
# FINANCE API
# =============================================================================

@app.route("/api/finance/data", methods=["GET"])
def get_finance_data():
    """Get all finance data for the frontend."""
    if not FINANCE_AVAILABLE:
        return jsonify({"success": False, "error": FINANCE_ERROR}), 500
    
    try:
        finance = create_finance_core()
        data = finance.get_dashboard_data()
        return jsonify({
            'success': True,
            'data': {
                'accounts': [a.to_dict() for a in finance.account_manager.accounts],
                'categories': [c.to_dict() for c in finance.category_manager.categories],
                'transactions': [t.to_dict() for t in finance.transaction_manager.transactions],
                'budgets': [b.to_dict() for b in finance.budget_manager.budgets],
                'dashboard': data
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/api/finance/transaction", methods=["POST"])
def create_transaction():
    """Create a new transaction."""
    if not FINANCE_AVAILABLE:
        return jsonify({"success": False, "error": FINANCE_ERROR}), 500
    
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
        return jsonify({'success': True, 'transaction': transaction.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route("/api/finance/transaction/<transaction_id>", methods=["GET"])
def get_transaction(transaction_id):
    """Get a specific transaction."""
    if not FINANCE_AVAILABLE:
        return jsonify({"success": False, "error": FINANCE_ERROR}), 500
    
    try:
        finance = create_finance_core()
        transaction = finance.transaction_manager.get_transaction(transaction_id)
        if transaction:
            return jsonify({'success': True, 'transaction': transaction.to_dict()})
        return jsonify({'success': False, 'message': 'Transaction not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/api/finance/transaction/<transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id):
    """Delete a transaction."""
    if not FINANCE_AVAILABLE:
        return jsonify({"success": False, "error": FINANCE_ERROR}), 500
    
    try:
        finance = create_finance_core()
        success = finance.transaction_manager.delete_transaction(transaction_id)
        return jsonify({'success': success, 'message': 'Transaction deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route("/api/finance/account", methods=["POST"])
def create_account():
    """Create a new account."""
    if not FINANCE_AVAILABLE:
        return jsonify({"success": False, "error": FINANCE_ERROR}), 500
    
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
        return jsonify({'success': True, 'account': account.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route("/api/finance/account/<account_id>", methods=["GET"])
def get_account(account_id):
    """Get a specific account."""
    if not FINANCE_AVAILABLE:
        return jsonify({"success": False, "error": FINANCE_ERROR}), 500
    
    try:
        finance = create_finance_core()
        account = finance.account_manager.get_account(account_id)
        if account:
            return jsonify({'success': True, 'account': account.to_dict()})
        return jsonify({'success': False, 'message': 'Account not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/api/finance/account/<account_id>", methods=["DELETE"])
def delete_account(account_id):
    """Delete an account."""
    if not FINANCE_AVAILABLE:
        return jsonify({"success": False, "error": FINANCE_ERROR}), 500
    
    try:
        finance = create_finance_core()
        success = finance.account_manager.delete_account(account_id)
        return jsonify({'success': success, 'message': 'Account deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route("/api/finance/budget", methods=["POST"])
def create_budget():
    """Create a new budget."""
    if not FINANCE_AVAILABLE:
        return jsonify({"success": False, "error": FINANCE_ERROR}), 500
    
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
        return jsonify({'success': True, 'budget': budget.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route("/api/finance/budget/<budget_id>", methods=["GET"])
def get_budget(budget_id):
    """Get a specific budget."""
    if not FINANCE_AVAILABLE:
        return jsonify({"success": False, "error": FINANCE_ERROR}), 500
    
    try:
        finance = create_finance_core()
        budget = finance.budget_manager.get_budget(budget_id)
        if budget:
            return jsonify({'success': True, 'budget': budget.to_dict()})
        return jsonify({'success': False, 'message': 'Budget not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/api/finance/budget/<budget_id>", methods=["DELETE"])
def delete_budget(budget_id):
    """Delete a budget."""
    if not FINANCE_AVAILABLE:
        return jsonify({"success": False, "error": FINANCE_ERROR}), 500
    
    try:
        finance = create_finance_core()
        success = finance.budget_manager.delete_budget(budget_id)
        return jsonify({'success': success, 'message': 'Budget deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route("/api/finance/report", methods=["POST"])
def generate_report():
    """Generate a financial report."""
    if not FINANCE_AVAILABLE:
        return jsonify({"success": False, "error": FINANCE_ERROR}), 500
    
    try:
        data = request.get_json()
        finance = create_finance_core()
        report = finance.generate_report(
            report_type=data.get('type', 'summary'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            account_id=data.get('account_id')
        )
        return jsonify({'success': True, 'data': report})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


# =============================================================================
# INVOICE API
# =============================================================================

@app.route("/api/invoice/list", methods=["GET"])
def list_invoices():
    """List all invoices."""
    if not INVOICE_AVAILABLE:
        return jsonify({"success": False, "error": INVOICE_ERROR}), 500
    
    try:
        invoice_core = InvoiceCore()
        invoices = invoice_core.list_invoices()
        return jsonify({'success': True, 'invoices': invoices})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/api/invoice", methods=["POST"])
def create_invoice():
    """Create a new invoice."""
    if not INVOICE_AVAILABLE:
        return jsonify({"success": False, "error": INVOICE_ERROR}), 500
    
    try:
        data = request.get_json()
        invoice_core = InvoiceCore()
        
        invoice, message = invoice_core.create_invoice(
            client_data=data.get('client', {}),
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
            return jsonify({'success': True, 'message': message, 'invoice_id': invoice.invoice_id, 'invoice_number': invoice.invoice_number})
        else:
            return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/api/invoice/<invoice_id>", methods=["GET"])
def get_invoice(invoice_id):
    """Get invoice by ID."""
    if not INVOICE_AVAILABLE:
        return jsonify({"success": False, "error": INVOICE_ERROR}), 500
    
    try:
        invoice_core = InvoiceCore()
        invoice, message = invoice_core.get_invoice(invoice_id)
        
        if invoice:
            return jsonify({'success': True, 'invoice': invoice.to_dict()})
        else:
            return jsonify({'success': False, 'message': message}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/api/invoice/<invoice_id>", methods=["DELETE"])
def delete_invoice(invoice_id):
    """Delete an invoice."""
    if not INVOICE_AVAILABLE:
        return jsonify({"success": False, "error": INVOICE_ERROR}), 500
    
    try:
        invoice_core = InvoiceCore()
        success, message = invoice_core.delete_invoice(invoice_id)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# DO NOT use app.run() - Vercel handles the entry point
