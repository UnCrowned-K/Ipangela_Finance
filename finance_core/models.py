import uuid
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


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


@dataclass
class Category:
    """Represents a transaction category."""
    id: str
    name: str
    type: str  # 'income', 'expense', 'transfer'
    icon: str = "tag"
    color: str = "#007a55"
    parent_id: Optional[str] = None
    is_system: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Category':
        return cls(**data)


@dataclass
class Account:
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
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['updated_at'] = datetime.now().isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Account':
        return cls(**data)


@dataclass
class Transaction:
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
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['updated_at'] = datetime.now().isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Transaction':
        return cls(**data)


@dataclass
class Budget:
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
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Budget':
        return cls(**data)


@dataclass
class Alert:
    """Represents a financial alert."""
    id: str
    type: str
    message: str
    severity: str  # 'info', 'warning', 'critical'
    is_read: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    data: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Alert':
        return cls(**data)
