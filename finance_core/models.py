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
    

