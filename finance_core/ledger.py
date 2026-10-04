"""Receivables and payables - the "what you're owed" and "what you owe" ledgers.

The transaction ledger alone cannot answer those two questions: a sale on
credit raises neither a bank balance nor a cash movement until the customer
pays. These managers hold the outstanding balances and, critically, write the
matching bank transaction when a payment is recorded, so cash, profit and the
aging report never disagree with each other.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from finance_core.models import (
    Contact, Receivable, Payable, ContactRole, LedgerStatus, TransactionType
)
from finance_core.storage import DataStorage
from finance_core import periods
from utils import ValidationUtils

logger = logging.getLogger(__name__)

#: Overdue-day upper bounds for the aging buckets, in order.
AGING_BUCKETS: Tuple[Tuple[str, Optional[int]], ...] = (
    ('current', 0),
    ('days_1_30', 30),
    ('days_31_60', 60),
    ('days_61_90', 90),
    ('days_90_plus', None),
)

#: Default category used for cash received from a customer.
DEFAULT_RECEIPT_CATEGORY = 'inc_other'
#: Default category used for cash paid to a supplier.
DEFAULT_PAYMENT_CATEGORY = 'exp_other'


def _round(value: float) -> float:
    return round(value, 2)


def aging_bucket(days_overdue: int) -> str:
    """Map a non-negative overdue-day count onto an aging bucket key."""
    for name, upper in AGING_BUCKETS:
        if upper is None or days_overdue <= upper:
            return name
    return AGING_BUCKETS[-1][0]


class ContactManager:
    """Manages the customers and suppliers the business bills."""

    def __init__(self, storage: DataStorage = None):
        self.storage = storage or DataStorage()
        self._contacts = None
        # Ledgers register themselves here once built. They depend on this
        # manager, so the link is made after construction rather than through
        # a circular constructor argument.
        self.ledger_managers: List[Any] = []

    def register_ledger(self, manager) -> None:
        """Attach a receivable or payable manager to this contact book."""
        if manager not in self.ledger_managers:
            self.ledger_managers.append(manager)

    @property
    def contacts(self) -> List[Contact]:
        """All contacts."""
        if self._contacts is None:
            self._load_contacts()
        return self._contacts

    def _load_contacts(self):
        self._contacts = [Contact.from_dict(c) for c in self.storage.get_contacts()]

    def _save_contacts(self):
        self.storage.save_contacts([c.to_dict() for c in self.contacts])

    def get_contact(self, contact_id: str) -> Optional[Contact]:
        return next((c for c in self.contacts if c.id == contact_id), None)

    def get_active_contacts(self) -> List[Contact]:
        return [c for c in self.contacts if c.is_active]

    def search_contacts(self, query: str = '', role: str = None) -> List[Contact]:
        """Filter contacts by free-text query and/or role."""
        needle = (query or '').strip().lower()
        results = []
        for contact in self.contacts:
            if role and contact.role != role and contact.role != ContactRole.BOTH.value:
                continue
            if not needle:
                results.append(contact)
                continue
            haystack = ' '.join([
                contact.name, contact.contact_person, contact.email,
                contact.phone, contact.tax_number, contact.notes,
            ]).lower()
            if needle in haystack:
                results.append(contact)
        return results

    def create_contact(self, name: str, role: str = ContactRole.CUSTOMER.value,
                       contact_person: str = "", email: str = "",
                       phone: str = "", tax_number: str = "",
                       notes: str = "") -> Contact:
        """Create a customer or supplier."""
        clean_name = ValidationUtils.sanitize_string(name, "name", 150)
        if not clean_name:
            raise ValueError("name is required")
        role = _validate_role(role)
        email = ValidationUtils.sanitize_string(email, "email", 150)

        if any(c.name.lower() == clean_name.lower() for c in self.contacts):
            raise ValueError(f"Contact '{clean_name}' already exists")

        contact = Contact(
            id=ValidationUtils.generate_secure_id(),
            name=clean_name,
            role=role,
            contact_person=ValidationUtils.sanitize_string(contact_person, "contact_person", 150),
            email=email,
            phone=ValidationUtils.sanitize_string(phone, "phone", 40),
            tax_number=ValidationUtils.sanitize_string(tax_number, "tax_number", 40),
            notes=ValidationUtils.sanitize_string(notes, "notes", 1000),
        )
        self.contacts.append(contact)
        self._save_contacts()
        logger.info(f"Created contact: {contact.name} ({contact.id})")
        return contact

    def update_contact(self, contact_id: str, **kwargs) -> Contact:
        """Update contact details."""
        contact = self.get_contact(contact_id)
        if not contact:
            raise ValueError(f"Contact not found: {contact_id}")

        for key, value in kwargs.items():
            if not hasattr(contact, key) or key in ('id', 'created_at'):
                continue
            if key == 'name':
                value = ValidationUtils.sanitize_string(value, "name", 150)
                if not value:
                    raise ValueError("name cannot be empty")
            elif key == 'role':
                value = _validate_role(value)
            elif key in ('contact_person', 'email', 'phone', 'tax_number'):
                value = ValidationUtils.sanitize_string(value, key, 150)
            elif key == 'notes':
                value = ValidationUtils.sanitize_string(value, key, 1000)
            setattr(contact, key, value)

        contact.updated_at = _now()
        self._save_contacts()
        return contact

    def delete_contact(self, contact_id: str) -> bool:
        """Delete a contact that has no ledger entries.

        Refusing to orphan a receivable or payable keeps the aging report
        honest, so callers must settle or reassign the entries first.
        """
        contact = self.get_contact(contact_id)
        if not contact:
            raise ValueError(f"Contact not found: {contact_id}")

        # A ledger entry pointing at a deleted contact would lose its name and
        # become unfollowable, so refuse unless every entry is closed out.
        blocking = self.ledger_entries_for_contact(contact_id, outstanding_only=True)
        if blocking:
            raise ValueError(
                f"{contact.name} still has {len(blocking)} open ledger "
                f"entries totalling {sum(e['outstanding'] for e in blocking):.2f}. "
                "Settle, write off or reassign them before deleting this contact."
            )

        settled = self.ledger_entries_for_contact(contact_id, outstanding_only=False)
        if settled:
            raise ValueError(
                f"{contact.name} has {len(settled)} ledger entries. Deleting the "
                "contact would break the history on those records; deactivate "
                "the contact instead."
            )

        self._contacts = [c for c in self.contacts if c.id != contact_id]
        self._save_contacts()
        logger.info(f"Deleted contact: {contact.name}")
        return True

    def ledger_entries_for_contact(self, contact_id: str,
                                   outstanding_only: bool = False) -> List[Dict[str, Any]]:
        """Ledger rows belonging to a contact, from any linked ledger.

        Lets the rest of the app ask "what does this person still owe me, or
        owe you" without knowing which ledgers are attached.
        """
        rows: List[Dict[str, Any]] = []
        for manager in self.ledger_managers:
            if manager is None:
                continue
            for row in manager.list_entries(reference=periods.today()):
                if row.get('contact_id') != contact_id:
                    continue
                if outstanding_only and row.get('status') == LedgerStatus.PAID.value:
                    continue
                rows.append(row)
        return rows

    def get_contact_summary(self, receivables: List[Any] = None,
                            payables: List[Any] = None) -> Dict[str, Dict[str, float]]:
        """Owed-to-us and owed-by-us totals per contact."""
        summary: Dict[str, Dict[str, float]] = {}
        for contact in self.contacts:
            summary[contact.id] = {
                'name': contact.name,
                'role': contact.role,
                'receivable': 0.0,
                'payable': 0.0,
                'net': 0.0,
            }
        for key, entries in (('receivable', receivables or []), ('payable', payables or [])):
            for entry in entries:
                row = summary.get(entry.contact_id)
                if row is None:
                    continue
                row[key] = _round(row[key] + _outstanding(entry))
        for row in summary.values():
            row['net'] = _round(row['receivable'] - row['payable'])
        return summary


def _validate_role(role: str) -> str:
    valid = [r.value for r in ContactRole]
    if role not in valid:
        raise ValueError(f"Invalid role: must be one of {', '.join(valid)}")
    return role


def _now() -> str:
    return datetime.now().isoformat()


def _outstanding(entry) -> float:
    """Amount still owed on a receivable or payable."""
    if entry.status == LedgerStatus.WRITTEN_OFF.value:
        return 0.0
    return _round(max(0.0, entry.amount - entry.amount_paid))


def _due_on(entry) -> Optional[date]:
    """Parse an entry's stored ISO due date, tolerating a missing value."""
    return periods.parse_date(entry.due_date, "due_date") if entry.due_date else None


