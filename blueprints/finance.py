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

# =============================================================================
# CONTACTS, RECEIVABLES AND PAYABLES
# =============================================================================

@finance_bp.route("/api/finance/contacts", methods=["GET"])
def list_contacts():
    """List or search customers and suppliers."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        contacts = finance.contact_manager.search_contacts(
            query=request.args.get('q', ''),
            role=request.args.get('role'),
        )
        return {
            'success': True,
            'contacts': [c.to_dict() for c in contacts],
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/contact", methods=["POST"])
def create_contact():
    """Create a customer or supplier."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        contact = finance.contact_manager.create_contact(
            name=data['name'],
            role=data.get('role', 'customer'),
            contact_person=data.get('contact_person', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            tax_number=data.get('tax_number', ''),
            notes=data.get('notes', ''),
        )
        return {'success': True, 'contact': contact.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/contact/<contact_id>", methods=["PUT"])
def update_contact(contact_id):
    """Update a contact."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        contact = finance.contact_manager.update_contact(contact_id, **data)
        return {'success': True, 'contact': contact.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/contact/<contact_id>", methods=["DELETE"])
def delete_contact(contact_id):
    """Delete a contact that has no ledger history."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        finance.contact_manager.delete_contact(contact_id)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/ledger", methods=["GET"])
def get_ledger():
    """Everything owed in and out, with aging on both sides."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        return {
            'success': True,
            'data': finance.get_ledger_overview(request.args.get('as_of')),
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/receivable", methods=["POST"])
def create_receivable():
    """Bill a customer for something not yet paid."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        entry = finance.receivable_manager.create_receivable(
            contact_id=data['contact_id'],
            amount=data['amount'],
            issue_date=data.get('issue_date'),
            due_date=data.get('due_date'),
            account_id=data.get('account_id', ''),
            description=data.get('description', ''),
            reference=data.get('reference', ''),
            terms_days=int(data.get('terms_days', 30)),
        )
        return {'success': True, 'receivable': entry.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/receivable/<entry_id>", methods=["PUT"])
def update_receivable(entry_id):
    """Edit a customer invoice."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        entry = finance.receivable_manager.update_receivable(entry_id, **data)
        return {'success': True, 'receivable': entry.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/receivable/<entry_id>/payment", methods=["POST"])
def record_receivable_payment(entry_id):
    """Record cash received against a customer invoice."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        result = finance.receivable_manager.record_payment(
            entry_id,
            amount=data['amount'],
            date_str=data.get('date'),
            account_id=data.get('account_id'),
            category_id=data.get('category_id'),
            reference=data.get('reference', ''),
            create_transaction=data.get('create_transaction', True),
        )
        return {'success': True, 'data': result}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/receivable/<entry_id>/write-off", methods=["POST"])
def write_off_receivable(entry_id):
    """Write a customer invoice off as uncollectable."""
    from finance_core import create_finance_core
    try:
        data = request.get_json() or {}
        finance = create_finance_core(_finance_storage_dir())
        result = finance.receivable_manager.write_off(
            entry_id, reason=data.get('reason', ''))
        return {'success': True, 'data': result}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/receivable/<entry_id>", methods=["DELETE"])
def delete_receivable(entry_id):
    """Delete an unpaid customer invoice."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        finance.receivable_manager.delete_receivable(entry_id)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/payable", methods=["POST"])
def create_payable():
    """Record a supplier bill that has not been paid yet."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        entry = finance.payable_manager.create_payable(
            contact_id=data['contact_id'],
            amount=data['amount'],
            issue_date=data.get('issue_date'),
            due_date=data.get('due_date'),
            account_id=data.get('account_id', ''),
            description=data.get('description', ''),
            reference=data.get('reference', ''),
            category_id=data.get('category_id', ''),
            terms_days=int(data.get('terms_days', 30)),
        )
        return {'success': True, 'payable': entry.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/payable/<entry_id>", methods=["PUT"])
def update_payable(entry_id):
    """Edit a supplier bill."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        entry = finance.payable_manager.update_payable(entry_id, **data)
        return {'success': True, 'payable': entry.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/payable/<entry_id>/payment", methods=["POST"])
def record_payable_payment(entry_id):
    """Record cash paid against a supplier bill."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        result = finance.payable_manager.record_payment(
            entry_id,
            amount=data['amount'],
            date_str=data.get('date'),
            account_id=data.get('account_id'),
            category_id=data.get('category_id'),
            reference=data.get('reference', ''),
            create_transaction=data.get('create_transaction', True),
        )
        return {'success': True, 'data': result}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/payable/<entry_id>", methods=["DELETE"])
