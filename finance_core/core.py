import os
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List

from finance_core.models import TransactionType
from finance_core.storage import DataStorage
from finance_core.managers import (
    CategoryManager, AccountManager, TransactionManager,
    BudgetManager, AlertManager, UserManager
)
from finance_core.ledger import ContactManager, ReceivableManager, PayableManager
from finance_core.compliance import TaxManager, PayrollManager, EntityManager, ForecastManager
from finance_core.statements import StatementBuilder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FinanceCore:
    """
    Main finance management system class.
    
    Provides a unified interface for all finance operations including
    accounts, transactions, budgets, categories, alerts, and user management.
    """
    
    def __init__(self, storage_dir: str = None):
        """Initialize the finance core system."""
        self.storage = DataStorage(storage_dir)
        
        # Initialize managers
        self.category_manager = CategoryManager(self.storage)
        self.account_manager = AccountManager(self.storage)
        self.transaction_manager = TransactionManager(
            self.storage, self.category_manager, self.account_manager
        )
        self.budget_manager = BudgetManager(self.storage, self.transaction_manager)
        self.alert_manager = AlertManager(self.storage, self.budget_manager)
        self.user_manager = UserManager(self.storage)

        # Customers, suppliers and the money they are owed
        self.contact_manager = ContactManager(self.storage)
        self.receivable_manager = ReceivableManager(
            self.storage, self.contact_manager, self.transaction_manager
        )
        self.payable_manager = PayableManager(
            self.storage, self.contact_manager, self.transaction_manager
        )

        # Tax, payroll, entity structuring and projections
        self.entity_manager = EntityManager(self.storage)
        self.tax_manager = TaxManager(
            self.storage, self.transaction_manager, self.entity_manager
        )
        self.payroll_manager = PayrollManager(self.storage)
        self.forecast_manager = ForecastManager(
            self.storage, self.transaction_manager, self.account_manager
        )

        # Financial statements and lender-facing metrics
        self.statement_builder = StatementBuilder(
            transaction_manager=self.transaction_manager,
            account_manager=self.account_manager,
            receivable_manager=self.receivable_manager,
            payable_manager=self.payable_manager,
            category_manager=self.category_manager,
            tax_manager=self.tax_manager,
            payroll_manager=self.payroll_manager,
            entity_manager=self.entity_manager,
        )

        logger.info("Finance Core initialized successfully")
    
    # =========================================================================
    # DASHBOARD METHODS
    # =========================================================================
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        account_balances = self.account_manager.get_total_balance()
        transaction_summary = self.transaction_manager.get_summary()
        budget_statuses = self.budget_manager.get_all_budgets_status()
        recent_transactions = sorted(
            self.transaction_manager.transactions,
            key=lambda t: datetime.fromisoformat(t.date),
            reverse=True
        )[:10]
        unread_alerts = self.alert_manager.get_unread_alerts()
        
        # Calculate monthly trends
        monthly_data = self._calculate_monthly_trends()
        
        # Category breakdown
        category_breakdown = self._get_category_breakdown()
        
        return {
            'account_balances': account_balances,
            'transaction_summary': transaction_summary,
            'budget_statuses': budget_statuses,
            'recent_transactions': [t.to_dict() for t in recent_transactions],
            'unread_alert_count': len(unread_alerts),
            'monthly_trends': monthly_data,
            'category_breakdown': category_breakdown,
            'generated_at': datetime.now().isoformat()
        }
    
    def _calculate_monthly_trends(self) -> Dict[str, Dict[str, float]]:
        """Calculate income and expenses by month."""
        trends = {}
        transactions = self.transaction_manager.transactions
        
        for t in transactions:
            month = t.date[:7]  # YYYY-MM
            if month not in trends:
                trends[month] = {'income': 0, 'expenses': 0, 'net': 0}
            
            if t.type == TransactionType.INCOME.value:
                trends[month]['income'] += t.amount
            elif t.type == TransactionType.EXPENSE.value:
                trends[month]['expenses'] += t.amount
        
        for month in trends:
            trends[month]['net'] = trends[month]['income'] - trends[month]['expenses']
        
        return trends
    
    def _get_category_breakdown(self) -> Dict[str, float]:
        """Get expense breakdown by category."""
        breakdown = {}
        expenses = [t for t in self.transaction_manager.transactions 
                       if t.type == TransactionType.EXPENSE.value]
        
        for t in expenses:
            cat = self.category_manager.get_category(t.category_id)
            cat_name = cat.name if cat else 'Unknown'
            breakdown[cat_name] = breakdown.get(cat_name, 0) + t.amount
        
        return breakdown
    
    # =========================================================================
    # REPORTING METHODS
    # =========================================================================
    
    def generate_report(self, report_type: str = "summary", 
                       start_date: str = None, end_date: str = None,
                       account_id: str = None) -> Dict[str, Any]:
        """Generate a financial report."""
        start = start_date or (date.today() - timedelta(days=30)).isoformat()
        end = end_date or date.today().isoformat()
        
        if report_type == "summary":
            return self._generate_summary_report(start, end, account_id)
        elif report_type == "income_expense":
            return self._generate_income_expense_report(start, end, account_id)
        elif report_type == "category":
            return self._generate_category_report(start, end, account_id)
        elif report_type == "budget":
            return self._generate_budget_report()
        elif report_type == "account":
            return self._generate_account_report(account_id)
        else:
            raise ValueError(f"Unknown report type: {report_type}")
    
    def _generate_summary_report(self, start_date: str, end_date: str, 
                                account_id: str = None) -> Dict[str, Any]:
        """Generate a summary report."""
        summary = self.transaction_manager.get_summary(start_date, end_date, account_id)
        
        # Get top expense categories
        transactions = self.transaction_manager.get_transactions_by_date_range(start_date, end_date)
        if account_id:
            transactions = [t for t in transactions if t.account_id == account_id]
        
        expenses = [t for t in transactions if t.type == TransactionType.EXPENSE.value]
        top_expenses = sorted(expenses, key=lambda t: t.amount, reverse=True)[:5]
        
        return {
            'report_type': 'summary',
            'period': {'start': start_date, 'end': end_date},
            'summary': summary,
            'top_expenses': [{'description': t.description, 'amount': t.amount, 'date': t.date} 
                               for t in top_expenses],
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_income_expense_report(self, start_date: str, end_date: str,
                                          account_id: str = None) -> Dict[str, Any]:
        """Generate income vs expense report."""
        transactions = self.transaction_manager.get_transactions_by_date_range(start_date, end_date)
        if account_id:
            transactions = [t for t in transactions if t.account_id == account_id]
        
        # Group by month
        monthly = {}
        for t in transactions:
            month = t.date[:7]
            if month not in monthly:
                monthly[month] = {'income': 0, 'expenses': 0}
            
            if t.type == TransactionType.INCOME.value:
                monthly[month]['income'] += t.amount
            elif t.type == TransactionType.EXPENSE.value:
                monthly[month]['expenses'] += t.amount
        
        return {
            'report_type': 'income_expense',
            'period': {'start': start_date, 'end': end_date},
            'monthly_breakdown': monthly,
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_category_report(self, start_date: str, end_date: str,
                                  account_id: str = None) -> Dict[str, Any]:
        """Generate category breakdown report."""
        transactions = self.transaction_manager.get_transactions_by_date_range(start_date, end_date)
        if account_id:
            transactions = [t for t in transactions if t.account_id == account_id]
        
        expenses = [t for t in transactions if t.type == TransactionType.EXPENSE.value]
        
        category_totals = {}
        for t in expenses:
            cat = self.category_manager.get_category(t.category_id)
            cat_name = cat.name if cat else 'Unknown'
            if cat_name not in category_totals:
                category_totals[cat_name] = {'amount': 0, 'count': 0, 'color': cat.color if cat else '#888'}
            category_totals[cat_name]['amount'] += t.amount
            category_totals[cat_name]['count'] += 1
        
        return {
            'report_type': 'category',
            'period': {'start': start_date, 'end': end_date},
            'category_breakdown': category_totals,
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_budget_report(self) -> Dict[str, Any]:
        """Generate budget performance report."""
        statuses = self.budget_manager.get_all_budgets_status()
        
        return {
            'report_type': 'budget',
            'budgets': statuses,
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_account_report(self, account_id: str = None) -> Dict[str, Any]:
        """Generate account statement report."""
        accounts = [self.account_manager.get_account(account_id)] if account_id \
                   else self.account_manager.get_active_accounts()
        
        account_reports = []
        for account in accounts:
            transactions = self.transaction_manager.get_transactions_by_account(account.id)
            sorted_transactions = sorted(
                transactions,
                key=lambda t: datetime.fromisoformat(t.date),
                reverse=True
            )[:50]
            
            total_in = sum(t.amount for t in transactions if t.type == TransactionType.INCOME.value)
            total_out = sum(t.amount for t in transactions if t.type == TransactionType.EXPENSE.value)
            
            account_reports.append({
                'account_name': account.name,
                'account_type': account.type,
                'current_balance': account.balance,
                'total_inflow': round(total_in, 2),
                'total_outflow': round(total_out, 2),
                'recent_transactions': [t.to_dict() for t in sorted_transactions]
            })
        
        return {
            'report_type': 'account',
            'accounts': account_reports,
            'generated_at': datetime.now().isoformat()
        }
    
    # =========================================================================
    # IMPORT/EXPORT METHODS
    # =========================================================================
    
    def export_data(self, export_format: str = "json") -> Dict[str, Any]:
        """Export all financial data."""
        data = {
            'export_date': datetime.now().isoformat(),
            'version': '1.0',
            'accounts': [a.to_dict() for a in self.account_manager.accounts],
            'categories': [c.to_dict() for c in self.category_manager.categories],
            'transactions': [t.to_dict() for t in self.transaction_manager.transactions],
            'budgets': [b.to_dict() for b in self.budget_manager.budgets]
        }
        
        if export_format == "json":
            return {'format': 'json', 'data': data}
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    
    def import_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Import financial data."""
        import_results = {
            'accounts_created': 0,
            'categories_created': 0,
            'transactions_created': 0,
            'budgets_created': 0,
            'errors': []
        }
        
        # Import accounts
        for acc_data in data.get('accounts', []):
            try:
                if not self.account_manager.get_account(acc_data.get('id')):
                    self.account_manager.create_account(
                        name=acc_data['name'],
                        type_str=acc_data['type'],
                        balance=acc_data.get('balance', 0),
                        currency=acc_data.get('currency', 'ZAR'),
                        institution=acc_data.get('institution', ''),
                        account_number=acc_data.get('account_number', '')
                    )
                    import_results['accounts_created'] += 1
            except Exception as e:
                import_results['errors'].append(f"Account import error: {str(e)}")
        
        # Import categories
        for cat_data in data.get('categories', []):
            try:
                if not self.category_manager.get_category(cat_data.get('id')):
                    self.category_manager.create_category(
                        name=cat_data['name'],
                        type_str=cat_data['type'],
                        icon=cat_data.get('icon', 'tag'),
                        color=cat_data.get('color', '#007a55')
                    )
                    import_results['categories_created'] += 1
            except Exception as e:
                import_results['errors'].append(f"Category import error: {str(e)}")
        
        # Import transactions
        for trans_data in data.get('transactions', []):
            try:
                self.transaction_manager.create_transaction(
                    account_id=trans_data['account_id'],
                    type_str=trans_data['type'],
                    amount=trans_data['amount'],
                    category_id=trans_data.get('category_id'),
                    description=trans_data.get('description', ''),
                    date_str=trans_data.get('date'),
                    payee=trans_data.get('payee', ''),
                    notes=trans_data.get('notes', ''),
                    tags=trans_data.get('tags', [])
                )
                import_results['transactions_created'] += 1
            except Exception as e:
                import_results['errors'].append(f"Transaction import error: {str(e)}")
        
        # Import budgets
        for budget_data in data.get('budgets', []):
            try:
                self.budget_manager.create_budget(
                    name=budget_data['name'],
                    category_id=budget_data['category_id'],
                    amount=budget_data['amount'],
                    period=budget_data.get('period', 'monthly')
                )
                import_results['budgets_created'] += 1
            except Exception as e:
                import_results['errors'].append(f"Budget import error: {str(e)}")
        
        return import_results
    
    def export_transactions_csv(self, start_date: str = None, end_date: str = None) -> str:
        """Export transactions as CSV."""
        return self.transaction_manager.export_transactions_csv(start_date, end_date)
    
    def import_transactions_csv(self, csv_content: str, account_id: str = None) -> Dict[str, Any]:
        """Import transactions from CSV."""
        return self.storage.import_transactions_csv(csv_content, account_id)
    
    def generate_recurring_transactions(self, up_to_date: str = None) -> List[Dict]:
        """Generate recurring transactions up to the specified date."""
        transactions = self.transaction_manager.generate_recurring_transactions(up_to_date)
        return [t.to_dict() for t in transactions]
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def run_health_check(self) -> Dict[str, Any]:
        """Run system health check."""
        issues = []
        
        # Check for overdue budget alerts
        self.alert_manager.check_budget_alerts()
        
        # Check for low balances
        self.alert_manager.check_balance_alerts()
        
        return {
            'status': 'healthy' if not issues else 'warning',
            'issues': issues,
            'timestamp': datetime.now().isoformat()
        }
    
    def run_daily_maintenance(self) -> Dict[str, Any]:
        """Run daily maintenance tasks."""
        results = {
            'recurring_generated': 0,
            'alerts_created': 0,
            'old_alerts_cleared': 0
        }
        
        # Generate recurring transactions
        recurring = self.generate_recurring_transactions()
        results['recurring_generated'] = len(recurring)
        
        # Check for budget alerts
        budget_alerts = self.alert_manager.check_budget_alerts()
        results['alerts_created'] += len(budget_alerts)
        
        # Check for low balance alerts
        balance_alerts = self.alert_manager.check_balance_alerts()
        results['alerts_created'] += len(balance_alerts)
        
        # Clear old alerts (older than 30 days)
        results['old_alerts_cleared'] = self.alert_manager.clear_old_alerts(30)
        
        logger.info(f"Daily maintenance completed: {results}")
        return results
    
    def clear_all_data(self) -> bool:
        """Clear all financial data (use with caution!)."""
        self.storage._write_json(self.storage.transactions_file, [])
        self.storage._write_json(self.storage.accounts_file, [])
        self.storage._write_json(self.storage.budgets_file, [])
        self.storage._write_json(self.storage.alerts_file, [])

        # Ledger and compliance collections
        self.storage._write_json(self.storage.contacts_file, [])
        self.storage._write_json(self.storage.receivables_file, [])
        self.storage._write_json(self.storage.payables_file, [])
        self.storage._write_json(self.storage.tax_records_file, [])
        self.storage._write_json(self.storage.payroll_runs_file, [])
        self.storage._write_json(self.storage.forecasts_file, [])
        if os.path.exists(self.storage.entity_profile_file):
            os.remove(self.storage.entity_profile_file)

        # Drop the in-memory caches so the next read comes from disk
        self.category_manager._categories = None
        self.account_manager._accounts = None
        self.transaction_manager._transactions = None
        self.budget_manager._budgets = None
        self.alert_manager._alerts = None
        self.contact_manager._contacts = None
        self.receivable_manager._items = None
        self.payable_manager._items = None
        self.tax_manager._records = None
        self.payroll_manager._runs = None
        self.forecast_manager._scenarios = None
        self.entity_manager._profile = None
        self.entity_manager._saved = False

        logger.warning("All financial data has been cleared")
        return True

    # =========================================================================
    # LEDGER AND COMPLIANCE
    # =========================================================================

    def get_ledger_overview(self, reference: str = None) -> Dict[str, Any]:
        """Everything owed in and out, with aging on both sides."""
        from finance_core import periods as _periods

        ref = _periods.parse_date(reference) if reference else _periods.today()
        return {
            'as_of': ref.isoformat(),
            'receivables': self.receivable_manager.list_entries(reference=ref),
            'payables': self.payable_manager.list_entries(reference=ref),
            'receivable_totals': self.receivable_manager.totals(ref),
            'payable_totals': self.payable_manager.totals(ref),
            'receivable_aging': self.receivable_manager.aging(ref),
            'payable_aging': self.payable_manager.aging(ref),
            'contacts': [c.to_dict() for c in self.contact_manager.get_active_contacts()],
        }

    def get_compliance_overview(self, reference: str = None) -> Dict[str, Any]:
        """Tax, payroll and structuring status in one payload."""
        from finance_core import periods as _periods

        ref = _periods.parse_date(reference) if reference else _periods.today()
        vat = self.tax_manager.estimate_vat(
            _periods.month_start(ref).isoformat(), ref.isoformat()
        )
        return {
            'as_of': ref.isoformat(),
            'profile': self.entity_manager.profile.to_dict(),
            'tax': {
                'records': self.tax_manager.list_records(reference=ref),
                'upcoming': self.tax_manager.upcoming_obligations(reference=ref),
                'vat_estimate': vat,
            },
            'payroll': {
                'runs': self.payroll_manager.list_runs(ref.year),
                'flags': self.payroll_manager.compliance_flags(ref),
                'totals': self.payroll_manager.totals(ref.year),
            },
            'structuring': self.entity_manager.structuring_checklist(self.account_manager),
        }

    def get_money_position(self, start: str = None, end: str = None,
                           reference: str = None) -> Dict[str, Any]:
        """The five questions answered for a period."""
        from finance_core import periods as _periods

        return self.statement_builder.money_position(
            start, end,
            _periods.parse_date(reference) if reference else None,
        )

    def get_financial_statements(self, report_type: str, start: str = None,
                                end: str = None, **options) -> Dict[str, Any]:
        """Build one of the formal statements.

        Supported types: profit_loss, balance_sheet, cash_flow,
        expense_analysis, records_health, funding_readiness.
        """
        builders = {
            'profit_loss': lambda: self.statement_builder.profit_and_loss(
                start, end, options.get('account_id')),
            'balance_sheet': lambda: self.statement_builder.balance_sheet(end),
            'cash_flow': lambda: self.statement_builder.cash_flow(
                start, end, options.get('account_id')),
            'expense_analysis': lambda: self.statement_builder.expense_analysis(start, end),
            'records_health': lambda: self.statement_builder.records_health(end),
            'funding_readiness': lambda: self.statement_builder.funding_readiness(
                end, options.get('months', 12)),
        }
        if report_type not in builders:
            raise ValueError(
                f"Unknown report type '{report_type}'. Use one of: "
                f"{', '.join(sorted(builders))}"
            )
        return builders[report_type]()


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_finance_core(storage_dir: str = None) -> FinanceCore:
    """Factory function to create a FinanceCore instance."""
    return FinanceCore(storage_dir)
