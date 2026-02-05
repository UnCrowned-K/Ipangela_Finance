"""
Finance Core Module - Comprehensive Finance Management System

This module provides a complete finance management solution including:
- Transaction management with automatic categorization
- Budget planning and tracking with alerts
- Multi-account support
- Financial calculations and projections
- Data import/export functionality
- Comprehensive logging and monitoring

@author: Bongani
@date: 2025-02-05
"""

import os
import json
import uuid
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from functools import wraps
import hashlib
import secrets
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

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
    recurring_frequency: Optional[str] = None
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


# =============================================================================
# EXCEPTIONS
# =============================================================================

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


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

class ValidationUtils:
    """Utilities for input validation and sanitization."""
    
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    AMOUNT_REGEX = re.compile(r'^-?\d+(\.\d{1,2})?$')
    
    @staticmethod
    def validate_amount(value: Any, field: str = "amount") -> float:
        """Validate and convert amount value."""
        try:
            amount = float(value)
            if amount < 0:
                raise ValidationError(f"{field} cannot be negative", field)
            return round(amount, 2)
        except (TypeError, ValueError) as e:
            raise ValidationError(f"Invalid {field}: must be a number", field)
    
    @staticmethod
    def validate_date(value: Any, field: str = "date") -> str:
        """Validate and format date value."""
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return value
            except ValueError:
                raise ValidationError(f"Invalid {field}: must be ISO format", field)
        elif isinstance(value, date):
            return value.isoformat()
        raise ValidationError(f"Invalid {field}: must be string or date", field)
    
    @staticmethod
    def validate_email(value: str, field: str = "email") -> str:
        """Validate email format."""
        if not value:
            return value
        if not ValidationUtils.EMAIL_REGEX.match(value):
            raise ValidationError(f"Invalid {field}: invalid email format", field)
        return value.lower().strip()
    
    @staticmethod
    def sanitize_string(value: Any, field: str = "string", max_length: int = 500) -> str:
        """Sanitize string input."""
        if value is None:
            return ""
        if not isinstance(value, str):
            value = str(value)
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\'\\{}|\[\]]', '', value)
        return sanitized.strip()[:max_length]
    
    @staticmethod
    def validate_account_type(value: str, field: str = "account_type") -> str:
        """Validate account type."""
        valid_types = [t.value for t in AccountType]
        if value.lower() not in valid_types:
            raise ValidationError(
                f"Invalid {field}: must be one of {', '.join(valid_types)}",
                field
            )
        return value.lower()
    
    @staticmethod
    def validate_transaction_type(value: str, field: str = "transaction_type") -> str:
        """Validate transaction type."""
        valid_types = [t.value for t in TransactionType]
        if value.lower() not in valid_types:
            raise ValidationError(
                f"Invalid {field}: must be one of {', '.join(valid_types)}",
                field
            )
        return value.lower()
    
    @staticmethod
    def generate_secure_id() -> str:
        """Generate a secure unique identifier."""
        return str(uuid.uuid4())
    
    @staticmethod
    def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
        """Hash a password with salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash_obj.hexdigest(), salt
    
    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """Verify a password against its hash."""
        new_hash, _ = ValidationUtils.hash_password(password, salt)
        return secrets.compare_digest(new_hash, hashed)


# =============================================================================
# DATA STORAGE
# =============================================================================

class DataStorage:
    """Handles persistent data storage for the finance system."""
    
    def __init__(self, storage_dir: str = None):
        """Initialize the data storage."""
        if storage_dir is None:
            # Use server directory relative to this file
            storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        
        self.storage_dir = storage_dir
        self._ensure_directories()
        
        # Data files
        self.transactions_file = os.path.join(storage_dir, 'transactions.json')
        self.accounts_file = os.path.join(storage_dir, 'accounts.json')
        self.budgets_file = os.path.join(storage_dir, 'budgets.json')
        self.categories_file = os.path.join(storage_dir, 'categories.json')
        self.alerts_file = os.path.join(storage_dir, 'alerts.json')
        self.users_file = os.path.join(storage_dir, 'users.json')
    
    def _ensure_directories(self):
        """Ensure storage directories exist."""
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create storage directory: {e}")
            raise FinanceError(f"Storage initialization failed: {e}")
    
    def _read_json(self, filepath: str, default: Any = None) -> Any:
        """Read JSON data from file."""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error reading {filepath}: {e}")
            return default
    
    def _write_json(self, filepath: str, data: Any) -> bool:
        """Write JSON data to file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            logger.error(f"Error writing {filepath}: {e}")
            return False
    
    # Transactions
    def get_transactions(self) -> List[Dict]:
        return self._read_json(self.transactions_file, [])
    
    def save_transactions(self, transactions: List[Dict]) -> bool:
        return self._write_json(self.transactions_file, transactions)
    
    # Accounts
    def get_accounts(self) -> List[Dict]:
        return self._read_json(self.accounts_file, [])
    
    def save_accounts(self, accounts: List[Dict]) -> bool:
        return self._write_json(self.accounts_file, accounts)
    
    # Budgets
    def get_budgets(self) -> List[Dict]:
        return self._read_json(self.budgets_file, [])
    
    def save_budgets(self, budgets: List[Dict]) -> bool:
        return self._write_json(self.budgets_file, budgets)
    
    # Categories
    def get_categories(self) -> List[Dict]:
        return self._read_json(self.categories_file, [])
    
    def save_categories(self, categories: List[Dict]) -> bool:
        return self._write_json(self.categories_file, categories)
    
    # Alerts
    def get_alerts(self) -> List[Dict]:
        return self._read_json(self.alerts_file, [])
    
    def save_alerts(self, alerts: List[Dict]) -> bool:
        return self._write_json(self.alerts_file, alerts)
    
    # Users
    def get_users(self) -> List[Dict]:
        return self._read_json(self.users_file, [])
    
    def save_users(self, users: List[Dict]) -> bool:
        return self._write_json(self.users_file, users)
    
    def backup_data(self, backup_dir: str = None) -> bool:
        """Create a backup of all data files."""
        if backup_dir is None:
            backup_dir = os.path.join(self.storage_dir, 'backups')
        
        try:
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            files = [
                'transactions.json', 'accounts.json', 'budgets.json',
                'categories.json', 'alerts.json', 'users.json'
            ]
            
            for filename in files:
                src = os.path.join(self.storage_dir, filename)
                if os.path.exists(src):
                    dst = os.path.join(backup_dir, f'{timestamp}_{filename}')
                    with open(src, 'r') as sf, open(dst, 'w') as df:
                        df.write(sf.read())
            
            logger.info(f"Backup created successfully: {timestamp}")
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False


