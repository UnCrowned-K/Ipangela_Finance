"""
Finance Core Package - Comprehensive Finance Management System

This package provides a complete finance management solution including:
- Transaction management with automatic categorization
- Budget planning and tracking with alerts
- Multi-account support
- Financial calculations and projections
- Data import/export functionality
- User authentication and registration
"""

from finance_core.models import (
    TransactionType, CategoryType, AccountType, BudgetPeriod, AlertType,
    Category, Account, Transaction, Budget, Alert
)
from finance_core.storage import DataStorage
from finance_core.managers import (
    CategoryManager, AccountManager, TransactionManager,
    BudgetManager, AlertManager, UserManager
)
from finance_core.core import FinanceCore, create_finance_core

# For backward compatibility
from finance_core.models import FinanceError, ValidationError, AuthenticationError, AuthorizationError, NotFoundError

__all__ = [
    # Models
    'TransactionType', 'CategoryType', 'AccountType', 'BudgetPeriod', 'AlertType',
    'Category', 'Account', 'Transaction', 'Budget', 'Alert',
    # Storage
    'DataStorage',
    # Managers
    'CategoryManager', 'AccountManager', 'TransactionManager',
    'BudgetManager', 'AlertManager', 'UserManager',
    # Core
    'FinanceCore', 'create_finance_core',
    # Exceptions
    'FinanceError', 'ValidationError', 'AuthenticationError', 'AuthorizationError', 'NotFoundError'
]
