"""
Finance blueprint: finance dashboard page and JSON API for accounts,
transactions, budgets and reporting.
"""

import os

from flask import Blueprint, render_template, request, session, current_app

from config import Config

finance_bp = Blueprint('finance', __name__)


def _finance_storage_dir() -> str:
    """Return a per-user finance data directory."""
    root = current_app.config.get('FINANCE_DATA_FOLDER',
                                  os.path.join(Config.BASE_DIR, 'data', 'finance'))
    user_id = session.get('user_id') or 'anonymous'
    return os.path.join(root, str(user_id))


@finance_bp.route("/finance", methods=["GET"])
def finance():
    """Finance page."""
    return render_template("finance.html")


@finance_bp.route("/api/finance/data", methods=["GET"])
def get_finance_data():
    """Get all finance data for the frontend."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
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


@finance_bp.route("/api/finance/transaction", methods=["POST"])
def create_transaction():
    """Create a new transaction."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
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


@finance_bp.route("/api/finance/transaction/<transaction_id>", methods=["GET"])
def get_transaction(transaction_id):
    """Get a specific transaction."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        transaction = finance.transaction_manager.get_transaction(transaction_id)
        if transaction:
            return {'success': True, 'transaction': transaction.to_dict()}
        return {'success': False, 'message': 'Transaction not found'}, 404
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@finance_bp.route("/api/finance/transaction/<transaction_id>", methods=["PUT"])
def update_transaction(transaction_id):
    """Update a transaction."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        transaction = finance.transaction_manager.update_transaction(transaction_id, **data)
        return {'success': True, 'transaction': transaction.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/transaction/<transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id):
    """Delete a transaction."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        success = finance.transaction_manager.delete_transaction(transaction_id)
        return {'success': success, 'message': 'Transaction deleted'}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/account", methods=["POST"])
def create_account():
    """Create a new account."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
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


@finance_bp.route("/api/finance/account/<account_id>", methods=["GET"])
def get_account(account_id):
    """Get a specific account."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        account = finance.account_manager.get_account(account_id)
        if account:
            return {'success': True, 'account': account.to_dict()}
        return {'success': False, 'message': 'Account not found'}, 404
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@finance_bp.route("/api/finance/account/<account_id>", methods=["PUT"])
def update_account(account_id):
    """Update an account."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        account = finance.account_manager.update_account(account_id, **data)
        return {'success': True, 'account': account.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/account/<account_id>", methods=["DELETE"])
def delete_account(account_id):
    """Delete an account."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        success = finance.account_manager.delete_account(account_id)
        return {'success': success, 'message': 'Account deleted'}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/budget", methods=["POST"])
def create_budget():
    """Create a new budget."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
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


@finance_bp.route("/api/finance/budget/<budget_id>", methods=["GET"])
def get_budget(budget_id):
    """Get a specific budget."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        budget = finance.budget_manager.get_budget(budget_id)
        if budget:
            return {'success': True, 'budget': budget.to_dict()}
        return {'success': False, 'message': 'Budget not found'}, 404
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@finance_bp.route("/api/finance/budget/<budget_id>", methods=["PUT"])
def update_budget(budget_id):
    """Update a budget."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        budget = finance.budget_manager.update_budget(budget_id, **data)
        return {'success': True, 'budget': budget.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/budget/<budget_id>", methods=["DELETE"])
def delete_budget(budget_id):
    """Delete a budget."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        success = finance.budget_manager.delete_budget(budget_id)
        return {'success': success, 'message': 'Budget deleted'}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/report", methods=["POST"])
def generate_report():
    """Generate a financial report."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        report = finance.generate_report(
            report_type=data.get('type', 'summary'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            account_id=data.get('account_id')
        )
        return {'success': True, 'data': report}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/export", methods=["POST"])
def export_finance_data():
    """Export all financial data."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        format_type = data.get('format', 'json')
        finance = create_finance_core(_finance_storage_dir())
        export_data = finance.export_data(format_type)
        return {'success': True, 'data': export_data['data']}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@finance_bp.route("/api/finance/export/csv", methods=["POST"])
def export_transactions_csv():
    """Export transactions as CSV."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        csv_data = finance.export_transactions_csv(
            start_date=data.get('start_date'),
            end_date=data.get('end_date')
        )
        return {'success': True, 'data': csv_data}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@finance_bp.route("/api/finance/category", methods=["POST"])
def create_category():
    """Create a new category."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        category = finance.category_manager.create_category(
            name=data['name'],
            type_str=data['type'],
            icon=data.get('icon', 'tag'),
            color=data.get('color', '#007a55'),
            parent_id=data.get('parent_id')
        )
        return {'success': True, 'category': category.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/category/<category_id>", methods=["PUT"])
def update_category(category_id):
    """Update a category."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        category = finance.category_manager.update_category(category_id, **data)
        return {'success': True, 'category': category.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/category/<category_id>", methods=["DELETE"])
def delete_category(category_id):
    """Delete a category."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        success = finance.category_manager.delete_category(category_id)
        return {'success': True, 'message': 'Category deleted'}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/alerts", methods=["GET"])
def list_alerts():
    """List all alerts."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        alerts = [a.to_dict() for a in sorted(
            finance.alert_manager.alerts,
            key=lambda a: a.created_at,
            reverse=True
        )]
        return {'success': True, 'alerts': alerts}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@finance_bp.route("/api/finance/alerts/read", methods=["POST"])
def mark_all_alerts_read():
    """Mark all alerts as read."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        count = finance.alert_manager.mark_all_alerts_read()
        return {'success': True, 'updated': count}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/alert/<alert_id>/read", methods=["POST"])
def mark_alert_read(alert_id):
    """Mark a single alert as read."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        alert = finance.alert_manager.mark_alert_read(alert_id)
        return {'success': True, 'alert': alert.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/import", methods=["POST"])
def import_finance_data():
    """Import financial data."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        results = finance.import_data(data)
        return {'success': True, 'data': results}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500