def _days_overdue(entry, reference: date) -> int:
    """Days past the due date, never negative."""
    due = _due_on(entry)
    if due is None or reference <= due:
        return 0
    return (reference - due).days


def derive_status(entry, reference: date = None) -> str:
    """Work out the effective status of a ledger entry.

    ``written_off`` is the only status a person sets by hand; everything else
    follows from the amounts paid and the due date, so the stored value can
    never drift away from the underlying money.
    """
    if entry.status == LedgerStatus.WRITTEN_OFF.value:
        return LedgerStatus.WRITTEN_OFF.value
    paid = _round(entry.amount_paid)
    total = _round(entry.amount)
    if total <= 0 or paid >= total:
        return LedgerStatus.PAID.value
    if paid > 0:
        return LedgerStatus.PARTIAL.value
    if _days_overdue(entry, reference or periods.today()) > 0:
        return LedgerStatus.OVERDUE.value
    return LedgerStatus.OPEN.value


def _status_payload(entry, contact: Optional[Contact],
                    reference: date = None) -> Dict[str, Any]:
    """Decorate a ledger entry with its computed status and aging."""
    ref = reference or periods.today()
    outstanding = _outstanding(entry)
    days = _days_overdue(entry, ref) if outstanding > 0 else 0

    payload = entry.to_dict()
    payload.update({
        'status': derive_status(entry, ref),
        'outstanding': outstanding,
        'days_overdue': days,
        'aging_bucket': aging_bucket(days) if outstanding > 0 else 'settled',
        'contact_name': contact.name if contact else 'Unknown contact',
        'contact_role': contact.role if contact else '',
    })
    return payload