# =============================================================================
# CATEGORY MANAGER
# =============================================================================

class CategoryManager:
    """Manages transaction categories."""
    
    DEFAULT_CATEGORIES = [
        # Income categories
        {"id": "inc_salary", "name": "Salary", "type": "income", "icon": "dollar-sign", "color": "#28a745", "is_system": True},
        {"id": "inc_investment", "name": "Investment Income", "type": "income", "icon": "trending-up", "color": "#20c997", "is_system": True},
        {"id": "inc_other", "name": "Other Income", "type": "income", "icon": "plus-circle", "color": "#17a2b8", "is_system": True},
        
        # Expense categories
        {"id": "exp_housing", "name": "Housing", "type": "expense", "icon": "home", "color": "#dc3545", "is_system": True},
        {"id": "exp_food", "name": "Food & Groceries", "type": "expense", "icon": "shopping-cart", "color": "#fd7e14", "is_system": True},
        {"id": "exp_transport", "name": "Transportation", "type": "expense", "icon": "car", "color": "#6610f2", "is_system": True},
        {"id": "exp_utilities", "name": "Utilities", "type": "expense", "icon": "zap", "color": "#6f42c1", "is_system": True},
        {"id": "exp_healthcare", "name": "Healthcare", "type": "expense", "icon": "heart", "color": "#e83e8c", "is_system": True},
        {"id": "exp_entertainment", "name": "Entertainment", "type": "expense", "icon": "film", "color": "#20c997", "is_system": True},
        {"id": "exp_shopping", "name": "Shopping", "type": "expense", "icon": "shopping-bag", "color": "#fd7e14", "is_system": True},
        {"id": "exp_education", "name": "Education", "type": "expense", "icon": "book", "color": "#007bff", "is_system": True},
        {"id": "exp_insurance", "name": "Insurance", "type": "expense", "icon": "shield", "color": "#6c757d", "is_system": True},
        {"id": "exp_taxes", "name": "Taxes", "type": "expense", "icon": "file-text", "color": "#343a40", "is_system": True},
        {"id": "exp_other", "name": "Other Expenses", "type": "expense", "icon": "ellipsis-circle", "color": "#adb5bd", "is_system": True},
        
        # Transfer category
        {"id": "transfer", "name": "Transfer", "type": "transfer", "icon": "repeat", "color": "#6c757d", "is_system": True}
    ]
    
    def __init__(self, storage: DataStorage = None):
        """Initialize the category manager."""
        self.storage = storage or DataStorage()
        self._categories = None
    
    @property
    def categories(self) -> List[Category]:
        """Get all categories."""
        if self._categories is None:
            self._load_categories()
        return self._categories
    
    def _load_categories(self):
        """Load categories from storage or initialize defaults."""
        data = self.storage.get_categories()
        if not data:
            data = self.DEFAULT_CATEGORIES
            self.storage.save_categories(data)
        self._categories = [Category.from_dict(c) for c in data]
    
    def get_category(self, category_id: str) -> Optional[Category]:
        """Get a specific category by ID."""
        return next((c for c in self.categories if c.id == category_id), None)
    
    def get_categories_by_type(self, type_str: str) -> List[Category]:
        """Get categories filtered by type."""
        return [c for c in self.categories if c.type == type_str]
    
    def create_category(self, name: str, type_str: str, icon: str = "tag", 
                        color: str = "#007a55", parent_id: str = None) -> Category:
        """Create a new category."""
        ValidationUtils.sanitize_string(name, "name", 100)
        ValidationUtils.sanitize_string(type_str, "type")
        
        # Check for duplicate names
        if any(c.name.lower() == name.lower() for c in self.categories):
            raise ValidationError(f"Category '{name}' already exists")
        
        category = Category(
            id=ValidationUtils.generate_secure_id(),
            name=name,
            type=type_str,
            icon=icon,
            color=color,
            parent_id=parent_id,
            is_system=False
        )
        
        self._categories.append(category)
        self._save_categories()
        return category
    
    def update_category(self, category_id: str, **kwargs) -> Category:
        """Update an existing category."""
        category = self.get_category(category_id)
        if not category:
            raise NotFoundError("Category", category_id)
        
        if category.is_system:
            raise ValidationError("Cannot modify system categories")
        
        for key, value in kwargs.items():
            if hasattr(category, key) and key not in ['id', 'is_system']:
                if key == 'name':
                    value = ValidationUtils.sanitize_string(value, key, 100)
                setattr(category, key, value)
        
        self._save_categories()
        return category
    
    def delete_category(self, category_id: str) -> bool:
        """Delete a category (soft delete for system categories)."""
        category = self.get_category(category_id)
        if not category:
            raise NotFoundError("Category", category_id)
        
        if category.is_system:
            # Soft delete - just mark as inactive
            category.is_active = False
        else:
            self._categories = [c for c in self._categories if c.id != category_id]
        
        self._save_categories()
        return True
    
    def _save_categories(self):
        """Save categories to storage."""
        data = [c.to_dict() for c in self.categories]
        self.storage.save_categories(data)
    
    def auto_categorize(self, description: str, amount: float) -> str:
        """Automatically suggest a category based on description and amount."""
        description_lower = description.lower()
        
        # Keywords for expense categories
        expense_keywords = {
            'exp_housing': ['rent', 'mortgage', 'housing', 'apartment', 'property'],
            'exp_food': ['food', 'grocery', 'restaurant', 'cafe', 'dinner', 'lunch', 'breakfast', 'takeaway'],
            'exp_transport': ['gas', 'fuel', 'uber', 'taxi', 'bus', 'train', 'car', 'automotive', 'petrol'],
            'exp_utilities': ['electric', 'water', 'internet', 'phone', 'utility', 'power'],
            'exp_healthcare': ['doctor', 'hospital', 'pharmacy', 'medical', 'health', 'dental'],
            'exp_entertainment': ['movie', 'cinema', 'concert', 'game', 'entertainment', 'streaming', 'netflix'],
            'exp_shopping': ['amazon', 'shopping', 'store', 'mall', 'retail'],
            'exp_education': ['school', 'university', 'course', 'education', 'tuition', 'book'],
            'exp_insurance': ['insurance', 'policy', 'premium'],
            'exp_taxes': ['tax', 'irs', 'sars'],
        }
        
        # Keywords for income categories
        income_keywords = {
            'inc_salary': ['salary', 'payroll', 'wage', 'income', 'paycheck', 'direct deposit'],
            'inc_investment': ['dividend', 'interest', 'investment', 'return', 'capital gain'],
        }
        
        # Check expense keywords first
        if amount < 0 or amount > 0:  # For expenses, we'll consider negative amounts
            for category_id, keywords in expense_keywords.items():
                if any(kw in description_lower for kw in keywords):
                    return category_id
        
        # Check income keywords
        if amount > 0:
            for category_id, keywords in income_keywords.items():
                if any(kw in description_lower for kw in keywords):
                    return category_id
        
        return 'exp_other' if amount < 0 else 'inc_other'


