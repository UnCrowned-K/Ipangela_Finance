"""Financial statements, position summaries and lender-facing metrics.

This is where the accounting questions get answered: what came in, what went
out, what is owed both ways, what was actually earned, and whether the records
would satisfy a bank or a tax practitioner.

Two distinctions are kept explicit throughout, because conflating them is the
usual way small businesses misread their own numbers:

* **Cash basis** - income and expenses as they hit the bank. This is what the
  transaction ledger can prove.
* **Accrual basis** - income earned and costs incurred, which is what a
  profit figure is legally meant to represent. It differs from cash whenever
  a sale is on credit or a supplier bill is unpaid.

Every derived figure states which basis it uses. Neither basis is "the" profit;
they answer different questions.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from finance_core.models import TransactionType, TaxStatus
from finance_core import periods

logger = logging.getLogger(__name__)

#: Category name fragments that indicate a direct cost rather than overhead.
COGS_PATTERNS = (
    'cost of sales', 'cost of goods', 'cogs', 'direct cost', 'direct material',
    'materials', 'stock', 'inventory', 'subcontract', 'freight in',
)

#: Records-health checks, worst first.
HEALTH_SEVERITY = {'critical': 0, 'warning': 1, 'info': 2}


def _round(value: float, places: int = 2) -> float:
    return round(value + 0.0, places)


def _is_settlement(transaction: Any) -> bool:
    """True when a transaction was posted to settle a ledger entry.

    Settlements move cash but do not create new income or cost, so the
    accrual figures exclude them and take the invoice or bill instead.
    """
    tags = getattr(transaction, 'tags', None) or []
    if 'settlement' in tags:
        return True
    notes = (getattr(transaction, 'notes', '') or '').lower()
    return notes.startswith('settles receivable') or notes.startswith('settles payable')


def _pct(numerator: float, denominator: float, places: int = 1) -> float:
    """Percentage that returns 0 rather than dividing by zero."""
    if not denominator:
        return 0.0
    return round(numerator / denominator * 100, places)


class StatementBuilder:
    """Builds statements and position summaries from the finance managers."""

    def __init__(self, transaction_manager=None, account_manager=None,
                 receivable_manager=None, payable_manager=None,
                 category_manager=None, tax_manager=None, payroll_manager=None,
                 entity_manager=None):
        self.transaction_manager = transaction_manager
        self.account_manager = account_manager
        self.receivable_manager = receivable_manager
        self.payable_manager = payable_manager
        self.category_manager = category_manager
        self.tax_manager = tax_manager
        self.payroll_manager = payroll_manager
        self.entity_manager = entity_manager

    # -- helpers -----------------------------------------------------------
    def _transactions(self, start: date, end: date, account_id: str = None) -> List[Any]:
        if self.transaction_manager is None:
            return []
        rows = self.transaction_manager.get_transactions_by_date_range(
            start.isoformat(), end.isoformat()
        )
        if account_id:
            rows = [t for t in rows if t.account_id == account_id]
        return sorted(rows, key=lambda t: t.date)

    def _category_name(self, category_id: str) -> str:
        if self.category_manager is None:
            return 'Uncategorised'
        category = self.category_manager.get_category(category_id)
        return category.name if category else 'Uncategorised'

    def _cogs_category_ids(self) -> set:
        """Category ids treated as cost of sales.

        Inferred from category names because the schema has no flag for it,
        so this stays visible in the statement output as ``cogs_categories``.
        """
        if self.category_manager is None:
            return set()
        return {
            c.id for c in self.category_manager.get_categories_by_type('expense')
            if any(pattern in c.name.lower() for pattern in COGS_PATTERNS)
        }

    def _ledger_totals(self, reference: date) -> Tuple[float, float]:
        """Outstanding receivables and payables as at ``reference``."""
        receivable = payable = 0.0
        if self.receivable_manager is not None:
            receivable = _round(sum(
                e['outstanding'] for e in self.receivable_manager.list_entries(reference=reference)
            ))
        if self.payable_manager is not None:
            payable = _round(sum(
                e['outstanding'] for e in self.payable_manager.list_entries(reference=reference)
            ))
        return receivable, payable

    def _unpaid_tax(self, reference: date) -> float:
        """Tax recorded but not yet paid."""
        if self.tax_manager is None:
            return 0.0
        total = 0.0
        for row in self.tax_manager.list_records(reference=reference):
            if row['status'] in (TaxStatus.PAID.value, TaxStatus.NOT_APPLICABLE.value):
                continue
            total += row['tax_amount']
        return _round(total)

    # -- profit and loss ---------------------------------------------------
    def profit_and_loss(self, start, end, account_id: str = None) -> Dict[str, Any]:
        """Income statement on both a cash and an accrual basis."""
        start_date, end_date = periods.require_range(start, end)
        ref = periods.today()
        rows = self._transactions(start_date, end_date, account_id)

        cash_income = _round(sum(t.amount for t in rows if t.type == TransactionType.INCOME.value))
        cash_expenses = _round(sum(t.amount for t in rows if t.type == TransactionType.EXPENSE.value))
        transfers = _round(sum(t.amount for t in rows if t.type == TransactionType.TRANSFER.value))

        cogs_ids = self._cogs_category_ids()
        expense_lines: Dict[str, Dict[str, Any]] = {}
        cogs_total = 0.0
        for t in rows:
            if t.type != TransactionType.EXPENSE.value:
                continue
            name = self._category_name(t.category_id)
            is_cogs = t.category_id in cogs_ids
            if is_cogs:
                cogs_total += t.amount
            line = expense_lines.setdefault(name, {
                'category_id': t.category_id, 'amount': 0.0, 'count': 0, 'is_cogs': is_cogs,
            })
            line['amount'] += t.amount
            line['count'] += 1

        cogs_total = _round(cogs_total)
        operating_expenses = _round(cash_expenses - cogs_total)

        lines = []
        for name, line in expense_lines.items():
            lines.append({
                'category': name,
                'category_id': line['category_id'],
                'amount': _round(line['amount']),
                'count': line['count'],
                'is_cogs': line['is_cogs'],
                'share_pct': _pct(line['amount'], cash_expenses),
            })
        lines.sort(key=lambda l: l['amount'], reverse=True)

        gross_profit = _round(cash_income - cogs_total)
        net_profit = _round(gross_profit - operating_expenses)

        # Accrual adjustments: money earned but not yet received, and costs
        # incurred but not yet paid. Movement is measured across the period.
        accrual = self._accrual_adjustments(start_date, end_date, rows)

        return {
            'report_type': 'profit_loss',
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'label': periods.describe_period(start_date, end_date),
                'days': (end_date - start_date).days + 1,
            },
            'cash_basis': {
                'income': cash_income,
                'expenses': cash_expenses,
                'cost_of_sales': cogs_total,
                'operating_expenses': operating_expenses,
                'gross_profit': gross_profit,
                'net_profit': net_profit,
                'net_margin_pct': _pct(net_profit, cash_income),
                'transfers': transfers,
            },
            'accrual_basis': accrual,
            'expense_lines': lines,
            'cogs_categories': sorted(
                line['category'] for line in lines if line['is_cogs']
            ),
            'basis_note': (
                "Cash basis counts money that actually moved. Accrual basis "
                "counts income earned and costs incurred, so it includes sales "
                "you have not been paid for yet and bills you have not paid yet."
            ),
            'generated_at': periods.today().isoformat(),
        }

    def _accrual_adjustments(self, start: date, end: date, rows: List[Any]) -> Dict[str, Any]:
        """Accrual-basis income, costs and profit for a period.

        Neither source is complete on its own: a cash sale is never a
        receivable, and a credit sale is never an income transaction until it
        settles. So accrual income is cash income *excluding* the settlement
        payments already captured in the ledger, plus every invoice raised in
        the period. Without that exclusion an invoice raised and settled
        inside the same period would be counted twice.
        """
        settled = [t for t in rows if _is_settlement(t)]
        cash_income = sum(
            t.amount for t in rows
            if t.type == TransactionType.INCOME.value and not _is_settlement(t)
        )
        cash_costs = sum(
            t.amount for t in rows
            if t.type == TransactionType.EXPENSE.value and not _is_settlement(t)
        )
        settled_income = sum(t.amount for t in settled if t.type == TransactionType.INCOME.value)
        settled_costs = sum(t.amount for t in settled if t.type == TransactionType.EXPENSE.value)

        invoiced = 0.0
        if self.receivable_manager is not None:
            for row in self.receivable_manager.list_entries(reference=end):
                issued = periods.parse_date(row['issue_date'])
                if issued and start <= issued <= end:
                    invoiced += row['amount']

        billed = 0.0
        if self.payable_manager is not None:
            for row in self.payable_manager.list_entries(reference=end):
                issued = periods.parse_date(row['issue_date'])
                if issued and start <= issued <= end:
                    billed += row['amount']

        accrual_income = _round(cash_income + invoiced)
        accrual_costs = _round(cash_costs + billed)
        accrual_net = _round(accrual_income - accrual_costs)

        return {
            'income_earned': accrual_income,
            'costs_incurred': accrual_costs,
            'net_profit': accrual_net,
            'net_margin_pct': _pct(accrual_net, accrual_income),
            'from_cash_transactions': _round(cash_income),
            'from_customer_invoices': _round(invoiced),
            'from_cash_expenses': _round(cash_costs),
            'from_supplier_bills': _round(billed),
            'settlements_received': _round(settled_income),
            'settlements_paid': _round(settled_costs),
            'basis_note': (
                "Cash sales and invoices raised this period are income; cash "
                "expenses and supplier bills received this period are costs. "
                "Payments that settle a ledger entry are excluded, so an invoice "
                "raised and settled in the same period is counted once."
            ),
        }

    # -- balance sheet -----------------------------------------------------
    def balance_sheet(self, as_of=None) -> Dict[str, Any]:
        """Statement of financial position at a point in time.

        Owner equity is the balancing figure, so the statement balances by
        construction. It only becomes meaningful once accounts, receivables
        and payables are all being maintained.
        """
        ref = periods.parse_date(as_of) if as_of else periods.today()
        cash_by_type: Dict[str, float] = {}
        total_cash = 0.0
        loans = 0.0
        if self.account_manager is not None:
            for account in self.account_manager.get_active_accounts():
                balance = _round(account.balance)
                cash_by_type.setdefault(account.type, 0.0)
                cash_by_type[account.type] = _round(cash_by_type[account.type] + balance)
                total_cash = _round(total_cash + balance)
                if account.type == 'loan' and balance < 0:
                    loans = _round(loans - balance)

        receivables, payables = self._ledger_totals(ref)
        tax_payable = self._unpaid_tax(ref)

        current_assets = _round(total_cash + receivables)
        current_liabilities = _round(payables + tax_payable + loans)
        total_assets = current_assets
        total_liabilities = current_liabilities
        equity = _round(total_assets - total_liabilities)

        return {
            'report_type': 'balance_sheet',
            'as_of': ref.isoformat(),
            'assets': {
                'cash_and_bank': total_cash,
                'cash_by_type': cash_by_type,
                'accounts_receivable': receivables,
                'total_assets': total_assets,
            },
            'liabilities': {
                'accounts_payable': payables,
                'tax_payable': tax_payable,
                'loans': loans,
                'total_liabilities': total_liabilities,
            },
            'equity': {
                'owners_equity': equity,
                'working_capital': _round(current_assets - current_liabilities),
            },
            'checks': {
                'balances': _round(total_assets - (total_liabilities + equity)) == 0,
                'current_ratio': round(current_assets / current_liabilities, 2) if current_liabilities else None,
            },
            'basis_note': (
                "Owner equity is derived as assets minus liabilities, so the "
                "statement balances by construction. Inventory, fixed assets "
                "and depreciation are not tracked, so this is not a complete "
                "statement of financial position."
            ),
            'generated_at': datetime.now().isoformat(),
        }

    # -- cash flow ---------------------------------------------------------
    def cash_flow(self, start, end, account_id: str = None) -> Dict[str, Any]:
        """Cash movement over a period, split by activity."""
        start_date, end_date = periods.require_range(start, end)
        rows = self._transactions(start_date, end_date, account_id)

        operating_in = 0.0
        operating_out = 0.0
        investing = 0.0
        financing = 0.0

        investment_types = ('investment',)
        loan_types = ('loan',)

        for t in rows:
            if t.type == TransactionType.INCOME.value:
                operating_in += t.amount
            elif t.type == TransactionType.EXPENSE.value:
                operating_out += t.amount
            elif t.type == TransactionType.TRANSFER.value:
                source_type = self._account_type(t.account_id)
                dest_type = self._account_type(t.destination_account_id)
                if dest_type in investment_types and source_type not in investment_types:
                    investing -= t.amount
                elif source_type in investment_types and dest_type not in investment_types:
                    investing += t.amount
                elif dest_type in loan_types or source_type in loan_types:
                    if dest_type in loan_types:
                        financing -= t.amount
                    else:
                        financing += t.amount

        operating_net = _round(operating_in - operating_out)
        net_change = _round(operating_net + investing + financing)

        closing_cash = 0.0
        if self.account_manager is not None:
            closing_cash = _round(self.account_manager.get_total_balance()['total'])

        return {
            'report_type': 'cash_flow',
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'label': periods.describe_period(start_date, end_date),
            },
            'operating': {
                'cash_in': _round(operating_in),
                'cash_out': _round(operating_out),
                'net': operating_net,
            },
            'investing': {'net': _round(investing)},
            'financing': {'net': _round(financing)},
            'net_change': net_change,
            'closing_cash': closing_cash,
            'opening_cash': _round(closing_cash - net_change),
            'basis_note': (
                "Opening cash is derived by backing the net movement out of the "
                "current balance, because account balances are stored as a "
                "single running figure rather than a dated history."
            ),
            'generated_at': datetime.now().isoformat(),
        }

    def _account_type(self, account_id: str) -> str:
        if self.account_manager is None or not account_id:
            return ''
        account = self.account_manager.get_account(account_id)
        return account.type if account else ''

    # -- the five questions ------------------------------------------------
    def money_position(self, start=None, end=None, reference: date = None) -> Dict[str, Any]:
        """The five numbers a business owner should always be able to answer.

        Mirrors the question set in the source material: what came in, what
        went out, what you owe, what you are owed, and what you actually made.
        """
        ref = reference or periods.today()
        start_date = periods.parse_date(start) if start else periods.month_start(ref)
        end_date = periods.parse_date(end) if end else ref
        if end_date < start_date:
            start_date, end_date = end_date, start_date

        rows = self._transactions(start_date, end_date)
        came_in = _round(sum(t.amount for t in rows if t.type == TransactionType.INCOME.value))
        went_out = _round(sum(t.amount for t in rows if t.type == TransactionType.EXPENSE.value))
        owed_to_us, we_owe = self._ledger_totals(ref)

        accrual = self._accrual_adjustments(start_date, end_date, rows)
        actual_profit = accrual['net_profit']

        cash_total = 0.0
        if self.account_manager is not None:
            cash_total = _round(self.account_manager.get_total_balance()['total'])

        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'label': periods.describe_period(start_date, end_date),
            },
            'as_of': ref.isoformat(),
            'questions': [
                {
                    'key': 'came_in',
                    'label': 'What came in',
                    'help': 'Money received from customers and other income',
                    'amount': came_in,
                    'basis': 'cash',
                },
                {
                    'key': 'went_out',
                    'label': 'What went out',
                    'help': 'Money paid to suppliers, staff and everyone else',
                    'amount': went_out,
                    'basis': 'cash',
                },
                {
                    'key': 'owe',
                    'label': 'What you owe',
                    'help': 'Supplier bills still unpaid',
                    'amount': we_owe,
                    'basis': 'ledger',
                },
                {
                    'key': 'owed',
                    'label': "What you're owed",
                    'help': 'Customer invoices still unpaid',
                    'amount': owed_to_us,
                    'basis': 'ledger',
                },
                {
                    'key': 'actual_profit',
                    'label': 'What you actually made',
                    'help': 'Income earned minus costs incurred, regardless of when cash moved',
                    'amount': actual_profit,
                    'basis': 'accrual',
                },
            ],
            'net_cash_position': _round(cash_total + owed_to_us - we_owe),
            'cash_in_bank': cash_total,
            'net_margin_pct': _pct(actual_profit, accrual['income_earned']),
            'generated_at': datetime.now().isoformat(),
        }

    # -- expenses ----------------------------------------------------------
    def expense_analysis(self, start, end) -> Dict[str, Any]:
        """Where the money goes, split into committed and discretionary spend."""
        start_date, end_date = periods.require_range(start, end)
        rows = self._transactions(start_date, end_date)
        expenses = [t for t in rows if t.type == TransactionType.EXPENSE.value]
        total = _round(sum(t.amount for t in expenses))

        committed = _round(sum(t.amount for t in expenses if t.is_recurring))
        discretionary = _round(total - committed)

        by_category: Dict[str, Dict[str, Any]] = {}
        for t in expenses:
            name = self._category_name(t.category_id)
            row = by_category.setdefault(name, {
                'category': name, 'category_id': t.category_id, 'amount': 0.0, 'count': 0,
            })
            row['amount'] += t.amount
            row['count'] += 1

        months = max(1, periods.months_in_range(start_date, end_date))
        largest = max(expenses, key=lambda t: t.amount) if expenses else None

        lines = []
        for name, row in by_category.items():
            lines.append({
                'category': name,
                'category_id': row['category_id'],
                'amount': _round(row['amount']),
                'count': row['count'],
                'share_pct': _pct(row['amount'], total),
                'avg_per_month': _round(row['amount'] / months),
            })
        lines.sort(key=lambda l: l['amount'], reverse=True)

        return {
            'report_type': 'expense_analysis',
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'label': periods.describe_period(start_date, end_date),
                'months': months,
            },
            'total_expenses': total,
            'committed_expenses': committed,
            'discretionary_expenses': discretionary,
            'committed_share_pct': _pct(committed, total),
            'avg_per_month': _round(total / months),
            'largest_expense': {
                'description': largest.description if largest else '',
                'amount': _round(largest.amount) if largest else 0.0,
                'date': largest.date if largest else None,
                'category': self._category_name(largest.category_id) if largest else '',
            } if largest else None,
            'by_category': lines,
            'basis_note': (
                "Committed spend is anything marked as recurring. Treat it as a "
                "guide: a one-off that repeats is not flagged, and a recurring "
                "label does not mean a contract exists."
            ),
            'generated_at': datetime.now().isoformat(),
        }

    # -- records health ----------------------------------------------------
    def records_health(self, reference: date = None) -> Dict[str, Any]:
        """How complete the records are, in the terms a lender or auditor uses.

        The source material's point is that software only helps if it is
        actually kept up to date, so this measures the records themselves
        rather than the money in them.
        """
        ref = periods.parse_date(reference) if reference else periods.today()
        transactions = self.transaction_manager.transactions if self.transaction_manager else []
        checks: List[Dict[str, Any]] = []

        def add(key: str, label: str, ok: bool, count: int, severity: str, hint: str) -> None:
            checks.append({
                'key': key, 'label': label, 'ok': ok, 'count': count,
                'severity': severity if not ok else 'info', 'hint': hint,
            })

        # Category coverage
        known = set()
        if self.category_manager is not None:
            known = {c.id for c in self.category_manager.categories}
        missing_category = [t for t in transactions if t.category_id not in known]
        add(
            'category_coverage', 'Every transaction has a category',
            not missing_category, len(missing_category), 'critical',
            "Transactions in 'Uncategorised' cannot be claimed as a business expense.",
        )

        # Payee recorded
        missing_payee = [t for t in transactions
                         if t.type == TransactionType.EXPENSE.value and not (t.payee or '').strip()]
        add(
            'payee_recorded', 'Every expense names who was paid',
            not missing_payee, len(missing_payee), 'warning',
            'SARS generally requires a supplier invoice or receipt, which needs a payee.',
        )

        # Supporting detail on expenses. A description counts: writing what
        # the spend was for is exactly the evidence being asked for.
        missing_note = [t for t in transactions
                        if t.type == TransactionType.EXPENSE.value
                        and not (t.description or '').strip()
                        and not (t.notes or '').strip()
                        and not t.tags]
        add(
            'expense_evidence', 'Expenses describe what they were for',
            not missing_note, len(missing_note), 'info',
            'A description, note or tag is what makes a claim defensible later.',
        )

        # Ledger entries linked to a known contact
        orphan = 0
        for manager in (self.receivable_manager, self.payable_manager):
            if manager is None:
                continue
            for row in manager.list_entries(reference=ref):
                if row['contact_name'] == 'Unknown contact':
                    orphan += 1
        add(
            'ledger_contacts', 'Every ledger entry is linked to a contact',
            orphan == 0, orphan, 'critical',
            'An invoice with no customer or supplier on it cannot be followed up.',
        )

        # Bookkeeping currency
        stale_days = 0
        if transactions:
            latest = max(periods.parse_date(t.date) or ref for t in transactions)
            stale_days = (ref - latest).days
        add(
            'bookkeeping_current', 'Transactions are up to date',
            stale_days <= 45, stale_days, 'warning',
            'Records older than about six weeks cannot support a funding application.',
        )

        # Accounts reconciled against a balance
        unreconciled = 0
        if self.account_manager is not None:
            unreconciled = sum(1 for a in self.account_manager.get_active_accounts() if a.balance == 0)
        add(
            'account_balances', 'Every account has a balance',
            unreconciled == 0, unreconciled, 'info',
            'A zero balance usually means the opening balance was never entered.',
        )

        outstanding = [c for c in checks if not c['ok']]
        outstanding.sort(key=lambda c: HEALTH_SEVERITY.get(c['severity'], 3))
        passed = len(checks) - len(outstanding)
        score = round(passed / len(checks) * 100) if checks else 0

        return {
            'report_type': 'records_health',
            'as_of': ref.isoformat(),
            'score': score,
            'band': 'good' if score >= 85 else ('needs_work' if score >= 60 else 'poor'),
            'checks_total': len(checks),
            'checks_passed': passed,
            'issues': outstanding,
            'all_checks': checks,
            'transaction_count': len(transactions),
            'days_since_last_entry': stale_days,
            'basis_note': (
                "This measures the completeness of your records, not the health "
                "of the business. A perfect score does not mean you are profitable."
            ),
            'generated_at': datetime.now().isoformat(),
        }

    # -- funding -----------------------------------------------------------
    def funding_readiness(self, reference: date = None, months: int = 12) -> Dict[str, Any]:
        """The metrics a bank or funder looks at before saying yes.

        Each metric carries a plain reading so the number is not just a score
        to guess at. Nothing here is a credit decision.
        """
        ref = periods.parse_date(reference) if reference else periods.today()
        year_start = periods.add_months(periods.month_start(ref), -(months - 1))
        start_date, end_date = year_start, ref

        rows = self._transactions(start_date, end_date)
        income = _round(sum(t.amount for t in rows if t.type == TransactionType.INCOME.value))
        expenses = _round(sum(t.amount for t in rows if t.type == TransactionType.EXPENSE.value))
        period_days = (end_date - start_date).days + 1

        monthly_income: List[float] = []
        monthly_expenses: List[float] = []
        for month in periods.iter_months(start_date, months):
            key = periods.month_key(month)
            next_month = periods.add_months(month, 1)
            window = [
                t for t in rows
                if key <= periods.month_key(t.date) < periods.month_key(next_month)
            ]
            monthly_income.append(_round(sum(t.amount for t in window if t.type == TransactionType.INCOME.value)))
            monthly_expenses.append(_round(sum(t.amount for t in window if t.type == TransactionType.EXPENSE.value)))

        receivables, payables = self._ledger_totals(ref)
        tax_payable = self._unpaid_tax(ref)
        cash = 0.0
        if self.account_manager is not None:
            cash = _round(self.account_manager.get_total_balance()['total'])

        current_assets = _round(cash + receivables)
        current_liabilities = _round(payables + tax_payable)
        current_ratio = round(current_assets / current_liabilities, 2) if current_liabilities else None
        dso = _round(receivables / income * period_days) if income else 0.0
        dpo = _round(payables / expenses * period_days) if expenses else 0.0
        avg_monthly_expenses = _round(expenses / max(1, months)) or 0.0
        runway = _round(cash / avg_monthly_expenses, 1) if avg_monthly_expenses else None
        margin = _pct(income - expenses, income)
        stability = _stability(monthly_income)
        growth = _growth(monthly_income)
        health = self.records_health(ref)
        # A single critical records problem is disqualifying on its own, so the
        # status follows the worst check rather than the average score. Scoring
        # it would let uncategorised transactions pass at 83%.
        worst = [i['severity'] for i in health['issues']]
        if 'critical' in worst:
            records_status = 'critical'
        elif 'warning' in worst:
            records_status = 'warning'
        elif health['score'] < 100:
            records_status = 'warning'
        else:
            records_status = 'good'

        metrics = [
            {
                'key': 'revenue', 'label': 'Revenue over the period',
                'value': income, 'format': 'currency',
                'reading': f"R{income:,.2f} recorded over {period_days} days",
                'status': 'good' if income > 0 else 'critical',
            },
            {
                'key': 'net_margin', 'label': 'Net margin',
                'value': margin, 'format': 'percent',
                'reading': _margin_reading(margin),
                'status': 'good' if margin >= 10 else ('warning' if margin > 0 else 'critical'),
            },
            {
                'key': 'current_ratio', 'label': 'Current ratio',
                'value': current_ratio, 'format': 'ratio',
                'reading': ('Nothing outstanding, so the ratio has no denominator'
                            if current_ratio is None
                            else f"R{current_assets:,.2f} of short-term assets against R{current_liabilities:,.2f} owed"),
                'status': ('info' if current_ratio is None
                           else 'good' if current_ratio >= 1.5
                           else 'warning' if current_ratio >= 1 else 'critical'),
            },
            {
                'key': 'dso', 'label': 'Days to get paid (DSO)',
                'value': dso, 'format': 'days',
                'reading': (f"Invoices take about {dso:.0f} days to be paid on average"
                            if income else 'No income recorded, so this cannot be measured'),
                'status': 'info' if not income else ('good' if dso <= 45 else 'warning' if dso <= 90 else 'critical'),
            },
            {
                'key': 'runway', 'label': 'Cash runway',
                'value': runway, 'format': 'months',
                'reading': ('No expenses recorded, so runway is undefined'
                            if runway is None
                            else f"About {runway} months of cover at the current spend rate"),
                'status': 'info' if runway is None else ('good' if runway >= 6 else 'warning' if runway >= 3 else 'critical'),
            },
            {
                'key': 'revenue_stability', 'label': 'Revenue consistency',
                'value': stability, 'format': 'percent',
                'reading': (f"Monthly income varies by about {100 - stability:.0f}% month to month"
                            if monthly_income and stability is not None
                            else 'Not enough months of income to judge'),
                'status': 'info' if stability is None else ('good' if stability >= 70 else 'warning' if stability >= 50 else 'critical'),
            },
            {
                'key': 'growth', 'label': 'Income trend',
                'value': growth, 'format': 'percent',
                'reading': _growth_reading(growth, monthly_income),
                'status': 'info' if growth is None else ('good' if growth > 0 else 'warning' if growth == 0 else 'critical'),
            },
            {
                'key': 'records_score', 'label': 'Records completeness',
                'value': health['score'], 'format': 'percent',
                'reading': (
                    f"{health['checks_passed']} of {health['checks_total']} record "
                    f"checks pass. {health['issues'][0]['hint']}"
                    if health['issues'] else
                    f"All {health['checks_total']} record checks pass"
                ),
                'status': records_status,
            },
        ]

        blockers = [m for m in metrics if m['status'] == 'critical']
        warnings = [m for m in metrics if m['status'] == 'warning']

        return {
            'report_type': 'funding_readiness',
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'label': periods.describe_period(start_date, end_date),
                'months': months,
            },
            'metrics': metrics,
            'monthly_income': monthly_income,
            'monthly_expenses': monthly_expenses,
            'blockers': [m['label'] for m in blockers],
            'warnings': [m['label'] for m in warnings],
            'ready': not blockers,
            'generated_at': datetime.now().isoformat(),
            'disclaimer': (
                "An internal readiness view built from your own records. It is "
                "not a credit assessment, and lenders look at factors this does "
                "not cover, such as security, guarantees and track record."
            ),
        }


def _stability(values: List[float]) -> Optional[float]:
    """Score 0-100 for how steady a monthly series is (100 = perfectly flat)."""
    active = [v for v in values if v > 0]
    if len(active) < 3:
        return None
    mean = sum(active) / len(active)
    if mean <= 0:
        return None
    variance = sum((v - mean) ** 2 for v in active) / len(active)
    deviation = variance ** 0.5
    return max(0.0, round(100 - (deviation / mean * 100), 1))


def _growth(values: List[float]) -> Optional[float]:
    """Percentage change between the most recent complete months."""
    if len(values) < 2:
        return None
    previous, current = values[-2], values[-1]
    if previous <= 0:
        return None
    return round((current - previous) / previous * 100, 1)


def _margin_reading(margin: float) -> str:
    if margin >= 20:
        return f"{margin}% of every rand of income is left after costs"
    if margin >= 10:
        return f"{margin}% margin: healthy for most small businesses"
    if margin > 0:
        return f"{margin}% margin: thin, one bad month turns it negative"
    if margin == 0:
        return "Break-even: income exactly matches costs"
    return f"Making a loss of {abs(margin)}% of income"


def _growth_reading(growth: Optional[float], values: List[float]) -> str:
    if growth is None:
        if not values or not any(v > 0 for v in values):
            return 'No income recorded yet'
        return 'Not enough months of income to show a trend'
    if growth > 0:
        return f"Most recent month is {growth}% up on the month before"
    if growth < 0:
        return f"Most recent month is {abs(growth)}% down on the month before"
    return 'Income is level with the month before'
