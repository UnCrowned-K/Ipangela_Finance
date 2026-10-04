"""
Finance Core Package - Comprehensive Finance Management System

This package provides a complete finance management solution including:
- Transaction management with automatic categorization
- Budget planning and tracking with alerts
- Multi-account support
- Customer and supplier ledgers with aging
- South African tax, payroll and entity compliance
- Financial statements on both cash and accrual basis
- Projections and lender-facing funding metrics
- Data import/export functionality
- User authentication and registration
"""

from finance_core.models import (
    TransactionType, CategoryType, AccountType, BudgetPeriod, AlertType,
    ContactRole, LedgerStatus, TaxType, TaxStatus, PayrollStatus, EntityType,
    Category, Account, Transaction, Budget, Alert,
    Contact, Receivable, Payable, TaxRecord, PayrollRun, EntityProfile,
    ForecastScenario
)
from finance_core.storage import DataStorage
from finance_core.managers import (
    CategoryManager, AccountManager, TransactionManager,
    BudgetManager, AlertManager, UserManager
)
from finance_core import periods
from finance_core.ledger import ContactManager, ReceivableManager, PayableManager
from finance_core.compliance import (
    TaxManager, PayrollManager, EntityManager, ForecastManager
)
from finance_core.statements import StatementBuilder
from finance_core.core import FinanceCore, create_finance_core

# For backward compatibility
from finance_core.models import FinanceError, ValidationError, AuthenticationError, AuthorizationError, NotFoundError

__all__ = [
    # Models
    'TransactionType', 'CategoryType', 'AccountType', 'BudgetPeriod', 'AlertType',
    'ContactRole', 'LedgerStatus', 'TaxType', 'TaxStatus', 'PayrollStatus',
    'EntityType',
    'Category', 'Account', 'Transaction', 'Budget', 'Alert',
    'Contact', 'Receivable', 'Payable', 'TaxRecord', 'PayrollRun',
    'EntityProfile', 'ForecastScenario',
    # Storage
    'DataStorage',
    # Periods
    'periods',
    # Managers
    'CategoryManager', 'AccountManager', 'TransactionManager',
    'BudgetManager', 'AlertManager', 'UserManager',
    # Ledger
    'ContactManager', 'ReceivableManager', 'PayableManager',
    # Compliance
    'TaxManager', 'PayrollManager', 'EntityManager', 'ForecastManager',
    # Reporting
    'StatementBuilder',
    # Core
    'FinanceCore', 'create_finance_core',
    # Exceptions
    'FinanceError', 'ValidationError', 'AuthenticationError', 'AuthorizationError', 'NotFoundError'
]