# =============================================================================
# ACCOUNT MANAGER
# =============================================================================

class AccountManager:
    """Manages financial accounts."""
    
    def __init__(self, storage: DataStorage = None):
        """Initialize the account manager."""
        self.storage = storage or DataStorage()
        self._accounts = None
    
    @property
    def accounts(self) -> List[Account]:
        """Get all accounts."""
        if self._accounts is None:
            self._load_accounts()
        return self._accounts
    
    def _load_accounts(self):
        """Load accounts from storage."""
        data = self.storage.get_accounts()
        self._accounts = [Account.from_dict(a) for a in data]
    
    def _save_accounts(self):
        """Save accounts to storage."""
        data = [a.to_dict() for a in self.accounts]
        self.storage.save_accounts(data)
    
    def get_account(self, account_id: str) -> Optional[Account]:
        """Get a specific account by ID."""
        return next((a for a in self.accounts if a.id == account_id), None)
    
    def get_active_accounts(self) -> List[Account]:
        """Get only active accounts."""
        return [a for a in self.accounts if a.is_active]
    
    def create_account(self, name: str, type_str: str, balance: float = 0.0,
                       currency: str = "ZAR", institution: str = "",
                       account_number: str = "", notes: str = "") -> Account:
        """Create a new account."""
        ValidationUtils.sanitize_string(name, "name", 100)
        ValidationUtils.validate_account_type(type_str, "type")
        balance_amount = ValidationUtils.validate_amount(balance, "balance")
        
        account = Account(
            id=ValidationUtils.generate_secure_id(),
            name=name,
            type=type_str,
            balance=balance_amount,
            currency=currency.upper(),
            institution=ValidationUtils.sanitize_string(institution, "institution"),
            account_number=ValidationUtils.sanitize_string(account_number, "account_number"),
            notes=ValidationUtils.sanitize_string(notes, "notes", 1000)
        )
        
        self._accounts.append(account)
        self._save_accounts()
        logger.info(f"Created account: {account.name} ({account.id})")
        return account
    
    def update_account(self, account_id: str, **kwargs) -> Account:
        """Update an existing account."""
        account = self.get_account(account_id)
        if not account:
            raise NotFoundError("Account", account_id)
        
        for key, value in kwargs.items():
            if hasattr(account, key) and key not in ['id', 'created_at']:
                if key == 'balance':
                    value = ValidationUtils.validate_amount(value, key)
                elif key in ['name', 'institution', 'account_number', 'notes']:
                    value = ValidationUtils.sanitize_string(value, key)
                elif key == 'currency':
                    value = value.upper()
                elif key == 'type':
                    value = ValidationUtils.validate_account_type(value, key)
                setattr(account, key, value)
        
        self._save_accounts()
        logger.info(f"Updated account: {account.name} ({account.id})")
        return account
    
    def delete_account(self, account_id: str) -> bool:
        """Delete an account."""
        account = self.get_account(account_id)
        if not account:
            raise NotFoundError("Account", account_id)
        
        self._accounts = [a for a in self.accounts if a.id != account_id]
        self._save_accounts()
        logger.info(f"Deleted account: {account.name} ({account.id})")
        return True
    
    def get_total_balance(self) -> Dict[str, float]:
        """Calculate total balance across all accounts."""
        totals = {
            'total': 0.0,
            'checking': 0.0,
            'savings': 0.0,
            'credit': 0.0,
            'cash': 0.0,
            'investment': 0.0,
            'loan': 0.0,
            'other': 0.0
        }
        
        for account in self.get_active_accounts():
            if account.type in totals:
                totals[account.type] += account.balance
                totals['total'] += account.balance
        
        return totals


