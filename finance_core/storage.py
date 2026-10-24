import os
import json
import logging
import threading
from datetime import datetime
from typing import Any, List, Optional, Tuple, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Loading, mutating and saving a file is one read-modify-write cycle spread
# over several calls, so the lock has to span the whole cycle in the caller.
# lock_for() hands out one lock per storage directory.
# shortcut: in-process only. Multiple worker processes can still lose updates;
# move to SQLite when that matters.
_dir_locks: Dict[str, threading.Lock] = {}
_dir_locks_guard = threading.Lock()


def lock_for(storage_dir: str) -> threading.Lock:
    """Return the process-wide lock guarding a storage directory."""
    key = os.path.normpath(storage_dir)
    with _dir_locks_guard:
        return _dir_locks.setdefault(key, threading.Lock())


class DataStorage:
    """Handles persistent data storage for the finance system."""
    
    def __init__(self, storage_dir: str = None):
        """Initialize the data storage."""
        if storage_dir is None:
            if 'VERCEL' in os.environ:
                storage_dir = '/tmp/data'
            else:
                storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
        
        self.storage_dir = os.path.normpath(storage_dir)
        self._ensure_directories()
        
        # Data files
        self.transactions_file = os.path.join(self.storage_dir, 'transactions.json')
        self.accounts_file = os.path.join(self.storage_dir, 'accounts.json')
        self.budgets_file = os.path.join(self.storage_dir, 'budgets.json')
        self.categories_file = os.path.join(self.storage_dir, 'categories.json')
        self.alerts_file = os.path.join(self.storage_dir, 'alerts.json')
        self.users_file = os.path.join(self.storage_dir, 'users.json')

        # Ledger, compliance and forecasting files
        self.contacts_file = os.path.join(self.storage_dir, 'contacts.json')
        self.receivables_file = os.path.join(self.storage_dir, 'receivables.json')
        self.payables_file = os.path.join(self.storage_dir, 'payables.json')
        self.tax_records_file = os.path.join(self.storage_dir, 'tax_records.json')
        self.payroll_runs_file = os.path.join(self.storage_dir, 'payroll_runs.json')
        self.entity_profile_file = os.path.join(self.storage_dir, 'entity_profile.json')
        self.forecasts_file = os.path.join(self.storage_dir, 'forecasts.json')
        self.login_attempts_file = os.path.join(self.storage_dir, 'login_attempts.json')
    
    def _ensure_directories(self):
        """Ensure storage directories exist."""
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create storage directory: {e}")
            raise Exception(f"Storage initialization failed: {e}")
    
    def _read_json(self, filepath: str, default: Any = None) -> Any:
        """Read JSON from a file, or return `default` when it does not exist.

        A file that exists but cannot be parsed is reported rather than
        treated as empty: returning the default would let the next save
        overwrite whatever the user had.
        """
        if not os.path.exists(filepath):
            return default
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Corrupt JSON in {filepath}: {e}")
            raise ValueError(f"Corrupt data file: {os.path.basename(filepath)}") from e
        except IOError as e:
            logger.error(f"Error reading {filepath}: {e}")
            return default
    
    def _write_json(self, filepath: str, data: Any) -> bool:
        """Write JSON atomically so an interrupted write cannot corrupt it."""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            tmp = f"{filepath}.tmp"
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, filepath)
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

    # Ledger
    def get_contacts(self) -> List[Dict]:
        return self._read_json(self.contacts_file, [])

    def save_contacts(self, contacts: List[Dict]) -> bool:
        return self._write_json(self.contacts_file, contacts)

    def get_receivables(self) -> List[Dict]:
        return self._read_json(self.receivables_file, [])

    def save_receivables(self, receivables: List[Dict]) -> bool:
        return self._write_json(self.receivables_file, receivables)

    def get_payables(self) -> List[Dict]:
        return self._read_json(self.payables_file, [])

    def save_payables(self, payables: List[Dict]) -> bool:
        return self._write_json(self.payables_file, payables)

    # Compliance
    def get_tax_records(self) -> List[Dict]:
        return self._read_json(self.tax_records_file, [])

    def save_tax_records(self, records: List[Dict]) -> bool:
        return self._write_json(self.tax_records_file, records)

    def get_payroll_runs(self) -> List[Dict]:
        return self._read_json(self.payroll_runs_file, [])

    def save_payroll_runs(self, runs: List[Dict]) -> bool:
        return self._write_json(self.payroll_runs_file, runs)

    def get_entity_profile(self) -> Optional[Dict]:
        """Return the stored business profile, or None when never saved."""
        return self._read_json(self.entity_profile_file, None)

    def save_entity_profile(self, profile: Dict) -> bool:
        return self._write_json(self.entity_profile_file, profile)

    # Forecasting
    def get_forecasts(self) -> List[Dict]:
        return self._read_json(self.forecasts_file, [])

    def save_forecasts(self, forecasts: List[Dict]) -> bool:
        return self._write_json(self.forecasts_file, forecasts)

    # Login rate limiting
    def get_login_attempts(self) -> Dict[str, List[float]]:
        return self._read_json(self.login_attempts_file, {})

    def save_login_attempts(self, attempts: Dict[str, List[float]]) -> bool:
        return self._write_json(self.login_attempts_file, attempts)

    #: Every file written by :class:`DataStorage`, used by backup and wipe.
    DATA_FILES = (
        'transactions.json', 'accounts.json', 'budgets.json',
        'categories.json', 'alerts.json', 'users.json',
        'contacts.json', 'receivables.json', 'payables.json',
        'tax_records.json', 'payroll_runs.json', 'entity_profile.json',
        'forecasts.json',
    )

    def backup_data(self, backup_dir: str = None) -> bool:
        """Create a backup of all data files."""
        if backup_dir is None:
            backup_dir = os.path.join(self.storage_dir, 'backups')
        
        try:
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            for filename in self.DATA_FILES:
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
    
    def import_transactions_csv(self, csv_content: str, account_id: str = None) -> Dict[str, Any]:
        """Import transactions from CSV content."""
        import csv
        from io import StringIO
        from finance_core.models import TransactionType
        from finance_core.managers import TransactionManager, CategoryManager, AccountManager
        
        result = {'created': 0, 'errors': []}
        
        try:
            reader = csv.DictReader(StringIO(csv_content))
            transaction_manager = TransactionManager(self)
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Expected columns: date, description, amount, type, category, payee
                    date_str = row.get('date', '').strip()
                    description = row.get('description', '').strip()
                    amount = float(row.get('amount', 0))
                    type_str = row.get('type', 'expense').strip().lower()
                    category_name = row.get('category', '').strip()
                    payee = row.get('payee', '').strip()
                    
                    # Find category by name
                    category_manager = CategoryManager(self)
                    category = next((c for c in category_manager.categories 
                                    if c.name.lower() == category_name.lower()), None)
                    category_id = category.id if category else None
                    
                    # Use provided account or find by name
                    trans_account_id = account_id
                    if not trans_account_id:
                        account_name = row.get('account', '').strip()
                        account_manager = AccountManager(self)
                        account = next((a for a in account_manager.accounts 
                                       if a.name.lower() == account_name.lower()), None)
                        trans_account_id = account.id if account else None
                    
                    if not trans_account_id:
                        result['errors'].append(f"Row {row_num}: No valid account")
                        continue
                    
                    transaction_manager.create_transaction(
                        account_id=trans_account_id,
                        type_str=type_str,
                        amount=amount,
                        category_id=category_id,
                        description=description,
                        date_str=date_str,
                        payee=payee
                    )
                    result['created'] += 1
                    
                except Exception as e:
                    result['errors'].append(f"Row {row_num}: {str(e)}")
            
            return result
        except Exception as e:
            result['errors'].append(f"CSV parsing error: {str(e)}")
            return result
