"""Tax, payroll, business structure and forecasting for South African users.

The figures this module produces are *planning aids*, not calculations of
record. VAT returns, provisional tax and income tax are determined by the
Income Tax Act, the VAT Act and SARS practice notes, and they depend on facts
the app cannot see: whether a business is registered for VAT, which expenses
carry input VAT, whether a payment was received or only accrued, and which
reliefs apply. Every summary therefore returns a ``disclaimer`` and the UI
shows it, so the software supports an accountant rather than pretending to
replace one.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from finance_core.models import (
    TaxRecord, PayrollRun, EntityProfile, ForecastScenario,
    TaxType, TaxStatus, PayrollStatus, EntityType, TransactionType
)
from finance_core.storage import DataStorage
from finance_core import periods
from utils import ValidationUtils

logger = logging.getLogger(__name__)

#: Shown wherever the module produces a tax or compliance figure.
COMPLIANCE_DISCLAIMER = (
    "These figures are planning estimates from your own records, not a tax "
    "calculation or filing. Confirm every amount and deadline with SARS or "
    "your registered tax practitioner before you submit anything."
)

#: Statuses that mean the obligation no longer needs attention.
SETTLED_TAX_STATUSES = (TaxStatus.PAID.value, TaxStatus.NOT_APPLICABLE.value)


def _round(value: float, places: int = 2) -> float:
    return round(value + 0.0, places)


def _now() -> str:
    return datetime.now().isoformat()


def _validate_tax_type(value: str) -> str:
    valid = [t.value for t in TaxType]
    if value not in valid:
        raise ValueError(f"Invalid tax type: must be one of {', '.join(valid)}")
    return value


def _validate_tax_status(value: str) -> str:
    valid = [s.value for s in TaxStatus]
    if value not in valid:
        raise ValueError(f"Invalid tax status: must be one of {', '.join(valid)}")
    return value


class TaxManager:
    """Tracks tax obligations, estimates and payment state."""

    def __init__(self, storage: DataStorage = None, transaction_manager=None,
                 entity_manager: 'EntityManager' = None):
        self.storage = storage or DataStorage()
        self.transaction_manager = transaction_manager
        self.entity_manager = entity_manager
        self._records = None

    # -- storage -----------------------------------------------------------
    @property
    def records(self) -> List[TaxRecord]:
        if self._records is None:
            self._load()
        return self._records

    def _load(self):
        self._records = [TaxRecord.from_dict(r) for r in self.storage.get_tax_records()]

    def _save(self):
        self.storage.save_tax_records([r.to_dict() for r in self.records])

    # -- reads -------------------------------------------------------------
    def get_record(self, record_id: str) -> Optional[TaxRecord]:
        return next((r for r in self.records if r.id == record_id), None)

    def list_records(self, tax_type: str = None, status: str = None,
                     year: int = None, reference: date = None) -> List[Dict[str, Any]]:
        """Tax records with overdue status derived from the due date."""
        ref = reference or periods.today()
        rows = []
        for record in self.records:
            effective = self.effective_status(record, ref)
            if tax_type and record.tax_type != tax_type:
                continue
            if status and effective != status:
                continue
            if year and not self._in_year(record, int(year)):
                continue
            payload = record.to_dict()
            payload.update({
                'status': effective,
                'days_to_due': (periods.require_date(record.due_date, "due_date") - ref).days,
                'period_label': periods.describe_period(record.period_start, record.period_end),
            })
            rows.append(payload)
        rows.sort(key=lambda r: (r['due_date'], r['id']))
        return rows

    def _in_year(self, record: TaxRecord, year: int) -> bool:
        return record.period_end.startswith(str(year)) or record.due_date.startswith(str(year))

    def effective_status(self, record: TaxRecord, reference: date = None) -> str:
        """Stored status, promoted to ``overdue`` once the due date passes.

        A record the user marked ``paid`` stays paid; the promotion only
        applies to obligations still outstanding.
        """
        stored = record.status
        if stored in SETTLED_TAX_STATUSES:
            return stored
        due = periods.parse_date(record.due_date, "due_date")
        if due and (reference or periods.today()) > due:
            return TaxStatus.OVERDUE.value
        return stored

    def totals_for_period(self, start, end, reference: date = None) -> Dict[str, Any]:
        """Tax liability and payments over an inclusive date range."""
        start_date, end_date = periods.require_range(start, end)
        ref = reference or periods.today()
        selected = [r for r in self.records
                    if start_date <= periods.require_date(r.period_end, "period_end") <= end_date]

        by_type: Dict[str, Dict[str, float]] = {}
        overdue_by_type: Dict[str, float] = {}
        for record in selected:
            status = self.effective_status(record, ref)
            if status in SETTLED_TAX_STATUSES:
                continue
            row = by_type.setdefault(record.tax_type, {
                'taxable_amount': 0.0, 'tax_amount': 0.0, 'count': 0,
            })
            row['taxable_amount'] = _round(row['taxable_amount'] + record.taxable_amount)
            row['tax_amount'] = _round(row['tax_amount'] + record.tax_amount)
            row['count'] += 1
            # Only the record that is actually past its due date is overdue, so
            # one late VAT period cannot make an upcoming PAYE bill look late.
            if status == TaxStatus.OVERDUE.value:
                overdue_by_type[record.tax_type] = _round(
                    overdue_by_type.get(record.tax_type, 0.0) + record.tax_amount
                )

        return {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'by_type': by_type,
            'outstanding_tax': _round(sum(r['tax_amount'] for r in by_type.values())),
            'overdue_tax': _round(sum(overdue_by_type.values())),
            'overdue_by_type': overdue_by_type,
            'record_count': len(selected),
            'disclaimer': COMPLIANCE_DISCLAIMER,
        }

    def upcoming_obligations(self, days: int = 60, reference: date = None) -> List[Dict[str, Any]]:
        """Outstanding obligations due within the next ``days`` days."""
        ref = reference or periods.today()
        horizon = periods.add_days(ref, max(0, int(days)))
        rows = []
        for record in self.records:
            status = self.effective_status(record, ref)
            if status in SETTLED_TAX_STATUSES:
                continue
            due = periods.parse_date(record.due_date, "due_date")
            if due is None or not (ref <= due <= horizon):
                continue
            payload = record.to_dict()
            payload.update({
                'status': status,
                'days_to_due': (due - ref).days,
                'is_overdue': due < ref,
                'period_label': periods.describe_period(record.period_start, record.period_end),
            })
            rows.append(payload)
        rows.sort(key=lambda r: r['due_date'])
        return rows

    def annual_return_readiness(self, reference: date = None,
                                year_end_month: int = None) -> Dict[str, Any]:
        """Where the business stands against its annual return deadline.

        Reports the tax year, the deadline, how long is left, and whether the
        records a return is built from are actually present.
        """
        ref = reference or periods.today()
        if year_end_month is None and self.entity_manager is not None:
            year_end_month = self.entity_manager.year_end_month
        year_start, year_end = periods.financial_year_bounds(
            ref, year_end_month or periods.DEFAULT_YEAR_END_MONTH
        )
        deadline = periods.annual_return_deadline(year_end)
        days_left = (deadline - ref).days

        declared = [r for r in self.records
                    if r.tax_type == TaxType.INCOME_TAX.value
                    and periods.parse_date(r.period_end) == year_end]
        provision = [r for r in self.records
                     if r.tax_type == TaxType.PROVISIONAL_TAX.value
                     and year_start <= periods.require_date(r.period_end) <= year_end]

        outstanding = [r for r in self.records
                       if self.effective_status(r, ref) == TaxStatus.OVERDUE.value]
        provisional_paid = [r for r in provision
                            if self.effective_status(r, ref) == TaxStatus.PAID.value]

        return {
            'tax_year': {
                'start': year_start.isoformat(),
                'end': year_end.isoformat(),
                'label': periods.financial_year_label(year_start, year_end),
            },
            'deadline': deadline.isoformat(),
            'days_remaining': days_left,
            'is_within_window': 0 <= days_left <= 365,
            'declared': len(declared) > 0,
            'declared_record': declared[0].to_dict() if declared else None,
            'provisional_periods': len(provision),
            'provisional_paid': len(provisional_paid),
            'overdue_records': len(outstanding),
            'disclaimer': COMPLIANCE_DISCLAIMER,
        }

    # -- VAT estimate ------------------------------------------------------
    def estimate_vat(self, start, end, vat_rate: float = periods.DEFAULT_VAT_RATE,
                     category_ids: Optional[set] = None) -> Dict[str, Any]:
        """Estimate net VAT payable for a period from recorded transactions.

        This is a rough guide: it assumes every recorded income is standard
        rated and every recorded expense carries full input VAT, which is why
        the caller can narrow the estimate to specific categories and the
        result is always labelled an estimate.
        """
        start_date, end_date = periods.require_range(start, end)
        try:
            rate = float(vat_rate)
        except (TypeError, ValueError):
            raise ValueError("vat_rate must be a number")
        if not 0 <= rate <= 1:
            raise ValueError("vat_rate must be between 0 and 1")

        income = 0.0
        expenses = 0.0
        counted = 0
        if self.transaction_manager is not None:
            for t in self.transaction_manager.get_transactions_by_date_range(
                    start_date.isoformat(), end_date.isoformat()):
                if category_ids and t.category_id not in category_ids:
                    continue
                counted += 1
                if t.type == TransactionType.INCOME.value:
                    income += t.amount
                elif t.type == TransactionType.EXPENSE.value:
                    expenses += t.amount

        income = _round(income)
        expenses = _round(expenses)
        output_vat = _round(income * rate)
        input_vat = _round(expenses * rate)
        return {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'vat_rate': rate,
            'vat_inclusive_income': income,
            'vat_inclusive_expenses': expenses,
            'output_vat': output_vat,
            'input_vat': input_vat,
            'net_vat_payable': _round(output_vat - input_vat),
            'is_estimated': True,
            'transaction_count': counted,
            'disclaimer': COMPLIANCE_DISCLAIMER,
        }

    def period_schedule(self, year_end_month: int = None, vat_interval: str = None,
                        periods_per_year: int = 2, reference: date = None
                        ) -> Dict[str, Any]:
        """Planned VAT and provisional tax periods for the current year.

        Returns a plan the user can turn into saved records; nothing is
        persisted here, so a schedule is safe to regenerate at any time.
        """
        if year_end_month is None and self.entity_manager is not None:
            year_end_month = self.entity_manager.year_end_month
        if vat_interval is None and self.entity_manager is not None:
            vat_interval = self.entity_manager.vat_interval
        year_end_month = year_end_month or periods.DEFAULT_YEAR_END_MONTH
        vat_interval = vat_interval or 'monthly'
        ref = reference or periods.today()

        year_start, year_end = periods.financial_year_bounds(ref, year_end_month)
        annual_due = periods.annual_return_deadline(year_end)
        existing = {(r.tax_type, r.period_start) for r in self.records}

        planned: List[Dict[str, Any]] = []
        for period in periods.vat_periods(year_end_month, vat_interval, ref):
            planned.append({
                'tax_type': TaxType.VAT.value,
                **period,
                'already_tracked': (TaxType.VAT.value, period['period_start']) in existing,
            })
        if vat_interval in periods.VAT_INTERVAL_MONTHS:
            for period in periods.provisional_tax_periods(year_end_month, ref, periods_per_year):
                planned.append({
                    'tax_type': TaxType.PROVISIONAL_TAX.value,
                    **period,
                    'already_tracked': (TaxType.PROVISIONAL_TAX.value, period['period_start']) in existing,
                })
        planned.append({
            'tax_type': TaxType.INCOME_TAX.value,
            'period_start': year_start.isoformat(),
            'period_end': year_end.isoformat(),
            'due_date': annual_due.isoformat(),
            'already_tracked': (TaxType.INCOME_TAX.value, year_start.isoformat()) in existing,
        })
        planned.sort(key=lambda p: p['due_date'])
        return {
            'financial_year': {
                'start': year_start.isoformat(),
                'end': year_end.isoformat(),
                'label': periods.financial_year_label(year_start, year_end),
            },
            'vat_interval': vat_interval,
            'periods': planned,
            'disclaimer': COMPLIANCE_DISCLAIMER,
        }

    # -- writes ------------------------------------------------------------
    def create_record(self, tax_type: str, period_start: str, period_end: str,
                      due_date: str, taxable_amount: float = 0.0,
                      tax_amount: float = 0.0, status: str = TaxStatus.ESTIMATED.value,
                      reference: str = "", provider: str = "",
                      notes: str = "") -> TaxRecord:
        """Record a tax obligation or estimate for a period."""
        tax_type = _validate_tax_type(tax_type)
        start, end = periods.require_range(period_start, period_end, "period_start", "period_end")
        due = periods.require_date(due_date, "due_date")
        if due < start:
            raise ValueError("due_date cannot be earlier than period_start")
        status = _validate_tax_status(status)

        record = TaxRecord(
            id=ValidationUtils.generate_secure_id(),
            tax_type=tax_type,
            period_start=start.isoformat(),
            period_end=end.isoformat(),
            due_date=due.isoformat(),
            taxable_amount=ValidationUtils.validate_amount(taxable_amount, "taxable_amount"),
            tax_amount=ValidationUtils.validate_amount(tax_amount, "tax_amount"),
            status=status,
            reference=ValidationUtils.sanitize_string(reference, "reference", 100),
            provider=ValidationUtils.sanitize_string(provider, "provider", 150),
            notes=ValidationUtils.sanitize_string(notes, "notes", 1000),
        )
        self.records.append(record)
        self._save()
        logger.info(f"Created {tax_type} record for {record.period_end} ({record.id})")
        return record

    def update_record(self, record_id: str, **kwargs) -> TaxRecord:
        """Update a tax record, re-validating any period or amount change."""
        record = self.get_record(record_id)
        if not record:
            raise ValueError(f"Tax record not found: {record_id}")

        if 'tax_type' in kwargs:
            record.tax_type = _validate_tax_type(kwargs['tax_type'])
        if 'status' in kwargs:
            record.status = _validate_tax_status(kwargs['status'])
        if 'period_start' in kwargs or 'period_end' in kwargs:
            start, end = periods.require_range(
                kwargs.get('period_start', record.period_start),
                kwargs.get('period_end', record.period_end),
                "period_start", "period_end",
            )
            record.period_start = start.isoformat()
            record.period_end = end.isoformat()
        if 'due_date' in kwargs:
            due = periods.require_date(kwargs['due_date'], "due_date")
            if due < periods.require_date(record.period_start, "period_start"):
                raise ValueError("due_date cannot be earlier than period_start")
            record.due_date = due.isoformat()
        for key in ('taxable_amount', 'tax_amount'):
            if key in kwargs:
                setattr(record, key, ValidationUtils.validate_amount(kwargs[key], key))
        for key in ('reference', 'provider', 'notes', 'paid_date'):
            if key in kwargs:
                setattr(record, key, ValidationUtils.sanitize_string(kwargs[key], key, 1000))
        record.updated_at = _now()
        self._save()
        return record

    def delete_record(self, record_id: str) -> bool:
        record = self.get_record(record_id)
        if not record:
            raise ValueError(f"Tax record not found: {record_id}")
        self._records = [r for r in self.records if r.id != record_id]
        self._save()
        return True

    def mark_status(self, record_id: str, status: str, paid_date: str = None) -> TaxRecord:
        """Move a record to ``declared`` or ``paid``."""
        status = _validate_tax_status(status)
        record = self.get_record(record_id)
        if not record:
            raise ValueError(f"Tax record not found: {record_id}")
        record.status = status
        if status == TaxStatus.PAID.value:
            record.paid_date = periods.to_iso(paid_date) or periods.today().isoformat()
        record.updated_at = _now()
        self._save()
        return record

    def seed_schedule(self, schedule: Dict[str, Any]) -> Dict[str, int]:
        """Create records for every planned period not already tracked.

        The check is re-run against live records rather than trusting the
        ``already_tracked`` flags in ``schedule``, so passing a stale schedule
        (or clicking the button twice) cannot create duplicate obligations.
        """
        existing = {(r.tax_type, r.period_start) for r in self.records}
        created = 0
        skipped = 0
        for period in schedule.get('periods', []):
            key = (period.get('tax_type'), period.get('period_start'))
            if key in existing:
                skipped += 1
                continue
            self.create_record(
                tax_type=period['tax_type'],
                period_start=period['period_start'],
                period_end=period['period_end'],
                due_date=period['due_date'],
                status=TaxStatus.ESTIMATED.value,
                notes='Created from the South African filing schedule',
            )
            existing.add(key)
            created += 1
        return {'created': created, 'skipped': skipped}


class PayrollManager:
    """Tracks South African payroll runs and the deductions on them."""

    def __init__(self, storage: DataStorage = None):
        self.storage = storage or DataStorage()
        self._runs = None

    @property
    def runs(self) -> List[PayrollRun]:
        if self._runs is None:
            self._load()
        return self._runs

    def _load(self):
        self._runs = [PayrollRun.from_dict(r) for r in self.storage.get_payroll_runs()]

    def _save(self):
        self.storage.save_payroll_runs([r.to_dict() for r in self.runs])

    def get_run(self, run_id: str) -> Optional[PayrollRun]:
        return next((r for r in self.runs if r.id == run_id), None)

    @staticmethod
    def net_pay(gross_pay: float, paye: float = 0.0, uif: float = 0.0,
                other_deductions: float = 0.0) -> float:
        """Take-home pay for a run."""
        return _round(gross_pay - paye - uif - other_deductions)

    @staticmethod
    def employer_cost(gross_pay: float, sdl: float = 0.0, employer_uif: float = 0.0,
                      employer_pension: float = 0.0) -> float:
        """Full cost to the employer of a run."""
        return _round(gross_pay + sdl + employer_uif + employer_pension)

    def _validate_period(self, period_start: str, period_end: str) -> Tuple[date, date]:
        return periods.require_range(period_start, period_end, "period_start", "period_end")

    def create_run(self, period_start: str, period_end: str, pay_date: str,
                   gross_pay: float, paye: float = 0.0, uif: float = 0.0,
                   other_deductions: float = 0.0, sdl: float = 0.0,
                   employer_uif: float = 0.0, employer_pension: float = 0.0,
                   employee_count: int = 0, status: str = PayrollStatus.DRAFT.value,
                   notes: str = "") -> PayrollRun:
        """Record a payroll run."""
        start, end = self._validate_period(period_start, period_end)
        paid_on = periods.require_date(pay_date, "pay_date")
        if paid_on < start:
            raise ValueError("pay_date cannot be earlier than period_start")
        if status not in [s.value for s in PayrollStatus]:
            raise ValueError(f"Invalid status: must be one of {', '.join(s.value for s in PayrollStatus)}")

        gross = ValidationUtils.validate_amount(gross_pay, "gross_pay")
        deductions = (ValidationUtils.validate_amount(paye, "paye")
                      + ValidationUtils.validate_amount(uif, "uif")
                      + ValidationUtils.validate_amount(other_deductions, "other_deductions"))
        if deductions > gross:
            raise ValueError(
                f"Deductions ({_round(deductions)}) cannot exceed gross pay ({gross})"
            )

        try:
            headcount = int(employee_count)
        except (TypeError, ValueError):
            raise ValueError("employee_count must be a whole number")
        if headcount < 0:
            raise ValueError("employee_count cannot be negative")

        run = PayrollRun(
            id=ValidationUtils.generate_secure_id(),
            period_start=start.isoformat(),
            period_end=end.isoformat(),
            pay_date=paid_on.isoformat(),
            gross_pay=gross,
            paye=ValidationUtils.validate_amount(paye, "paye"),
            uif=ValidationUtils.validate_amount(uif, "uif"),
            other_deductions=ValidationUtils.validate_amount(other_deductions, "other_deductions"),
            sdl=ValidationUtils.validate_amount(sdl, "sdl"),
            employer_uif=ValidationUtils.validate_amount(employer_uif, "employer_uif"),
            employer_pension=ValidationUtils.validate_amount(employer_pension, "employer_pension"),
            employee_count=headcount,
            status=status,
            notes=ValidationUtils.sanitize_string(notes, "notes", 1000),
        )
        self.runs.append(run)
        self._save()
        logger.info(f"Created payroll run for {run.period_end} ({run.id})")
        return run

    def update_run(self, run_id: str, **kwargs) -> PayrollRun:
        """Update a payroll run, re-checking that deductions fit gross pay."""
        run = self.get_run(run_id)
        if not run:
            raise ValueError(f"Payroll run not found: {run_id}")

        if 'status' in kwargs:
            if kwargs['status'] not in [s.value for s in PayrollStatus]:
                raise ValueError("Invalid payroll status")
            run.status = kwargs['status']
        if 'period_start' in kwargs or 'period_end' in kwargs:
            start, end = self._validate_period(
                kwargs.get('period_start', run.period_start),
                kwargs.get('period_end', run.period_end),
            )
            run.period_start = start.isoformat()
            run.period_end = end.isoformat()
        if 'pay_date' in kwargs:
            run.pay_date = periods.require_date(kwargs['pay_date'], "pay_date").isoformat()
        if 'employee_count' in kwargs:
            try:
                headcount = int(kwargs['employee_count'])
            except (TypeError, ValueError):
                raise ValueError("employee_count must be a whole number")
            if headcount < 0:
                raise ValueError("employee_count cannot be negative")
            run.employee_count = headcount
        for key in ('gross_pay', 'paye', 'uif', 'other_deductions', 'sdl',
                    'employer_uif', 'employer_pension'):
            if key in kwargs:
                setattr(run, key, ValidationUtils.validate_amount(kwargs[key], key))
        if 'notes' in kwargs:
            run.notes = ValidationUtils.sanitize_string(kwargs['notes'], "notes", 1000)

        deductions = _round(run.paye + run.uif + run.other_deductions)
        if deductions > run.gross_pay:
            raise ValueError(
                f"Deductions ({deductions}) cannot exceed gross pay ({run.gross_pay})"
            )
        run.updated_at = _now()
        self._save()
        return run

    def delete_run(self, run_id: str) -> bool:
        run = self.get_run(run_id)
        if not run:
            raise ValueError(f"Payroll run not found: {run_id}")
        self._runs = [r for r in self.runs if r.id != run_id]
        self._save()
        return True

    def list_runs(self, year: int = None) -> List[Dict[str, Any]]:
        """Payroll runs newest first, with net pay and employer cost derived."""
        rows = []
        for run in self.runs:
            if year and not run.period_end.startswith(str(int(year))):
                continue
            rows.append(self._payload(run))
        rows.sort(key=lambda r: (r['pay_date'], r['id']), reverse=True)
        return rows

    @staticmethod
    def _payload(run: PayrollRun) -> Dict[str, Any]:
        payload = run.to_dict()
        payload.update({
            'net_pay': PayrollManager.net_pay(run.gross_pay, run.paye, run.uif, run.other_deductions),
            'employer_cost': PayrollManager.employer_cost(
                run.gross_pay, run.sdl, run.employer_uif, run.employer_pension),
            'total_deductions': _round(run.paye + run.uif + run.other_deductions),
            'period_label': periods.describe_period(run.period_start, run.period_end),
        })
        return payload

    def totals(self, year: int = None) -> Dict[str, Any]:
        """Payroll totals for a calendar year, or all time when omitted."""
        rows = self.list_runs(year)
        return {
            'year': int(year) if year else None,
            'run_count': len(rows),
            'gross_pay': _round(sum(r['gross_pay'] for r in rows)),
            'paye': _round(sum(r['paye'] for r in rows)),
            'uif': _round(sum(r['uif'] for r in rows)),
            'other_deductions': _round(sum(r['other_deductions'] for r in rows)),
            'net_pay': _round(sum(r['net_pay'] for r in rows)),
            'sdl': _round(sum(r['sdl'] for r in rows)),
            'employer_uif': _round(sum(r['employer_uif'] for r in rows)),
            'employer_pension': _round(sum(r['employer_pension'] for r in rows)),
            'employer_cost': _round(sum(r['employer_cost'] for r in rows)),
            'disclaimer': COMPLIANCE_DISCLAIMER,
        }

    def compliance_flags(self, reference: date = None) -> List[Dict[str, str]]:
        """SARS remittance checks: PAYE and UIF are due monthly by the 7th."""
        ref = reference or periods.today()
        flags: List[Dict[str, str]] = []
        for run in self.runs:
            if run.status == PayrollStatus.PAID.value:
                continue
            for amount, label in ((run.paye, 'PAYE'), (run.uif, 'UIF')):
                if amount <= 0:
                    continue
                # Remittance for month M is due in M+1.
                due = periods.add_days(periods.add_months(periods.month_end(run.period_end), 1), 6)
                if ref > due:
                    flags.append({
                        'label': label,
                        'message': f"{label} of R{amount:,.2f} for {run.period_end} is past its expected remittance date of {due.isoformat()}",
                        'severity': 'critical',
                    })
                elif ref >= due - timedelta(days=7):
                    flags.append({
                        'label': label,
                        'message': f"{label} of R{amount:,.2f} for {run.period_end} is due by {due.isoformat()}",
                        'severity': 'warning',
                    })
        return flags


class EntityManager:
    """The business's legal and tax identity, plus a structuring checklist."""

    def __init__(self, storage: DataStorage = None):
        self.storage = storage or DataStorage()
        self._profile = None
        self._saved = False

    @property
    def profile(self) -> EntityProfile:
        """Stored profile, or a blank one for a first-time user."""
        if self._profile is None:
            self._load()
        return self._profile

    def _load(self):
        stored = self.storage.get_entity_profile()
        self._saved = stored is not None
        self._profile = EntityProfile.from_dict(stored) if stored else EntityProfile()

    def _save(self):
        self._profile.updated_at = _now()
        return self.storage.save_entity_profile(self._profile.to_dict())

    @property
    def year_end_month(self) -> int:
        return int(self.profile.financial_year_end_month or periods.DEFAULT_YEAR_END_MONTH)

    @property
    def vat_interval(self) -> str:
        interval = self.profile.vat_interval
        return interval if interval in periods.VAT_INTERVAL_MONTHS else 'monthly'

    def update_profile(self, **kwargs) -> EntityProfile:
        """Update the business profile.

        Unknown fields are rejected rather than ignored, so a caller working
        from a stale field name finds out instead of silently saving nothing.
        """
        editable = {
            'entity_type', 'financial_year_end_month', 'vat_interval',
            'employee_count', 'vat_registered', 'registered_name',
            'trading_name', 'registration_number', 'tax_number', 'vat_number',
            'industry', 'address', 'accountant_name', 'accountant_contact',
            'notes',
        }
        unknown = sorted(set(kwargs) - editable)
        if unknown:
            raise ValueError(
                f"Unknown profile field(s): {', '.join(unknown)}. "
                f"Valid fields: {', '.join(sorted(editable))}"
            )

        profile = self.profile
        if 'entity_type' in kwargs:
            if kwargs['entity_type'] not in [e.value for e in EntityType]:
                raise ValueError(
                    f"Invalid entity type: must be one of {', '.join(e.value for e in EntityType)}"
                )
            profile.entity_type = kwargs['entity_type']
        if 'financial_year_end_month' in kwargs:
            try:
                month = int(kwargs['financial_year_end_month'])
            except (TypeError, ValueError):
                raise ValueError("financial_year_end_month must be a whole number")
            if not 1 <= month <= 12:
                raise ValueError("financial_year_end_month must be between 1 and 12")
            profile.financial_year_end_month = month
        if 'vat_interval' in kwargs:
            if kwargs['vat_interval'] not in periods.VAT_INTERVAL_MONTHS:
                raise ValueError(
                    f"Invalid VAT interval: must be one of {', '.join(periods.VAT_INTERVAL_MONTHS)}"
                )
            profile.vat_interval = kwargs['vat_interval']
        if 'employee_count' in kwargs:
            try:
                headcount = int(kwargs['employee_count'])
            except (TypeError, ValueError):
                raise ValueError("employee_count must be a whole number")
            if headcount < 0:
                raise ValueError("employee_count cannot be negative")
            profile.employee_count = headcount
        if 'vat_registered' in kwargs:
            profile.vat_registered = bool(kwargs['vat_registered'])
        for key in ('registered_name', 'trading_name', 'registration_number', 'tax_number',
                    'vat_number', 'industry', 'address', 'accountant_name',
                    'accountant_contact', 'notes'):
            if key in kwargs:
                setattr(profile, key, ValidationUtils.sanitize_string(kwargs[key], key, 500))

        self._save()
        logger.info("Updated entity profile")
        return profile

    def structuring_checklist(self, account_manager=None) -> List[Dict[str, Any]]:
        """What a lender, auditor or tax practitioner will ask for.

        Each item is a plain yes/no about the user's own records, so a new
        business can see exactly which documents are still missing.
        """
        profile = self.profile

        has_bank_account = False
        if account_manager is not None:
            try:
                has_bank_account = any(
                    a.type in ('checking', 'savings', 'credit') and a.balance != 0
                    for a in account_manager.get_active_accounts()
                )
            except Exception:  # a missing or unreadable account file must not break the checklist
                has_bank_account = False

        return [
            {
                'key': 'registered_name',
                'label': 'Registered legal name recorded',
                'done': bool(profile.registered_name),
                'hint': 'The name on your CIPC registration, not your trading name.',
            },
            {
                'key': 'entity_type',
                'label': 'Business structure chosen and saved',
                'done': self._saved,
                'hint': 'Sole proprietor, partnership, CC, Pty Ltd, trust or NPO.',
            },
            {
                'key': 'registration_number',
                'label': 'CIPC registration number recorded',
                'done': bool(profile.registration_number),
                'hint': 'Required for CCs, Pty Ltds and NPOs.',
            },
            {
                'key': 'tax_number',
                'label': 'SARS income tax number recorded',
                'done': bool(profile.tax_number),
                'hint': 'Issued by SARS once the entity is registered for tax.',
            },
            {
                'key': 'financial_year_end_month',
                'label': 'Financial year end set',
                'done': self._saved,
                'hint': 'February is the South African default; change it if yours differs.',
            },
            {
                'key': 'vat_registration',
                'label': 'VAT registration recorded',
                'done': bool(profile.vat_number) or not profile.vat_registered,
                'hint': 'Only compulsory once taxable supplies pass the VAT threshold.',
            },
            {
                'key': 'bank_account',
                'label': 'A business bank account is tracked',
                'done': has_bank_account,
                'hint': 'Add an account so the cash position reflects real bank money.',
            },
            {
                'key': 'accountant_name',
                'label': 'Accountant or tax practitioner recorded',
                'done': bool(profile.accountant_name),
                'hint': 'Software keeps records; a professional signs off on them.',
            },
        ]