def delete_payable(entry_id):
    """Delete an unpaid supplier bill."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        finance.payable_manager.delete_payable(entry_id)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


# =============================================================================
# COMPLIANCE
# =============================================================================

@finance_bp.route("/api/finance/compliance", methods=["GET"])
def get_compliance():
    """Tax, payroll and structuring status in one payload."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        return {
            'success': True,
            'data': finance.get_compliance_overview(request.args.get('as_of')),
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/entity-profile", methods=["POST"])
def update_entity_profile():
    """Create or update the business profile."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        profile = finance.entity_manager.update_profile(**data)
        return {'success': True, 'profile': profile.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/tax-schedule", methods=["GET"])
def get_tax_schedule():
    """Planned VAT and provisional tax periods for the current year."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        schedule = finance.tax_manager.period_schedule(
            year_end_month=request.args.get('year_end_month', type=int),
            vat_interval=request.args.get('vat_interval'),
            periods_per_year=request.args.get('periods_per_year', type=int) or 2,
        )
        return {'success': True, 'data': schedule}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/tax-schedule/seed", methods=["POST"])
def seed_tax_schedule():
    """Turn a planned schedule into tracked obligations.

    Safe to call twice: periods already tracked are skipped rather than
    duplicated.
    """
    from finance_core import create_finance_core
    try:
        data = request.get_json() or {}
        finance = create_finance_core(_finance_storage_dir())
        schedule = data.get('schedule') or finance.tax_manager.period_schedule(
            year_end_month=data.get('year_end_month'),
            vat_interval=data.get('vat_interval'),
            periods_per_year=data.get('periods_per_year', 2),
        )
        result = finance.tax_manager.seed_schedule(schedule)
        return {'success': True, 'data': result}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/tax", methods=["POST"])
