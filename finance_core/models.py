import uuid
from copy import deepcopy
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Mapping, Union, get_args, get_origin
from dataclasses import dataclass, field, fields as _fields, MISSING
from enum import Enum as PyEnum, Enum

class FinanceError(Exception):
    """Base exception for finance module errors."""
    def __init__(self, message: str, code: str = "FINANCE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class ValidationError(FinanceError):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: str = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field

class AuthenticationError(FinanceError):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR")

class AuthorizationError(FinanceError):
    """Raised when authorization fails."""
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, "AUTHZ_ERROR")

class NotFoundError(FinanceError):
    """Raised when a resource is not found."""
    def __init__(self, resource: str, identifier: str):
        super().__init__(f"{resource} not found: {identifier}", "NOT_FOUND")
        self.resource = resource
        self.identifier = identifier

class TransactionType(Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"

class CategoryType(Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"

class AccountType(Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT = "credit"
    CASH = "cash"
    INVESTMENT = "investment"
    LOAN = "loan"
    OTHER = "other"

class BudgetPeriod(Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class AlertType(Enum):
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    LOW_BALANCE = "low_balance"
    LARGE_TRANSACTION = "large_transaction"
    RECURRING_PATTERN = "recurring_pattern"
    RECEIVABLE_OVERDUE = "receivable_overdue"
    PAYABLE_OVERDUE = "payable_overdue"
    TAX_DUE = "tax_due"
    PROFIT_WARNING = "profit_warning"


class ContactRole(Enum):
    """Whether a contact owes us money, we owe them, or both."""
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    BOTH = "both"


class LedgerStatus(Enum):
    """Lifecycle of a receivable or payable."""
    OPEN = "open"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    WRITTEN_OFF = "written_off"


class TaxType(Enum):
    """South African tax types tracked by the compliance module."""
    VAT = "vat"
    PROVISIONAL_TAX = "provisional_tax"
    INCOME_TAX = "income_tax"
    PAYE = "paye"
    UIF = "uif"
    SDL = "sdl"
    DIVIDENDS_TAX = "dividends_tax"
    TURNOVER_TAX = "turnover_tax"
    EMPLOYEES_TAX = "employees_tax"
    OTHER = "other"


class TaxStatus(Enum):
    ESTIMATED = "estimated"
    DECLARED = "declared"
    PAID = "paid"
    OVERDUE = "overdue"
    NOT_APPLICABLE = "not_applicable"


class PayrollStatus(Enum):
    DRAFT = "draft"
    PROCESSED = "processed"
    PAID = "paid"


class EntityType(Enum):
    """South African business structures."""
    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    PARTNERSHIP = "partnership"
    CLOSE_CORPORATION = "close_corporation"
    PRIVATE_COMPANY = "private_company"
    TRUST = "trust"
    NON_PROFIT = "non_profit"
    OTHER = "other"

def _coerce_value(tp: Any, value: Any) -> Any:
    """Coerce a raw JSON value to the declared field type.

    Raises ``ValueError``/``TypeError`` when the value cannot be converted.
    ``None`` is allowed only for ``Optional[...]`` types.
    """
    if value is None:
        origin = get_origin(tp)
        args = get_args(tp)
        if origin is Union and type(None) in args:
            return None
        raise TypeError(f"expected a value, got null")

    origin = get_origin(tp)
    args = get_args(tp)
    if origin is Union:
        real = [a for a in args if a is not type(None)]
        if len(real) == 1:
            return _coerce_value(real[0], value)
        return value

    if isinstance(tp, type) and issubclass(tp, PyEnum):
        if isinstance(value, tp):
            return value
        if isinstance(value, str):
            return tp[value]
        return tp(value)

    if tp is bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            low = value.strip().lower()
            if low in ("true", "1", "yes", "on"):
                return True
            if low in ("false", "0", "no", "off"):
                return False
            raise ValueError(f"cannot interpret {value!r} as boolean")
        raise TypeError(f"cannot interpret {value!r} as boolean")

    if tp is float:
        if isinstance(value, bool):
            raise TypeError(f"cannot interpret {value!r} as float")
        return float(value)

    if tp is int:
        if isinstance(value, bool):
            raise TypeError(f"cannot interpret {value!r} as int")
        return int(value)

    if tp is str:
        return str(value)

    if tp is list or tp is dict:
        if isinstance(value, (list, tuple)) if tp is list else isinstance(value, dict):
            return value
        raise TypeError(f"expected {tp.__name__}, got {type(value).__name__}")

    return value

class SerializableMixin:
    """Robust JSON (de)serialization for dataclass models.

    ``to_dict`` is a pure read of the declared fields (no side effects).
    ``from_dict`` tolerates extra keys, drops ``None`` overrides and coerces
    values to the declared field types, raising ``ValidationError`` with a
    field name when required fields are missing or values are unusable.
    """

    @classmethod
    def _schema(cls) -> Dict[str, Any]:
        return {f.name: f.type for f in _fields(cls)}  # type: ignore[arg-type]

    def to_dict(self) -> Dict[str, Any]:
        return {f.name: deepcopy(getattr(self, f.name)) for f in _fields(self)}  # type: ignore[arg-type]

    @classmethod
    def from_dict(cls, data: Optional[Mapping[str, Any]]) -> 'SerializableMixin':
        schema = cls._schema()
        kwargs: Dict[str, Any] = {}
        if data:
            for name, value in data.items():
                if name not in schema:
                    continue  # tolerate unknown keys from older/foreign data
                try:
                    kwargs[name] = _coerce_value(schema[name], value)
                except (ValueError, TypeError) as exc:
                    raise ValidationError(f"invalid value for {name}: {value!r} ({exc})", name)
        for f in _fields(cls):  # type: ignore[arg-type]
            if f.name not in kwargs and f.default is MISSING and f.default_factory is MISSING:
                raise ValidationError(f"missing required field: {f.name}", f.name)
        return cls(**kwargs)

@dataclass
class Category(SerializableMixin):
    """Represents a transaction category."""
    id: str
    name: str
    type: str  # 'income', 'expense', 'transfer'
    icon: str = "tag"
    color: str = "#007a55"
    parent_id: Optional[str] = None
    is_system: bool = False
    is_active: bool = True
    

@dataclass
class Account(SerializableMixin):
    """Represents a financial account."""
    id: str
    name: str
    type: str
    balance: float = 0.0
    currency: str = "ZAR"
    institution: str = ""
    account_number: str = ""
    notes: str = ""
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    

@dataclass
class Transaction(SerializableMixin):
    """Represents a financial transaction."""
    id: str
    account_id: str
    type: str
    amount: float
    category_id: str
    description: str
    date: str  # ISO format
    payee: str = ""
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    is_recurring: bool = False
    recurring_frequency: Optional[str] = None  # 'daily', 'weekly', 'monthly', 'yearly'
    destination_account_id: Optional[str] = None  # For transfers
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    

@dataclass
class Budget(SerializableMixin):
    """Represents a budget allocation."""
    id: str
    name: str
    category_id: str
    amount: float
    spent: float = 0.0
    period: str = "monthly"
    start_date: str = field(default_factory=lambda: date.today().isoformat())
    end_date: Optional[str] = None
    is_active: bool = True
    alert_threshold: float = 80.0  # Alert at 80% spent
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    

@dataclass
class Alert(SerializableMixin):
    """Represents a financial alert."""
    id: str
    type: str
    message: str
    severity: str  # 'info', 'warning', 'critical'
    is_read: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    data: Dict = field(default_factory=dict)


@dataclass
class Contact(SerializableMixin):
    """A client or supplier the business transacts with."""
    id: str
    name: str
    role: str = "customer"  # 'customer', 'supplier', 'both'
    contact_person: str = ""
    email: str = ""
    phone: str = ""
    tax_number: str = ""
    notes: str = ""
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Receivable(SerializableMixin):
    """Money a customer owes the business ('what you're owed')."""
    id: str
    contact_id: str
    amount: float
    issue_date: str
    account_id: str = ""
    due_date: Optional[str] = None
    amount_paid: float = 0.0
    description: str = ""
    reference: str = ""  # e.g. linked invoice number
    terms_days: int = 30
    status: str = "open"  # open, partial, paid, overdue, written_off
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Payable(SerializableMixin):
    """Money the business owes a supplier ('what you owe')."""
    id: str
    contact_id: str
    amount: float
    issue_date: str
    account_id: str = ""
    due_date: Optional[str] = None
    amount_paid: float = 0.0
    description: str = ""
    reference: str = ""  # e.g. supplier statement number
    category_id: str = ""
    terms_days: int = 30
    status: str = "open"  # open, partial, paid, overdue, written_off
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaxRecord(SerializableMixin):
    """A single tax obligation or estimate for a period."""
    id: str
    tax_type: str
    period_start: str
    period_end: str
    due_date: str
    taxable_amount: float = 0.0
    tax_amount: float = 0.0
    status: str = "estimated"  # estimated, declared, paid, overdue, not_applicable
    reference: str = ""
    provider: str = ""  # responsible accountant / tax practitioner
    notes: str = ""
    paid_date: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PayrollRun(SerializableMixin):
    """A South African payroll run, including PAYE/UIF/SDL."""
    id: str
    period_start: str
    period_end: str
    pay_date: str
    gross_pay: float = 0.0
    paye: float = 0.0
    uif: float = 0.0
    other_deductions: float = 0.0
    sdl: float = 0.0
    employer_uif: float = 0.0
    employer_pension: float = 0.0
    employee_count: int = 0
    status: str = "draft"  # draft, processed, paid
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class EntityProfile(SerializableMixin):
    """The business's legal and tax identity (one per user)."""
    registered_name: str = ""
    trading_name: str = ""
    entity_type: str = "sole_proprietorship"
    registration_number: str = ""
    tax_number: str = ""
    vat_number: str = ""
    financial_year_end_month: int = 2  # 1-12; 2 = February (SA SARS year)
    vat_registered: bool = False
    vat_interval: str = "monthly"  # monthly, bi_monthly, quarterly, four_monthly
    industry: str = ""
    employee_count: int = 0
    address: str = ""
    accountant_name: str = ""
    accountant_contact: str = ""
    notes: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ForecastScenario(SerializableMixin):
    """Saved assumptions for a forward financial projection."""
    id: str
    name: str
    projection_months: int = 6
    baseline_months: int = 3
    income_growth_pct: float = 0.0
    expense_growth_pct: float = 0.0
    one_off_income: float = 0.0
    one_off_expenses: float = 0.0
    notes: str = ""
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    