class _LedgerManager:
    """Shared behaviour for the receivable and payable ledgers.

    Subclasses supply the model, the storage accessors and the transaction
    type that settles an entry.
    """

    model = Receivable
    #: Transaction type written to the bank ledger when the entry is settled.
    settle_transaction_type = TransactionType.INCOME.value
    default_category_id = DEFAULT_RECEIPT_CATEGORY

    def __init__(self, storage: DataStorage = None, contact_manager: ContactManager = None,
                 transaction_manager=None):
        self.storage = storage or DataStorage()
        self.contact_manager = contact_manager or ContactManager(self.storage)
        self.transaction_manager = transaction_manager
        self._items = None
        self.contact_manager.register_ledger(self)

    # -- storage -----------------------------------------------------------
    def _load(self, records: List[Dict]) -> None:
        self._items = [self.model.from_dict(r) for r in records]

    def _save(self) -> None:
        self._save_all([item.to_dict() for item in self.items])

    # -- reads -------------------------------------------------------------
    @property
    def items(self):
        if self._items is None:
            self._load(self._read_all())
        return self._items

    def get_entry(self, entry_id: str):
        return next((i for i in self.items if i.id == entry_id), None)

    def get_entries_for_contact(self, contact_id: str) -> List[Any]:
        return [i for i in self.items if i.contact_id == contact_id]

    def open_entries(self, reference: date = None) -> List[Any]:
        """Entries with money still outstanding."""
        ref = reference or periods.today()
        return [i for i in self.items if _outstanding(i) > 0 and derive_status(i, ref) != LedgerStatus.WRITTEN_OFF.value]

    def overdue_entries(self, reference: date = None) -> List[Any]:
        ref = reference or periods.today()
        return [i for i in self.items if derive_status(i, ref) == LedgerStatus.OVERDUE.value]

    def list_entries(self, reference: date = None, contact_id: str = None,
                     status: str = None) -> List[Dict[str, Any]]:
        """All entries, newest issue date first, with computed status."""
        ref = reference or periods.today()
        rows = []
        for entry in self.items:
            if contact_id and entry.contact_id != contact_id:
                continue
            effective = derive_status(entry, ref)
            if status and effective != status:
                continue
            rows.append(_status_payload(entry, self.contact_manager.get_contact(entry.contact_id), ref))
        rows.sort(key=lambda r: (r['issue_date'], r['id']), reverse=True)
        return rows

    def totals(self, reference: date = None) -> Dict[str, float]:
        """Total billed, settled and outstanding, plus the overdue portion."""
        ref = reference or periods.today()
        billed = _round(sum(i.amount for i in self.items))
        settled = _round(sum(i.amount_paid for i in self.items))
        open_rows = [i for i in self.open_entries(ref)]
        outstanding = _round(sum(_outstanding(i) for i in open_rows))
        overdue = _round(sum(_outstanding(i) for i in open_rows if derive_status(i, ref) == LedgerStatus.OVERDUE.value))
        return {
            'billed': billed,
            'settled': settled,
            'outstanding': outstanding,
            'overdue': overdue,
            'entry_count': len(self.items),
            'open_count': len(open_rows),
        }

    def aging(self, reference: date = None) -> Dict[str, Any]:
        """Outstanding balance split into aging buckets."""
        ref = reference or periods.today()
        buckets = {name: 0.0 for name, _ in AGING_BUCKETS}
        counts = {name: 0 for name, _ in AGING_BUCKETS}
        for entry in self.open_entries(ref):
            days = _days_overdue(entry, ref)
            name = aging_bucket(days)
            buckets[name] = _round(buckets[name] + _outstanding(entry))
            counts[name] += 1
        total = _round(sum(buckets.values()))
        return {
            'buckets': [
                {
                    'bucket': name,
                    'amount': buckets[name],
                    'count': counts[name],
                    'share_pct': round((buckets[name] / total * 100) if total else 0.0, 1),
                }
                for name, _ in AGING_BUCKETS
            ],
            'total': total,
            'as_at': ref.isoformat(),
        }

    def reconcile_statuses(self, reference: date = None) -> int:
        """Persist statuses derived from payments and due dates.

        Returns the number of entries whose stored status changed.
        """
        ref = reference or periods.today()
        changed = 0
        for entry in self.items:
            effective = derive_status(entry, ref)
            if entry.status != effective:
                entry.status = effective
                entry.updated_at = _now()
                changed += 1
        if changed:
            self._save()
        return changed

    def total_for_contact(self, contact_id: str, reference: date = None) -> float:
        return _round(sum(_outstanding(i) for i in self.get_entries_for_contact(contact_id)))

    # -- writes ------------------------------------------------------------
    def _validate_common(self, contact_id: str, amount, issue_date, due_date,
                         account_id: str, terms_days) -> Tuple[float, str, Optional[str], int]:
        contact = self.contact_manager.get_contact(contact_id)
        if not contact:
            raise ValueError(f"Contact not found: {contact_id}")
        if not contact.is_active:
            raise ValueError(f"Contact '{contact.name}' is inactive")

        amount_value = ValidationUtils.validate_amount(amount, "amount")
        if amount_value <= 0:
            raise ValueError("amount must be greater than zero")

        issue = periods.require_date(issue_date, "issue_date")
        due = periods.parse_date(due_date, "due_date") if due_date else None
        if due and due < issue:
            raise ValueError("due_date cannot be earlier than issue_date")

        try:
            terms = int(terms_days if terms_days is not None else 30)
        except (TypeError, ValueError):
            raise ValueError("terms_days must be a whole number")
        if terms < 0 or terms > 365:
            raise ValueError("terms_days must be between 0 and 365")

        if due is None:
            due = periods.add_days(issue, terms)
        return amount_value, issue.isoformat(), due.isoformat(), terms

    def record_payment(self, entry_id: str, amount, date_str: str = None,
                       account_id: str = None, category_id: str = None,
                       reference: str = "", create_transaction: bool = True) -> Dict[str, Any]:
        """Settle some or all of an entry and post the matching cash movement.

        ``create_transaction`` writes a bank transaction so account balances
        and the cash flow statement reflect the payment. It is kept optional
        for back-dated bookkeeping, where the bank line may already be
        recorded separately.
        """
        entry = self.get_entry(entry_id)
        if not entry:
            raise ValueError(f"Entry not found: {entry_id}")
        if entry.status == LedgerStatus.WRITTEN_OFF.value:
            raise ValueError("Cannot record a payment against a written-off entry")

        payment = ValidationUtils.validate_amount(amount, "payment")
        if payment <= 0:
            raise ValueError("payment must be greater than zero")

        remaining = _outstanding(entry)
        if _round(entry.amount_paid + payment) > _round(entry.amount) + 0.005:
            raise ValueError(
                f"Payment of {payment:.2f} exceeds the outstanding "
                f"{remaining:.2f} on this entry"
            )

        paid_on = periods.require_date(date_str, "date") if date_str else periods.today()
        if paid_on < periods.require_date(entry.issue_date, "issue_date"):
            raise ValueError("Payment date cannot be earlier than the issue date")

        # Resolve the target account up front: a settlement without a matching
        # cash movement would make the ledger and the bank disagree, so a
        # missing or unknown account must fail before anything is written.
        target_account = account_id or entry.account_id
        if create_transaction and self.transaction_manager is not None:
            if not target_account:
                raise ValueError(
                    "An account is required to post the settlement transaction; "
                    "pass create_transaction=False to skip it"
                )
            if not self.transaction_manager.account_manager.get_account(target_account):
                raise ValueError(f"Account not found: {target_account}")

        # Stage the change in memory, post the cash movement, then persist.
        # If posting raises, nothing has been saved and the entry is unchanged.
        previous_paid = entry.amount_paid
        previous_status = entry.status
        entry.amount_paid = _round(entry.amount_paid + payment)
        entry.status = derive_status(entry, paid_on)
        entry.updated_at = _now()

        transaction = None
        try:
            if create_transaction and self.transaction_manager is not None:
                transaction = self._post_settlement_transaction(
                    entry, payment, paid_on, target_account, category_id, reference
                )
        except Exception:
            entry.amount_paid = previous_paid
            entry.status = previous_status
            entry.updated_at = _now()
            raise

        self._save()

        logger.info(
            f"Recorded {self.settle_transaction_type} payment {payment:.2f} on entry {entry.id}"
        )
        return {
            'entry': _status_payload(entry, self.contact_manager.get_contact(entry.contact_id)),
            'payment': payment,
            'settled': entry.status == LedgerStatus.PAID.value,
            'transaction': transaction.to_dict() if transaction else None,
        }

    def _post_settlement_transaction(self, entry, payment: float, paid_on: date,
                                     account_id: str, category_id: str, reference: str):
        """Write the cash movement that settles an entry."""
        target_account = account_id or entry.account_id
        if not target_account:
            raise ValueError(
                "An account is required to post the settlement transaction; "
                "pass create_transaction=False to skip it"
            )
        if not self.transaction_manager.account_manager.get_account(target_account):
            raise ValueError(f"Account not found: {target_account}")

        contact = self.contact_manager.get_contact(entry.contact_id)
        who = contact.name if contact else 'unknown contact'
        direction = 'from' if self.settle_transaction_type == TransactionType.INCOME.value else 'to'
        parts = [p for p in (entry.description, f"({reference})" if reference else "") if p]
        description = f"Payment {direction} {who}"
        if parts:
            description = f"{description} {' '.join(parts)}"

        return self.transaction_manager.create_transaction(
            account_id=target_account,
            type_str=self.settle_transaction_type,
            amount=payment,
            category_id=category_id or getattr(entry, 'category_id', None) or self.default_category_id,
            description=description,
            date_str=paid_on.isoformat(),
            payee=who if self.settle_transaction_type == TransactionType.EXPENSE.value else '',
            notes=f'Settles {self.model.__name__.lower()} {entry.id}',
            tags=['settlement', self.model.__name__.lower()],
        )

    def write_off(self, entry_id: str, reason: str = "") -> Dict[str, Any]:
        """Write an entry off so it stops counting as money owed."""
        entry = self.get_entry(entry_id)
        if not entry:
            raise ValueError(f"Entry not found: {entry_id}")
        if entry.status == LedgerStatus.WRITTEN_OFF.value:
            raise ValueError("Entry is already written off")

        written_off = _outstanding(entry)
        entry.status = LedgerStatus.WRITTEN_OFF.value
        note = ValidationUtils.sanitize_string(reason, "reason", 500)
        stamp = f"Written off {periods.today().isoformat()}"
        entry.notes = f"{entry.notes}; {stamp}: {note}".strip('; ') if note else \
                      f"{entry.notes}; {stamp}".strip('; ')
        entry.updated_at = _now()
        self._save()
        return {
            'entry': _status_payload(entry, self.contact_manager.get_contact(entry.contact_id)),
            'written_off': written_off,
        }

    def _build_entry(self, **kwargs):
        return self.model(
            id=ValidationUtils.generate_secure_id(),
            **kwargs
        )

    def _update_entry(self, entry, kwargs: Dict[str, Any], allow_amount: bool,
                      allow_contact: bool):
        """Apply validated edits to a ledger entry.

        Shares one implementation between receivables and payables so the two
        ledgers cannot drift apart on validation rules. Every field is checked
        before anything is written, so a rejected edit cannot leave a
        half-applied change in memory for a later save to persist.
        """
        staged: Dict[str, Any] = {}

        if 'contact_id' in kwargs and kwargs['contact_id'] != entry.contact_id:
            if not allow_contact:
                raise ValueError("contact_id cannot be changed")
            if not self.contact_manager.get_contact(kwargs['contact_id']):
                raise ValueError(f"Contact not found: {kwargs['contact_id']}")
            staged['contact_id'] = kwargs['contact_id']

        if allow_amount and 'amount' in kwargs:
            new_amount = ValidationUtils.validate_amount(kwargs['amount'], "amount")
            if new_amount <= 0:
                raise ValueError("amount must be greater than zero")
            if _round(new_amount) < _round(entry.amount_paid):
                raise ValueError(
                    f"amount cannot be less than the {entry.amount_paid:.2f} already paid"
                )
            staged['amount'] = new_amount

        if 'issue_date' in kwargs or 'due_date' in kwargs:
            issue = periods.require_date(kwargs.get('issue_date', entry.issue_date), "issue_date")
            due_raw = kwargs.get('due_date', entry.due_date)
            due = periods.require_date(due_raw, "due_date") if due_raw else None
            if due and due < issue:
                raise ValueError("due_date cannot be earlier than issue_date")
            staged['issue_date'] = issue.isoformat()
            staged['due_date'] = due.isoformat() if due else None

        for key in ('description', 'reference', 'account_id', 'category_id', 'notes'):
            if key in kwargs:
                staged[key] = ValidationUtils.sanitize_string(kwargs[key], key, 500)

        for key, value in staged.items():
            setattr(entry, key, value)

        entry.status = derive_status(entry)
        entry.updated_at = _now()
        self._save()
        return entry