def create_tax_record():
    """Record a tax obligation or estimate."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        record = finance.tax_manager.create_record(
            tax_type=data['tax_type'],
            period_start=data['period_start'],
            period_end=data['period_end'],
            due_date=data['due_date'],
            taxable_amount=float(data.get('taxable_amount', 0)),
            tax_amount=float(data.get('tax_amount', 0)),
            status=data.get('status', 'estimated'),
            reference=data.get('reference', ''),
            provider=data.get('provider', ''),
            notes=data.get('notes', ''),
        )
        return {'success': True, 'tax': record.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/tax/<record_id>/status", methods=["POST"])
def update_tax_status(record_id):
    """Mark a tax obligation as paid, or change its state."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        record = finance.tax_manager.mark_status(
            record_id, data['status'], paid_date=data.get('paid_date'))
        return {'success': True, 'tax': record.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/vat-estimate", methods=["GET"])
def estimate_vat():
    """Rough net VAT payable for a period, from recorded transactions."""
    from finance_core import create_finance_core
    from finance_core import periods as _periods
    try:
        finance = create_finance_core(_finance_storage_dir())
        end = request.args.get('end') or _periods.today().isoformat()
        start = request.args.get('start') or _periods.month_start(end).isoformat()
        result = finance.tax_manager.estimate_vat(start, end)
        return {'success': True, 'data': result}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/payroll", methods=["POST"])
def create_payroll_run():
    """Record a payroll run."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        run = finance.payroll_manager.create_run(
            period_start=data['period_start'],
            period_end=data['period_end'],
            pay_date=data['pay_date'],
            gross_pay=float(data['gross_pay']),
            paye=float(data.get('paye', 0)),
            uif=float(data.get('uif', 0)),
            other_deductions=float(data.get('other_deductions', 0)),
            sdl=float(data.get('sdl', 0)),
            employer_uif=float(data.get('employer_uif', 0)),
            employer_pension=float(data.get('employer_pension', 0)),
            employee_count=int(data.get('employee_count', 0)),
            status=data.get('status', 'draft'),
            notes=data.get('notes', ''),
        )
        return {'success': True, 'payroll': run.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/payroll/<run_id>", methods=["PUT"])
def update_payroll_run(run_id):
    """Update a payroll run, including marking it submitted or paid."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        run = finance.payroll_manager.update_run(run_id, **data)
        return {'success': True, 'payroll': run.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/payroll/<run_id>", methods=["DELETE"])
def delete_payroll_run(run_id):
    """Delete a payroll run."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        finance.payroll_manager.delete_run(run_id)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


# =============================================================================
# FORECASTING
# =============================================================================

@finance_bp.route("/api/finance/forecast", methods=["GET"])
def list_forecasts():
    """List saved projection scenarios."""
    from finance_core import create_finance_core
    try:
        finance = create_finance_core(_finance_storage_dir())
        return {
            'success': True,
            'scenarios': [s.to_dict() for s in finance.forecast_manager.scenarios],
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/forecast", methods=["POST"])
def create_forecast():
    """Save a projection scenario."""
    from finance_core import create_finance_core
    try:
        data = request.get_json()
        finance = create_finance_core(_finance_storage_dir())
        scenario = finance.forecast_manager.create_scenario(
            name=data['name'],
            projection_months=int(data.get('projection_months', 12)),
            baseline_months=int(data.get('baseline_months', 3)),
            income_growth_pct=float(data.get('income_growth_pct', 0)),
            expense_growth_pct=float(data.get('expense_growth_pct', 0)),
            one_off_income=float(data.get('one_off_income', 0)),
            one_off_expenses=float(data.get('one_off_expenses', 0)),
            notes=data.get('notes', ''),
        )
        return {'success': True, 'scenario': scenario.to_dict()}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/forecast/<scenario_id>/project", methods=["POST"])
def project_forecast(scenario_id):
    """Run a scenario projection.

    Any growth or month count in the body overrides the saved scenario for
    this run only, so a figure can be tried without saving it.
    """
    from finance_core import create_finance_core
    from finance_core import periods as _periods
    try:
        data = request.get_json() or {}
        finance = create_finance_core(_finance_storage_dir())
        result = finance.forecast_manager.project(
            scenario_id,
            reference=_periods.parse_date(data.get('as_of')),
            overrides={
                'projection_months': data.get('projection_months'),
                'baseline_months': data.get('baseline_months'),
                'income_growth_pct': data.get('income_growth_pct'),
                'expense_growth_pct': data.get('expense_growth_pct'),
                'one_off_income': data.get('one_off_income'),
                'one_off_expenses': data.get('one_off_expenses'),
            },
        )
        return {'success': True, 'data': result}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


# =============================================================================
# STATEMENTS AND POSITION
# =============================================================================

@finance_bp.route("/api/finance/money-position", methods=["GET"])
def get_money_position():
    """The five questions: in, out, owe, owed, and what you actually made."""
    from finance_core import create_finance_core
    from finance_core import periods as _periods
    try:
        finance = create_finance_core(_finance_storage_dir())
        end = request.args.get('end') or _periods.today().isoformat()
        start = request.args.get('start') or _periods.month_start(end).isoformat()
        result = finance.get_money_position(start, end, end)
        return {'success': True, 'data': result}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400


@finance_bp.route("/api/finance/statement", methods=["GET"])
def get_statement():
    """Build one of the financial statements.

    ``type`` is one of profit_loss, balance_sheet, cash_flow,
    expense_analysis, records_health or funding_readiness.
    """
    from finance_core import create_finance_core
    from finance_core import periods as _periods
    try:
        report_type = request.args.get('type', 'profit_loss')
        end = request.args.get('end') or _periods.today().isoformat()
        start = request.args.get('start') or _periods.month_start(end).isoformat()
        finance = create_finance_core(_finance_storage_dir())
        result = finance.get_financial_statements(
            report_type,
            start,
            end,
            account_id=request.args.get('account_id'),
            months=request.args.get('months', type=int) or 12,
        )
        return {'success': True, 'data': result}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 400
