import os
import uuid
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple

from finance_core.models import (
    TransactionType, CategoryType, AccountType, BudgetPeriod, AlertType,
    Category, Account, Transaction, Budget, Alert
)
from finance_core.storage import DataStorage
from utils import ValidationUtils

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
            raise ValueError(f"Category '{name}' already exists")
        
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
            raise ValueError(f"Category not found: {category_id}")
        
        if category.is_system:
            raise ValueError("Cannot modify system categories")
        
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
            raise ValueError(f"Category not found: {category_id}")
        
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
        if amount <0 or amount >0:  # For expenses, we'll consider negative amounts
            for category_id, keywords in expense_keywords.items():
                if any(kw in description_lower for kw in keywords):
                    return category_id
        
        # Check income keywords
        if amount >0:
            for category_id, keywords in income_keywords.items():
                if any(kw in description_lower for kw in keywords):
                    return category_id
        
        return 'exp_other' if amount <0 else 'inc_other'


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
    
    def create_account(self, name: str, type_str: str, balance: float =0.0,
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
            raise ValueError(f"Account not found: {account_id}")
        
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
            raise ValueError(f"Account not found: {account_id}")
        
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
    
    def get_active_accounts(self) -> List[Account]:
        """Get all active accounts."""
        return [a for a in self.accounts if a.is_active]


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
                          recurring_frequency: str = None,
                          destination_account_id: str = None) -> Transaction:
        """Create a new transaction."""
        # Validate account exists
        account_manager = AccountManager(self.storage)
        if not account_manager.get_account(account_id):
            raise ValueError(f"Account not found: {account_id}")
        
        # For transfers, validate destination account
        if type_str == TransactionType.TRANSFER.value:
            if not destination_account_id:
                raise ValueError("Destination account required for transfers")
            if not account_manager.get_account(destination_account_id):
                raise ValueError(f"Destination account not found: {destination_account_id}")
            if account_id == destination_account_id:
                raise ValueError("Source and destination accounts must be different")
        
        # Auto-categorize if no category provided
        if category_id is None:
            category_id = self.category_manager.auto_categorize(description, amount)
        
        # Validate category
        if not self.category_manager.get_category(category_id):
            raise ValueError(f"Category not found: {category_id}")
        
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
            recurring_frequency=recurring_frequency,
            destination_account_id=destination_account_id if type_str == TransactionType.TRANSFER.value else None
        )
        
        self._transactions.append(transaction)
        self._save_transactions()
        
        # Update account balance
        self._update_account_balance(account_id, amount, type_str, destination_account_id)
        
        logger.info(f"Created transaction: {transaction.description} ({transaction.amount})")
        return transaction
    
    def update_transaction(self, transaction_id: str, **kwargs) -> Transaction:
        """Update an existing transaction."""
        transaction = self.get_transaction(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        old_amount = transaction.amount
        old_type = transaction.type
        old_account_id = transaction.account_id
        old_destination_id = transaction.destination_account_id
        
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
                        raise ValueError(f"Category not found: {value}")
                elif key == 'type':
                    value = ValidationUtils.validate_transaction_type(value)
                elif key == 'destination_account_id':
                    if value and value == transaction.account_id:
                        raise ValueError("Source and destination must be different")
                    if value and not AccountManager(self.storage).get_account(value):
                        raise ValueError(f"Account not found: {value}")
                setattr(transaction, key, value)
        
        self._save_transactions()
        
        # Adjust account balances if relevant fields changed
        if (old_amount != transaction.amount or old_type != transaction.type or 
            old_account_id != transaction.account_id or 
            old_destination_id != transaction.destination_account_id):
            # Revert old effect
            if old_type == TransactionType.TRANSFER.value and old_destination_id:
                # Reverse old transfer
                self._update_account_balance(old_account_id, -old_amount, old_type, old_destination_id)
            else:
                self._update_account_balance(old_account_id, -old_amount, old_type)
            
            # Apply new effect
            self._update_account_balance(
                transaction.account_id, transaction.amount, transaction.type,
                transaction.destination_account_id
            )
        
        logger.info(f"Updated transaction: {transaction.description} ({transaction.id})")
        return transaction
    
    def delete_transaction(self, transaction_id: str) -> bool:
        """Delete a transaction."""
        transaction = self.get_transaction(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        # Reverse the balance effect
        if transaction.type == TransactionType.TRANSFER.value and transaction.destination_account_id:
            # For transfers, reverse both accounts
            self._update_account_balance(transaction.account_id, -transaction.amount, transaction.type, transaction.destination_account_id)
        else:
            self._update_account_balance(transaction.account_id, -transaction.amount, transaction.type)
        
        self._transactions = [t for t in self.transactions if t.id != transaction_id]
        self._save_transactions()
        
        logger.info(f"Deleted transaction: {transaction.description} ({transaction.id})")
        return True
    
    def _update_account_balance(self, account_id: str, amount: float, type_str: str, destination_account_id: str = None):
        """Update account balance after transaction."""
        account_manager = AccountManager(self.storage)
        
        # Handle transfers
        if type_str == TransactionType.TRANSFER.value and destination_account_id:
            # Debit source account
            source_account = account_manager.get_account(account_id)
            if source_account:
                source_account.balance -= amount
            # Credit destination account
            dest_account = account_manager.get_account(destination_account_id)
            if dest_account:
                dest_account.balance += amount
        else:
            # Handle income/expense
            account = account_manager.get_account(account_id)
            if account:
                if type_str == TransactionType.INCOME.value:
                    account.balance += amount
                elif type_str == TransactionType.EXPENSE.value:
                    account.balance -= amount
        
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
    
    def generate_recurring_transactions(self, up_to_date: str = None) -> List[Transaction]:
        """Generate recurring transactions up to the specified date."""
        if up_to_date is None:
            up_to_date = date.today().isoformat()
        
        up_to = datetime.fromisoformat(up_to_date)
        generated = []
        
        for transaction in self.transactions:
            if not transaction.is_recurring or not transaction.recurring_frequency:
                continue
            
            # Get the last occurrence of this recurring transaction
            last_date = datetime.fromisoformat(transaction.date)
            
            # Calculate next occurrence based on frequency
            if transaction.recurring_frequency == 'daily':
                next_date = last_date + timedelta(days=1)
            elif transaction.recurring_frequency == 'weekly':
                next_date = last_date + timedelta(weeks=1)
            elif transaction.recurring_frequency == 'monthly':
                # Add one month
                if last_date.month == 12:
                    next_date = last_date.replace(year=last_date.year + 1, month=1)
                else:
                    next_date = last_date.replace(month=last_date.month + 1)
            elif transaction.recurring_frequency == 'yearly':
                next_date = last_date.replace(year=last_date.year + 1)
            else:
                continue  # Unknown frequency
            
            # Generate transactions up to the target date
            while next_date <= up_to:
                new_trans = Transaction(
                    id=ValidationUtils.generate_secure_id(),
                    account_id=transaction.account_id,
                    type=transaction.type,
                    amount=transaction.amount,
                    category_id=transaction.category_id,
                    description=transaction.description,
                    date=next_date.isoformat(),
                    payee=transaction.payee,
                    notes=transaction.notes,
                    tags=transaction.tags.copy(),
                    is_recurring=True,
                    recurring_frequency=transaction.recurring_frequency,
                    destination_account_id=transaction.destination_account_id
                )
                self._transactions.append(new_trans)
                generated.append(new_trans)
                next_date = self._get_next_recurring_date(next_date, transaction.recurring_frequency)
            
            # Update the original transaction date to the last generated date
            if generated:
                transaction.date = generated[-1].date
        
        if generated:
            self._save_transactions()
            # Update account balances for new transactions
            for trans in generated:
                self._update_account_balance(trans.account_id, trans.amount, trans.type, trans.destination_account_id)
        
        return generated
    
    def _get_next_recurring_date(self, current: datetime, frequency: str) -> datetime:
        """Calculate the next date for a recurring transaction."""
        if frequency == 'daily':
            return current + timedelta(days=1)
        elif frequency == 'weekly':
            return current + timedelta(weeks=1)
        elif frequency == 'monthly':
            if current.month == 12:
                return current.replace(year=current.year + 1, month=1)
            else:
                return current.replace(month=current.month + 1)
        elif frequency == 'yearly':
            return current.replace(year=current.year + 1)
        return current


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
            raise ValueError(f"Category not found: {category_id}")
        
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
            raise ValueError(f"Budget not found: {budget_id}")
        
        for key, value in kwargs.items():
            if hasattr(budget, key) and key not in ['id', 'created_at', 'spent']:
                if key == 'amount':
                    value = ValidationUtils.validate_amount(value)
                elif key == 'name':
                    value = ValidationUtils.sanitize_string(value, key, 100)
                elif key == 'period':
                    valid_periods = [p.value for p in BudgetPeriod]
                    if value not in valid_periods:
                        raise ValueError(f"Invalid period: must be {', '.join(valid_periods)}")
                setattr(budget, key, value)
        
        self._save_budgets()
        logger.info(f"Updated budget: {budget.name} ({budget.id})")
        return budget
    
    def delete_budget(self, budget_id: str) -> bool:
        """Delete a budget."""
        budget = self.get_budget(budget_id)
        if not budget:
            raise ValueError(f"Budget not found: {budget_id}")
        
        self._budgets = [b for b in self.budgets if b.id != budget_id]
        self._save_budgets()
        logger.info(f"Deleted budget: {budget.name} ({budget.id})")
        return True
    
    def calculate_spent(self, budget_id: str) -> float:
        """Calculate actual spending against a budget."""
        budget = self.get_budget(budget_id)
        if not budget:
            raise ValueError(f"Budget not found: {budget_id}")
        
        # Get date range based on budget period
        start_date = datetime.fromisoformat(budget.start_date)
        end_date = budget.end_date or date.today().isoformat()
        
        # Adjust end_date based on period if no explicit end_date
        if not budget.end_date:
            end_date = self._get_period_end_date(start_date, budget.period)
        
        end = datetime.fromisoformat(end_date)
        
        transactions = self.transaction_manager.get_transactions_by_category(budget.category_id)
        transactions = [t for t in transactions 
                        if start_date <= datetime.fromisoformat(t.date) <= end]
        
        return sum(t.amount for t in transactions if t.type == TransactionType.EXPENSE.value)
    
    def _get_period_end_date(self, start: datetime, period: str) -> datetime:
        """Calculate the end date for a budget period."""
        if period == BudgetPeriod.WEEKLY.value:
            return start + timedelta(weeks=1)
        elif period == BudgetPeriod.MONTHLY.value:
            if start.month == 12:
                return start.replace(year=start.year + 1, month=1) - timedelta(days=1)
            else:
                return start.replace(month=start.month + 1) - timedelta(days=1)
        elif period == BudgetPeriod.QUARTERLY.value:
            # Add 3 months
            month = start.month + 2
            year = start.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            return start.replace(year=year, month=month) - timedelta(days=1)
        elif period == BudgetPeriod.YEARLY.value:
            return start.replace(year=start.year + 1) - timedelta(days=1)
        return start + timedelta(days=30)  # Default to 30 days
    
    def update_budget_spending(self, budget_id: str) -> Budget:
        """Update the spent amount for a budget."""
        budget = self.get_budget(budget_id)
        if not budget:
            raise ValueError(f"Budget not found: {budget_id}")
        
        budget.spent = self.calculate_spent(budget_id)
        self._save_budgets()
        return budget
    
    def get_budget_status(self, budget_id: str) -> Dict[str, Any]:
        """Get detailed budget status including alerts."""
        budget = self.get_budget(budget_id)
        if not budget:
            raise ValueError(f"Budget not found: {budget_id}")
        
        # Update spent amount
        budget = self.update_budget_spending(budget_id)
        
        percentage = (budget.spent / budget.amount * 100) if budget.amount >0 else 0
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
            raise ValueError(f"Alert not found: {alert_id}")
        
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
                # Check for duplicate alerts in last 24 hours
                if not self._has_recent_alert(AlertType.LOW_BALANCE.value, {'account_id': account.id}):
                    new_alerts.append(
                        self.create_alert(
                            type_str=AlertType.LOW_BALANCE.value,
                            message=f"Low balance alert: {account.name} has {account.balance:.2f} {account.currency}",
                            severity='warning',
                            data={'account_id': account.id, 'balance': account.balance}
                        )
                    )
        return new_alerts
    
    def _has_recent_alert(self, alert_type: str, data_filter: Dict, hours: int = 24) -> bool:
        """Check if a similar alert was created in the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        for alert in self.alerts:
            if (alert.type == alert_type and 
                alert.created_at >= cutoff.isoformat() and
                data_filter.items() <= alert.data.items()):
                return True
        return False


class UserManager:
    """Manages user authentication and registration."""
    
    def __init__(self, storage: DataStorage = None):
        """Initialize the user manager."""
        self.storage = storage or DataStorage()
        self._users = None
    
    @property
    def users(self) -> List[Dict]:
        """Get all users."""
        if self._users is None:
            self._load_users()
        return self._users
    
    def _load_users(self):
        """Load users from storage."""
        self._users = self.storage.get_users()
    
    def _save_users(self):
        """Save users to storage."""
        self.storage.save_users(self._users)
    
    def register(self, username: str, password: str, email: str = None) -> Dict:
        """Register a new user."""
        username = ValidationUtils.sanitize_string(username, "username", 50).lower()
        email = ValidationUtils.validate_email(email) if email else None
        
        # Check if user already exists
        if any(u.get('username') == username for u in self.users):
            raise ValueError("Username already exists")
        
        # Hash password
        password_hash, salt = ValidationUtils.hash_password(password)
        
        user = {
            'id': ValidationUtils.generate_secure_id(),
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'salt': salt,
            'created_at': datetime.now().isoformat(),
            'is_active': True
        }
        
        self._users.append(user)
        self._save_users()
        
        logger.info(f"Registered new user: {username}")
        return {'id': user['id'], 'username': user['username'], 'email': user.get('email')}
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate a user."""
        username = username.lower().strip()
        
        user = next((u for u in self.users if u.get('username') == username), None)
        if not user:
            return None
        
        if not user.get('is_active', True):
            raise PermissionError("Account is deactivated")
        
        if ValidationUtils.verify_password(password, user['password_hash'], user['salt']):
            return {'id': user['id'], 'username': user['username'], 'email': user.get('email')}
        
        return None
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        return next((u for u in self.users if u.get('id') == user_id), None)
    
    def update_user(self, user_id: str, **kwargs) -> Dict:
        """Update user information."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        for key, value in kwargs.items():
            if key in ['email', 'is_active'] and key in user:
                if key == 'email':
                    value = ValidationUtils.validate_email(value)
                user[key] = value
        
        self._save_users()
        return {'id': user['id'], 'username': user['username'], 'email': user.get('email')}
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Change user password."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        if not ValidationUtils.verify_password(old_password, user['password_hash'], user['salt']):
            raise ValueError("Invalid current password")
        
        password_hash, salt = ValidationUtils.hash_password(new_password)
        user['password_hash'] = password_hash
        user['salt'] = salt
        
        self._save_users()
        return True