class ForecastManager:
    """Projects cash, income and expenses forward from recent history."""

    def __init__(self, storage: DataStorage = None, transaction_manager=None,
                 account_manager=None):
        self.storage = storage or DataStorage()
        self.transaction_manager = transaction_manager
        self.account_manager = account_manager
        self._scenarios = None

    @property
    def scenarios(self) -> List[ForecastScenario]:
        if self._scenarios is None:
            self._load()
        return self._scenarios

    def _load(self):
        self._scenarios = [ForecastScenario.from_dict(s) for s in self.storage.get_forecasts()]

    def _save(self):
        self.storage.save_forecasts([s.to_dict() for s in self.scenarios])

    def get_scenario(self, scenario_id: str) -> Optional[ForecastScenario]:
        return next((s for s in self.scenarios if s.id == scenario_id), None)

    def create_scenario(self, name: str, projection_months: int = 6,
                        baseline_months: int = 3,
                        income_growth_pct: float = 0.0,
                        expense_growth_pct: float = 0.0,
                        one_off_income: float = 0.0, one_off_expenses: float = 0.0,
                        notes: str = "") -> ForecastScenario:
        """Save a set of projection assumptions."""
        clean = ValidationUtils.sanitize_string(name, "name", 150)
        if not clean:
            raise ValueError("name is required")
        if any(s.name.lower() == clean.lower() for s in self.scenarios):
            raise ValueError(f"Forecast '{clean}' already exists")

        scenario = ForecastScenario(
            id=ValidationUtils.generate_secure_id(),
            name=clean,
            projection_months=_bounded_int(projection_months, "projection_months", 1, 60),
            baseline_months=_bounded_int(baseline_months, "baseline_months", 1, 24),
            income_growth_pct=_bounded_number(income_growth_pct, "income_growth_pct", -100, 500),
            expense_growth_pct=_bounded_number(expense_growth_pct, "expense_growth_pct", -100, 500),
            one_off_income=ValidationUtils.validate_amount(one_off_income, "one_off_income"),
            one_off_expenses=ValidationUtils.validate_amount(one_off_expenses, "one_off_expenses"),
            notes=ValidationUtils.sanitize_string(notes, "notes", 1000),
        )
        self.scenarios.append(scenario)
        self._save()
        return scenario

    def update_scenario(self, scenario_id: str, **kwargs) -> ForecastScenario:
        """Update a saved scenario."""
        scenario = self.get_scenario(scenario_id)
        if not scenario:
            raise ValueError(f"Forecast not found: {scenario_id}")

        if 'name' in kwargs:
            clean = ValidationUtils.sanitize_string(kwargs['name'], "name", 150)
            if not clean:
                raise ValueError("name cannot be empty")
            if any(s.name.lower() == clean.lower() for s in self.scenarios if s.id != scenario_id):
                raise ValueError(f"Forecast '{clean}' already exists")
            scenario.name = clean
        if 'projection_months' in kwargs:
            scenario.projection_months = _bounded_int(kwargs['projection_months'], "projection_months", 1, 60)
        if 'baseline_months' in kwargs:
            scenario.baseline_months = _bounded_int(kwargs['baseline_months'], "baseline_months", 1, 24)
        for key in ('income_growth_pct', 'expense_growth_pct'):
            if key in kwargs:
                setattr(scenario, key, _bounded_number(kwargs[key], key, -100, 500))
        for key in ('one_off_income', 'one_off_expenses'):
            if key in kwargs:
                setattr(scenario, key, ValidationUtils.validate_amount(kwargs[key], key))
        if 'notes' in kwargs:
            scenario.notes = ValidationUtils.sanitize_string(kwargs['notes'], "notes", 1000)
        if 'is_active' in kwargs:
            scenario.is_active = bool(kwargs['is_active'])

        scenario.updated_at = _now()
        self._save()
        return scenario

    def delete_scenario(self, scenario_id: str) -> bool:
        scenario = self.get_scenario(scenario_id)
        if not scenario:
            raise ValueError(f"Forecast not found: {scenario_id}")
        self._scenarios = [s for s in self.scenarios if s.id != scenario_id]
        self._save()
        return True

    def _baseline(self, baseline_months: int, reference: date) -> Dict[str, Any]:
        """Average monthly income and expenses over the trailing window."""
        window_start = periods.month_start(periods.add_months(reference, -(baseline_months - 1)))
        buckets: Dict[str, Dict[str, float]] = {}
        count = 0
        if self.transaction_manager is not None:
            for t in self.transaction_manager.get_transactions_by_date_range(
                    window_start.isoformat(), reference.isoformat()):
                key = periods.month_key(t.date)
                row = buckets.setdefault(key, {'income': 0.0, 'expenses': 0.0})
                count += 1
                if t.type == TransactionType.INCOME.value:
                    row['income'] += t.amount
                elif t.type == TransactionType.EXPENSE.value:
                    row['expenses'] += t.amount

        income = _round(sum(b['income'] for b in buckets.values()) / baseline_months)
        expenses = _round(sum(b['expenses'] for b in buckets.values()) / baseline_months)
        return {
            'window_start': window_start.isoformat(),
            'window_end': reference.isoformat(),
            'baseline_months': baseline_months,
            'avg_monthly_income': income,
            'avg_monthly_expenses': expenses,
            'avg_monthly_profit': _round(income - expenses),
            'months_with_data': len(buckets),
            'transaction_count': count,
        }

    def project(self, scenario: Any = None, reference: date = None,
                overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """Project cash, income and expenses month by month.

        Growth compounds month over month from the trailing average, and the
        one-off amounts land in the first projected month. ``overrides`` lets
        a caller try a figure without saving it as a scenario.
        """
        ref = reference or periods.today()
        if scenario is None:
            if not self.scenarios:
                raise ValueError("Create a forecast scenario first")
            scenario = self.scenarios[0]
        elif isinstance(scenario, str):
            found = self.get_scenario(scenario)
            if not found:
                raise ValueError(f"Forecast not found: {scenario}")
            scenario = found
        elif isinstance(scenario, dict):
            scenario = ForecastScenario.from_dict(scenario)

        settings = scenario.to_dict()
        if overrides:
            for key, value in overrides.items():
                if key in settings and value is not None:
                    settings[key] = value

        projection_months = _bounded_int(settings['projection_months'], "projection_months", 1, 60)
        baseline_months = _bounded_int(settings['baseline_months'], "baseline_months", 1, 24)
        income_growth = _bounded_number(settings['income_growth_pct'], "income_growth_pct", -100, 500) / 100
        expense_growth = _bounded_number(settings['expense_growth_pct'], "expense_growth_pct", -100, 500) / 100
        one_off_income = ValidationUtils.validate_amount(settings.get('one_off_income', 0), "one_off_income")
        one_off_expenses = ValidationUtils.validate_amount(settings.get('one_off_expenses', 0), "one_off_expenses")

        baseline = self._baseline(baseline_months, ref)
        opening_cash = 0.0
        if self.account_manager is not None:
            opening_cash = _round(self.account_manager.get_total_balance()['total'])

        rows: List[Dict[str, Any]] = []
        closing = opening_cash
        lowest = opening_cash
        cumulative = 0.0
        first_profit_month = None
        first_loss_month = None
        break_even_month = None

        for index, month in enumerate(periods.iter_months(periods.add_months(ref, 1), projection_months)):
            income = _round(baseline['avg_monthly_income'] * ((1 + income_growth) ** (index + 1)))
            expenses = _round(baseline['avg_monthly_expenses'] * ((1 + expense_growth) ** (index + 1)))
            if index == 0:
                income = _round(income + one_off_income)
                expenses = _round(expenses + one_off_expenses)
            net = _round(income - expenses)
            closing = _round(closing + net)
            cumulative = _round(cumulative + net)
            lowest = min(lowest, closing)
            if first_profit_month is None and net > 0:
                first_profit_month = month.isoformat()
            if first_loss_month is None and net < 0:
                first_loss_month = month.isoformat()
            # Break-even is the month the projection stops losing money in
            # total, which is the only reading a business owner can act on.
            # A month that merely fails to cover its costs is a loss month.
            if break_even_month is None and cumulative >= 0 and first_loss_month:
                break_even_month = month.isoformat()
            rows.append({
                'month': month.isoformat(),
                'label': f"{periods.MONTH_NAMES[month.month]} {month.year}",
                'income': income,
                'expenses': expenses,
                'net': net,
                'cumulative_net': cumulative,
                'closing_cash': closing,
            })

        total_income = _round(sum(r['income'] for r in rows))
        total_expenses = _round(sum(r['expenses'] for r in rows))
        negative_from = next((r['month'] for r in rows if r['closing_cash'] < 0), None)

        return {
            'scenario': {
                'id': getattr(scenario, 'id', None),
                'name': settings.get('name', 'Untitled'),
                'projection_months': projection_months,
                'baseline_months': baseline_months,
                'income_growth_pct': _round(income_growth * 100, 1),
                'expense_growth_pct': _round(expense_growth * 100, 1),
            },
            'baseline': baseline,
            'opening_cash': opening_cash,
            'months': rows,
            'summary': {
                'total_income': total_income,
                'total_expenses': total_expenses,
                'total_net': _round(total_income - total_expenses),
                'closing_cash': _round(closing),
                'lowest_cash': _round(lowest),
                'average_monthly_profit': _round((total_income - total_expenses) / projection_months),
                'break_even_month': break_even_month,
                'first_profit_month': first_profit_month,
                'first_loss_month': first_loss_month,
                'goes_negative': negative_from is not None,
                'goes_negative_from': negative_from,
                'months_of_cash_left': (len(rows) if negative_from is None
                                        else len([r for r in rows if r['month'] < negative_from])),
                'reading': _forecast_reading(rows, break_even_month, first_loss_month,
                                             negative_from, opening_cash),
            },
            'generated_at': _now(),
            'disclaimer': (
                "A projection from your own averages, not a budget or a forecast "
                "of what will happen. Treat it as a planning range."
            ),
        }


def _bounded_int(value: Any, field_name: str, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a whole number")
    if not low <= number <= high:
        raise ValueError(f"{field_name} must be between {low} and {high}")
    return number


def _bounded_number(value: Any, field_name: str, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a number")
    if not low <= number <= high:
        raise ValueError(f"{field_name} must be between {low} and {high}")
    return _round(number)


def _month_label(iso_month: str) -> str:
    """Turn '2026-03-01' into 'March 2026' for display."""
    parsed = periods.parse_date(iso_month)
    if not parsed:
        return iso_month
    return f"{periods.MONTH_NAMES[parsed.month]} {parsed.year}"


def _forecast_reading(rows: List[Dict[str, Any]], break_even_month, first_loss_month,
                      negative_from, opening_cash: float) -> str:
    """One plain sentence saying what the projection actually shows."""
    if not rows:
        return "No months to project."

    if negative_from:
        return (
            f"Cash runs out in {_month_label(negative_from)}. "
            f"You start with R{opening_cash:,.2f} and need to raise cash or cut "
            "spend before then."
        )

    if first_loss_month and not break_even_month:
        return (
            f"Every month covers its own costs, but {first_loss_month} onwards "
            "runs at a loss. The projection never recovers the shortfall."
        )

    if first_loss_month and break_even_month:
        return (
            f"Back into profit in {_month_label(break_even_month)} after the "
            f"loss starting {_month_label(first_loss_month)}. Cash stays positive "
            "throughout."
        )

    if not first_loss_month:
        final = rows[-1]
        return (
            f"Profitable every month, closing on R{final['closing_cash']:,.2f} "
            f"after {len(rows)} months."
        )

    return "Cash stays positive throughout the projection."