class ReceivableManager(_LedgerManager):
    """Money customers owe the business."""

    model = Receivable
    settle_transaction_type = TransactionType.INCOME.value
    default_category_id = DEFAULT_RECEIPT_CATEGORY

    def _read_all(self) -> List[Dict]:
        return self.storage.get_receivables()

    def _save_all(self, rows: List[Dict]) -> bool:
        return self.storage.save_receivables(rows)

    def create_receivable(self, contact_id: str, amount, issue_date: str = None,
                          due_date: str = None, account_id: str = "",
                          description: str = "", reference: str = "",
                          terms_days: int = 30) -> Receivable:
        """Bill a customer for goods or services not yet paid."""
        amount_value, issue_iso, due_iso, terms = self._validate_common(
            contact_id, amount, issue_date or periods.today().isoformat(),
            due_date, account_id, terms_days
        )
        entry = self._build_entry(
            contact_id=contact_id,
            amount=amount_value,
            issue_date=issue_iso,
            due_date=due_iso,
            account_id=ValidationUtils.sanitize_string(account_id, "account_id"),
            description=ValidationUtils.sanitize_string(description, "description", 500),
            reference=ValidationUtils.sanitize_string(reference, "reference", 100),
            terms_days=terms,
        )
        self.items.append(entry)
        self._save()
        logger.info(f"Created receivable of {amount_value:.2f} ({entry.id})")
        return entry

    def update_receivable(self, receivable_id: str, **kwargs) -> Receivable:
        """Update a receivable, keeping paid and total amounts consistent."""
        entry = self.get_entry(receivable_id)
        if not entry:
            raise ValueError(f"Receivable not found: {receivable_id}")
        return self._update_entry(entry, kwargs, allow_amount=True, allow_contact=True)

    def delete_receivable(self, receivable_id: str) -> bool:
        entry = self.get_entry(receivable_id)
        if not entry:
            raise ValueError(f"Receivable not found: {receivable_id}")
        if _round(entry.amount_paid) > 0:
            raise ValueError(
                "Cannot delete a receivable with payments recorded; write it off instead"
            )
        self._items = [i for i in self.items if i.id != receivable_id]
        self._save()
        return True

    def record_payment(self, entry_id: str, amount, date_str: str = None,
                       account_id: str = None, category_id: str = None,
                       reference: str = "", create_transaction: bool = True) -> Dict[str, Any]:
        """Record cash received from a customer."""
        return super().record_payment(
            entry_id, amount, date_str, account_id, category_id, reference, create_transaction
        )