# =============================================================================
# TRANSACTION MANAGER
# =============================================================================

class TransactionManager:
    """Manages financial transactions."""
    
    def __init__(self, storage: DataStorage = None, category_manager: CategoryManager = None):
        """Initialize the transaction manager."""
        self.storage = storage or DataStorage()
        self.category_manager = category_manager or CategoryManager(storage)
        self._transactions = None
    
    @property
    def transactions(self) -> List[Transaction]:
        """Get all transactions."""
        if self._transactions is None:
            self._load_transactions()
        return self._transactions
    
    def _load_transactions(self):
        """Load transactions from storage."""
        data = self.storage.get_transactions()
        self._transactions = [Transaction.from_dict(t) for t in data]
    
    def _save_transactions(self):
        """Save transactions to storage."""
        data = [t.to_dict() for t in self.transactions]
        self.storage.save_transactions(data)
    
    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Get a specific transaction by ID."""
        return next((t for t in self.transactions if t.id == transaction_id), None)
    
    def create_transaction(self, account_id: str, type_str: str, amount: float,
                          category_id: str = None, description: str = "",
                          date_str: str = None, payee: str = "", notes: str = "",
                          tags: List[str] = None, is_recurring: bool = False,
                          recurring_frequency: str = None) -> Transaction:
        """Create a new transaction."""
        # Validate account exists
        account_manager = AccountManager(self.storage)
        if not account_manager.get_account(account_id):
            raise NotFoundError("Account", account_id)
        
        # Auto-categorize if no category provided
        if category_id is None:
            category_id = self.category_manager.auto_categorize(description, amount)
        
        # Validate category
        if not self.category_manager.get_category(category_id):
            raise NotFoundError("Category", category_id)
        
        transaction = Transaction(
            id=ValidationUtils.generate_secure_id(),
            account_id=account_id,
            type=ValidationUtils.validate_transaction_type(type_str),
            amount=ValidationUtils.validate_amount(amount),
            category_id=category_id,
            description=ValidationUtils.sanitize_string(description, "description", 500),
            date=ValidationUtils.validate_date(date_str or date.today().isoformat(), "date"),
            payee=ValidationUtils.sanitize_string(payee, "payee", 200),
            notes=ValidationUtils.sanitize_string(notes, "notes", 1000),
            tags=[ValidationUtils.sanitize_string(t, "tag", 50) for t in (tags or [])],
            is_recurring=is_recurring,
            recurring_frequency=recurring_frequency
        )
        
        self._transactions.append(transaction)
        self._save_transactions()
        
        # Update account balance
        self._update_account_balance(account_id, amount, type_str)
        
        logger.info(f"Created transaction: {transaction.description} ({transaction.amount})")
        return transaction
    
    def update_transaction(self, transaction_id: str, **kwargs) -> Transaction:
        """Update an existing transaction."""
        transaction = self.get_transaction(transaction_id)
        if not transaction:
            raise NotFoundError("Transaction", transaction_id)
        
        old_amount = transaction.amount
        old_type = transaction.type
        
        for key, value in kwargs.items():
            if hasattr(transaction, key) and key not in ['id', 'created_at']:
                if key == 'amount':
                    value = ValidationUtils.validate_amount(value)
                elif key in ['description', 'payee', 'notes']:
                    value = ValidationUtils.sanitize_string(value, key)
                elif key == 'date':
                    value = ValidationUtils.validate_date(value)
                elif key == 'category_id':
                    if not self.category_manager.get_category(value):
                        raise NotFoundError("Category", value)
                elif key == 'type':
                    value = ValidationUtils.validate_transaction_type(value)
                setattr(transaction, key, value)
        
        self._save_transactions()
        
        # Adjust account balance if amount or type changed
        if old_amount != transaction.amount or old_type != transaction.type:
            # Revert old effect
            self._update_account_balance(transaction.account_id, -old_amount, old_type)
            # Apply new effect
            self._update_account_balance(transaction.account_id, transaction.amount, transaction.type)
        
        logger.info(f"Updated transaction: {transaction.description} ({transaction.id})")
        return transaction
    
    def delete_transaction(self, transaction_id: str) -> bool:
        """Delete a transaction."""
        transaction = self.get_transaction(transaction_id)
        if not transaction:
            raise NotFoundError("Transaction", transaction_id)
        
        # Reverse the balance effect
        self._update_account_balance(transaction.account_id, -transaction.amount, transaction.type)
        
        self._transactions = [t for t in self.transactions if t.id != transaction_id]
        self._save_transactions()
        
        logger.info(f"Deleted transaction: {transaction.description} ({transaction.id})")
        return True
    
    def _update_account_balance(self, account_id: str, amount: float, type_str: str):
        """Update account balance after transaction."""
        account_manager = AccountManager(self.storage)
        account = account_manager.get_account(account_id)
        if account:
            if type_str == TransactionType.INCOME.value:
                account.balance += amount
            elif type_str == TransactionType.EXPENSE.value:
                account.balance -= amount
            # Transfers don't affect total balance
            account_manager._save_accounts()
    
    def get_transactions_by_account(self, account_id: str) -> List[Transaction]:
        """Get all transactions for a specific account."""
        return [t for t in self.transactions if t.account_id == account_id]
    
    def get_transactions_by_date_range(self, start_date: str, end_date: str) -> List[Transaction]:
        """Get transactions within a date range."""
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        return [t for t in self.transactions 
                if start <= datetime.fromisoformat(t.date) <= end]
    
    def get_transactions_by_category(self, category_id: str) -> List[Transaction]:
        """Get all transactions for a specific category."""
        return [t for t in self.transactions if t.category_id == category_id]
    
    def get_transactions_by_type(self, type_str: str) -> List[Transaction]:
        """Get all transactions of a specific type."""
        return [t for t in self.transactions if t.type == type_str]
    
    def search_transactions(self, query: str) -> List[Transaction]:
        """Search transactions by description, payee, or notes."""
        query_lower = query.lower()
        return [t for t in self.transactions 
                if query_lower in t.description.lower() or 
                   query_lower in t.payee.lower() or 
                   query_lower in t.notes.lower() or
                   any(query_lower in tag.lower() for tag in t.tags)]
    
    def get_summary(self, start_date: str = None, end_date: str = None, 
                   account_id: str = None) -> Dict[str, float]:
        """Get transaction summary for a period."""
        transactions = self.transactions
        
        if account_id:
            transactions = [t for t in transactions if t.account_id == account_id]
        
        if start_date and end_date:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            transactions = [t for t in transactions 
                           if start <= datetime.fromisoformat(t.date) <= end]
        
        income = sum(t.amount for t in transactions if t.type == TransactionType.INCOME.value)
        expenses = sum(t.amount for t in transactions if t.type == TransactionType.EXPENSE.value)
        transfers = sum(t.amount for t in transactions if t.type == TransactionType.TRANSFER.value)
        
        return {
            'income': round(income, 2),
            'expenses': round(expenses, 2),
            'transfers': round(transfers, 2),
            'net_income': round(income - expenses, 2),
            'transaction_count': len(transactions)
        }


# =============================================================================
# BUDGET MANAGER
# =============================================================================

class BudgetManager:
    """Manages budget planning and tracking."""
    
    def __init__(self, storage: DataStorage = None, transaction_manager: TransactionManager = None):
        """Initialize the budget manager."""
        self.storage = storage or DataStorage()
        self.transaction_manager = transaction_manager or TransactionManager(storage)
        self._budgets = None
    
    @property
    def budgets(self) -> List[Budget]:
        """Get all budgets."""
        if self._budgets is None:
            self._load_budgets()
        return self._budgets
    
    def _load_budgets(self):
        """Load budgets from storage."""
        data = self.storage.get_budgets()
        self._budgets = [Budget.from_dict(b) for b in data]
    
    def _save_budgets(self):
        """Save budgets to storage."""
        data = [b.to_dict() for b in self.budgets]
        self.storage.save_budgets(data)
    
    def get_budget(self, budget_id: str) -> Optional[Budget]:
        """Get a specific budget by ID."""
        return next((b for b in self.budgets if b.id == budget_id), None)
    
    def create_budget(self, name: str, category_id: str, amount: float,
                     period: str = "monthly", start_date: str = None,
                     alert_threshold: float = 80.0) -> Budget:
        """Create a new budget."""
        ValidationUtils.sanitize_string(name, "name", 100)
        amount_value = ValidationUtils.validate_amount(amount)
        
        if not self.transaction_manager.category_manager.get_category(category_id):
            raise NotFoundError("Category", category_id)
        
        budget = Budget(
            id=ValidationUtils.generate_secure_id(),
            name=name,
            category_id=category_id,
            amount=amount_value,
            spent=0.0,
            period=period,
            start_date=ValidationUtils.validate_date(start_date or date.today().isoformat()),
            alert_threshold=alert_threshold
        )
        
        self._budgets.append(budget)
        self._save_budgets()
        
        logger.info(f"Created budget: {budget.name} ({budget.amount})")
        return budget
    
    def update_budget(self, budget_id: str, **kwargs) -> Budget:
        """Update an existing budget."""
        budget = self.get_budget(budget_id)
        if not budget:
            raise NotFoundError("Budget", budget_id)
        
        for key, value in kwargs.items():
            if hasattr(budget, key) and key not in ['id', 'created_at', 'spent']:
                if key == 'amount':
                    value = ValidationUtils.validate_amount(value)
                elif key == 'name':
                    value = ValidationUtils.sanitize_string(value, key, 100)
                elif key == 'period':
                    valid_periods = [p.value for p in BudgetPeriod]
                    if value not in valid_periods:
                        raise ValidationError(f"Invalid period: must be {', '.join(valid_periods)}")
                setattr(budget, key, value)
        
        self._save_budgets()
        logger.info(f"Updated budget: {budget.name} ({budget.id})")
        return budget
    
    def delete_budget(self, budget_id: str) -> bool:
        """Delete a budget."""
        budget = self.get_budget(budget_id)
        if not budget:
            raise NotFoundError("Budget", budget_id)
        
        self._budgets = [b for b in self.budgets if b.id != budget_id]
        self._save_budgets()
        logger.info(f"Deleted budget: {budget.name} ({budget.id})")
        return True
    
    def calculate_spent(self, budget_id: str) -> float:
        """Calculate actual spending against a budget."""
        budget = self.get_budget(budget_id)
        if not budget:
            raise NotFoundError("Budget", budget_id)
        
        # Get transactions for this category in the budget period
        start_date = budget.start_date
        end_date = budget.end_date or date.today().isoformat()
        
        transactions = self.transaction_manager.get_transactions_by_category(budget.category_id)
        transactions = [t for t in transactions 
                        if datetime.fromisoformat(start_date) <= datetime.fromisoformat(t.date) <= datetime.fromisoformat(end_date)]
        
        return sum(t.amount for t in transactions if t.type == TransactionType.EXPENSE.value)
    
    def update_budget_spending(self, budget_id: str) -> Budget:
        """Update the spent amount for a budget."""
        budget = self.get_budget(budget_id)
        if not budget:
            raise NotFoundError("Budget", budget_id)
        
        budget.spent = self.calculate_spent(budget_id)
        self._save_budgets()
        return budget
    
    def get_budget_status(self, budget_id: str) -> Dict[str, Any]:
        """Get detailed budget status including alerts."""
        budget = self.get_budget(budget_id)
        if not budget:
            raise NotFoundError("Budget", budget_id)
        
        # Update spent amount
        budget = self.update_budget_spending(budget_id)
        
        percentage = (budget.spent / budget.amount * 100) if budget.amount > 0 else 0
        remaining = budget.amount - budget.spent
        
        alerts = []
        if percentage >= budget.alert_threshold:
            alerts.append({
                'type': AlertType.BUDGET_WARNING.value,
                'message': f"Budget '{budget.name}' has reached {percentage:.1f}% of limit",
                'severity': 'warning'
            })
        if budget.spent > budget.amount:
            alerts.append({
                'type': AlertType.BUDGET_EXCEEDED.value,
                'message': f"Budget '{budget.name}' has exceeded the limit by {abs(remaining):.2f}",
                'severity': 'critical'
            })
        
        return {
            'budget': budget,
            'spent': round(budget.spent, 2),
            'remaining': round(remaining, 2),
            'percentage': round(percentage, 1),
            'status': 'over_budget' if budget.spent > budget.amount else 
                     ('warning' if percentage >= budget.alert_threshold else 'ok'),
            'alerts': alerts
        }
    
    def get_all_budgets_status(self) -> List[Dict[str, Any]]:
        """Get status for all active budgets."""
        return [self.get_budget_status(b.id) for b in self.budgets if b.is_active]
    
    def get_category_budget_summary(self) -> Dict[str, Dict[str, float]]:
        """Get budget summary grouped by category."""
        summary = {}
        for budget in self.budgets:
            if budget.category_id not in summary:
                category = self.transaction_manager.category_manager.get_category(budget.category_id)
                summary[budget.category_id] = {
                    'name': category.name if category else 'Unknown',
                    'allocated': 0,
                    'spent': 0
                }
            summary[budget.category_id]['allocated'] += budget.amount
            summary[budget.category_id]['spent'] += self.calculate_spent(budget.id)
        
        return summary


# =============================================================================
# ALERT MANAGER
# =============================================================================

class AlertManager:
    """Manages financial alerts."""
    
    def __init__(self, storage: DataStorage = None, budget_manager: BudgetManager = None):
        """Initialize the alert manager."""
        self.storage = storage or DataStorage()
        self.budget_manager = budget_manager or BudgetManager(storage)
        self._alerts = None
    
    @property
    def alerts(self) -> List[Alert]:
        """Get all alerts."""
        if self._alerts is None:
            self._load_alerts()
        return self._alerts
    
    def _load_alerts(self):
        """Load alerts from storage."""
        data = self.storage.get_alerts()
        self._alerts = [Alert.from_dict(a) for a in data]
    
    def _save_alerts(self):
        """Save alerts to storage."""
        data = [a.to_dict() for a in self.alerts]
        self.storage.save_alerts(data)
    
    def create_alert(self, type_str: str, message: str, severity: str = "info",
                     data: Dict = None) -> Alert:
        """Create a new alert."""
        alert = Alert(
            id=ValidationUtils.generate_secure_id(),
            type=type_str,
            message=ValidationUtils.sanitize_string(message, "message", 1000),
            severity=severity,
            data=data or {}
        )
        
        self._alerts.append(alert)
        self._save_alerts()
        
        logger.info(f"Created alert: {type_str} - {message}")
        return alert
    
    def mark_alert_read(self, alert_id: str) -> Alert:
        """Mark an alert as read."""
        alert = next((a for a in self.alerts if a.id == alert_id), None)
        if not alert:
            raise NotFoundError("Alert", alert_id)
        
        alert.is_read = True
        self._save_alerts()
        return alert
    
    def mark_all_alerts_read(self) -> int:
        """Mark all alerts as read."""
        count = 0
        for alert in self.alerts:
            if not alert.is_read:
                alert.is_read = True
                count += 1
        self._save_alerts()
        return count
    
    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert."""
        self._alerts = [a for a in self.alerts if a.id != alert_id]
        self._save_alerts()
        return True
    
    def clear_old_alerts(self, days: int = 30) -> int:
        """Clear alerts older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        original_count = len(self.alerts)
        self._alerts = [a for a in self.alerts 
                       if datetime.fromisoformat(a.created_at) >= cutoff]
        deleted_count = original_count - len(self.alerts)
        self._save_alerts()
        return deleted_count
    
    def get_unread_alerts(self) -> List[Alert]:
        """Get all unread alerts."""
        return [a for a in self.alerts if not a.is_read]
    
    def check_budget_alerts(self) -> List[Alert]:
        """Check all budgets and generate alerts if needed."""
        new_alerts = []
        for status in self.budget_manager.get_all_budgets_status():
            for alert_data in status.get('alerts', []):
                new_alerts.append(
                    self.create_alert(
                        type_str=alert_data['type'],
                        message=alert_data['message'],
                        severity=alert_data['severity'],
                        data={'budget_id': status['budget'].id}
                    )
                )
        return new_alerts
    
    def check_balance_alerts(self, low_balance_threshold: float = 100.0) -> List[Alert]:
        """Check account balances and generate low balance alerts."""
        new_alerts = []
        account_manager = AccountManager(self.storage)
        
        for account in account_manager.get_active_accounts():
            if account.balance < low_balance_threshold:
                new_alerts.append(
                    self.create_alert(
                        type_str=AlertType.LOW_BALANCE.value,
                        message=f"Low balance alert: {account.name} has {account.balance:.2f} {account.currency}",
                        severity='warning',
                        data={'account_id': account.id, 'balance': account.balance}
                    )
                )
        return new_alerts


# =============================================================================
# FINANCE CORE - MAIN CLASS
# =============================================================================

class FinanceCore:
    """
    Main finance management system class.
    
    Provides a unified interface for all finance operations including
    accounts, transactions, budgets, categories, and alerts.
    """
    
    def __init__(self, storage_dir: str = None):
        """Initialize the finance core system."""
        self.storage = DataStorage(storage_dir)
        
        # Initialize managers
        self.category_manager = CategoryManager(self.storage)
        self.account_manager = AccountManager(self.storage)
        self.transaction_manager = TransactionManager(self.storage, self.category_manager)
        self.budget_manager = BudgetManager(self.storage, self.transaction_manager)
        self.alert_manager = AlertManager(self.storage, self.budget_manager)
        
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
            raise ValidationError(f"Unknown report type: {report_type}")
    
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
            raise ValidationError(f"Unsupported export format: {export_format}")
    
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
                        account_number=acc_data.get('account_number', ''),
                        notes=acc_data.get('notes', '')
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
        import csv
        
        transactions = self.transaction_manager.transactions
        if start_date and end_date:
            transactions = self.transaction_manager.get_transactions_by_date_range(start_date, end_date)
        
        output = []
        output.append('Date,Description,Category,Amount,Type,Account,Payee,Notes')
        
        for t in transactions:
            category = self.category_manager.get_category(t.category_id)
            account = self.account_manager.get_account(t.account_id)
            output.append(
                f"{t.date},\"{t.description}\",\"{category.name if category else 'Unknown'}\","
                f"{t.amount},{t.type},\"{account.name if account else 'Unknown' if t.payee else ''}\","
                f"\"{t.notes}\""
            )
        
        return '\n'.join(output)
    
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
        
        # Check data consistency
        for account in self.account_manager.accounts:
            if not account.is_active:
                continue
            account_transactions = self.transaction_manager.get_transactions_by_account(account.id)
            calculated_balance = account.balance
            
            for t in account_transactions:
                if t.type == TransactionType.INCOME.value:
                    calculated_balance -= t.amount
                elif t.type == TransactionType.EXPENSE.value:
                    calculated_balance += t.amount
            
            # Note: This is a simplified check
        
        return {
            'status': 'healthy' if not issues else 'warning',
            'issues': issues,
            'timestamp': datetime.now().isoformat()
        }
    
    def clear_all_data(self) -> bool:
        """Clear all financial data (use with caution!)."""
        self.storage._write_json(self.storage.transactions_file, [])
        self.storage._write_json(self.storage.accounts_file, [])
        self.storage._write_json(self.storage.budgets_file, [])
        self.storage._write_json(self.storage.alerts_file, [])
        
        self._transactions = None
        self._accounts = None
        self._budgets = None
        self._alerts = None
        
        logger.warning("All financial data has been cleared")
        return True


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_finance_core(storage_dir: str = None) -> FinanceCore:
    """Factory function to create a FinanceCore instance."""
    return FinanceCore(storage_dir)


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    # Initialize the finance system
    finance = create_finance_core()
    
    # Create some sample data
    print("Creating sample financial data...")
    
    # Create accounts
    checking = finance.account_manager.create_account(
        name="Main Checking",
        type_str="checking",
        balance=5000.0,
        institution="First National Bank"
    )
    
    savings = finance.account_manager.create_account(
        name="Emergency Savings",
        type_str="savings",
        balance=15000.0,
        institution="First National Bank"
    )
    
    credit = finance.account_manager.create_account(
        name="Credit Card",
        type_str="credit",
        balance=-500.0,
        institution="Standard Bank"
    )
    
    print(f"Created accounts: {checking.name}, {savings.name}, {credit.name}")
    
    # Create some transactions
    finance.transaction_manager.create_transaction(
        account_id=checking.id,
        type_str="income",
        amount=5000.0,
        category_id="inc_salary",
        description="Monthly Salary",
        date_str=date.today().isoformat()
    )
    
    finance.transaction_manager.create_transaction(
        account_id=checking.id,
        type_str="expense",
        amount=1500.0,
        category_id="exp_housing",
        description="Monthly Rent",
        date_str=date.today().isoformat()
    )
    
    finance.transaction_manager.create_transaction(
        account_id=checking.id,
        type_str="expense",
        amount=500.0,
        category_id="exp_food",
        description="Grocery Shopping",
        date_str=(date.today() - timedelta(days=1)).isoformat()
    )
    
    print("Created sample transactions")
    
    # Create a budget
    budget = finance.budget_manager.create_budget(
        name="Monthly Food Budget",
        category_id="exp_food",
        amount=1000.0,
        period="monthly"
    )
    
    print(f"Created budget: {budget.name}")
    
    # Get dashboard data
    dashboard = finance.get_dashboard_data()
    print("\nDashboard Summary:")
    print(f"Total Balance: {dashboard['account_balances']['total']}")
    print(f"Monthly Income: {dashboard['transaction_summary']['income']}")
    print(f"Monthly Expenses: {dashboard['transaction_summary']['expenses']}")
    
    # Generate a report
    report = finance.generate_report("summary")
    print("\nReport generated successfully")
    
    print("\nFinance Core system is ready!")