class PayableManager(_LedgerManager):
    """Money the business owes its suppliers."""

    model = Payable
    settle_transaction_type = TransactionType.EXPENSE.value
    default_category_id = DEFAULT_PAYMENT_CATEGORY

    def _read_all(self) -> List[Dict]:
        return self.storage.get_payables()

    def _save_all(self, rows: List[Dict]) -> bool:
        return self.storage.save_payables(rows)

    def create_payable(self, contact_id: str, amount, issue_date: str = None,
                       due_date: str = None, account_id: str = "",
                       description: str = "", reference: str = "",
                       category_id: str = "", terms_days: int = 30) -> Payable:
        """Record a supplier bill the business has not yet paid."""
        amount_value, issue_iso, due_iso, terms = self._validate_common(
            contact_id, amount, issue_date or periods.today().isoformat(),
            due_date, account_id, terms_days
        )
        entry = self._build_entry(
            contact_id=contact_id,
            amount=amount_value,
            issue_date=issue_iso,
            due_date=due_iso,
            account_id=ValidationUtils.sanitize_string(account_id, "account_id"),
            description=ValidationUtils.sanitize_string(description, "description", 500),
            reference=ValidationUtils.sanitize_string(reference, "reference", 100),
            category_id=ValidationUtils.sanitize_string(category_id, "category_id"),
            terms_days=terms,
        )
        self.items.append(entry)
        self._save()
        logger.info(f"Created payable of {amount_value:.2f} ({entry.id})")
        return entry

    def update_payable(self, payable_id: str, **kwargs) -> Payable:
        """Update a payable, keeping paid and total amounts consistent."""
        entry = self.get_entry(payable_id)
        if not entry:
            raise ValueError(f"Payable not found: {payable_id}")
        return self._update_entry(entry, kwargs, allow_amount=True, allow_contact=True)

    def delete_payable(self, payable_id: str) -> bool:
        entry = self.get_entry(payable_id)
        if not entry:
            raise ValueError(f"Payable not found: {payable_id}")
        if _round(entry.amount_paid) > 0:
            raise ValueError(
                "Cannot delete a payable with payments recorded; write it off instead"
            )
        self._items = [i for i in self.items if i.id != payable_id]
        self._save()
        return True

    def record_payment(self, entry_id: str, amount, date_str: str = None,
                       account_id: str = None, category_id: str = None,
                       reference: str = "", create_transaction: bool = True) -> Dict[str, Any]:
        """Record cash paid to a supplier."""
        return super().record_payment(
            entry_id, amount, date_str, account_id, category_id, reference, create_transaction
        )
