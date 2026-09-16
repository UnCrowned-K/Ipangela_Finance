import csv

import pytest
from finance_core import CategoryManager, AccountManager, TransactionManager


@pytest.fixture()
def managers(storage):
    cm = CategoryManager(storage)
    am = AccountManager(storage)
    tm = TransactionManager(storage, cm, am)
    return cm, am, tm


class TestAutoCategorize:
    def test_expense_keywords(self, managers):
        cm, _, _ = managers
        assert cm.auto_categorize('Grocery Store', 250.0, 'expense') == 'exp_food'
        assert cm.auto_categorize('Netflix subscription', 15.0, 'expense') == 'exp_entertainment'

    def test_income_keywords(self, managers):
        cm, _, _ = managers
        assert cm.auto_categorize('Salary deposit', 5000.0, 'income') == 'inc_salary'

    def test_unknown_expense(self, managers):
        cm, _, _ = managers
        assert cm.auto_categorize('Mystery charge', 99.0, 'expense') == 'exp_other'

    def test_unknown_income(self, managers):
        cm, _, _ = managers
        assert cm.auto_categorize('Mystery deposit', 99.0, 'income') == 'inc_other'

    def test_income_not_classified_as_expense(self, managers):
        cm, _, _ = managers
        assert cm.auto_categorize('Amazon refund', 20.0, 'income') != 'exp_shopping'

    def test_transfer(self, managers):
        cm, _, _ = managers
        assert cm.auto_categorize('Transfer to savings', 100.0, 'transfer') == 'transfer'


class TestManagers:
    def test_create_account_transaction_budget_alert(self, managers, storage):
        cm, am, tm = managers
        acc = am.create_account('Main', 'checking', 1000.0, 'ZAR')
        assert acc.id

        trans = tm.create_transaction(
            account_id=acc.id,
            type_str='expense',
            amount=100.0,
            category_id='exp_food',
            description='Lunch',
        )
        assert trans.id
        assert acc.balance == 900.0

        from finance_core import BudgetManager, AlertManager
        bm = BudgetManager(storage, tm)
        budget = bm.create_budget('Food', 'exp_food', 500.0)
        assert budget.id
        status = bm.get_budget_status(budget.id)
        assert status['spent'] == 100.0

        alm = AlertManager(storage, bm)
        alert = alm.create_alert('info', 'Test alert')
        assert alert.id
        assert alert.message == 'Test alert'

    def test_export_transactions_csv_sanitizes(self, managers, storage):
        cm, am, tm = managers
        acc = am.create_account('Main', 'checking', 1000.0, 'ZAR')
        tm.create_transaction(
            account_id=acc.id,
            type_str='expense',
            amount=50.0,
            category_id='exp_food',
            description='=CMD("calc")',
            notes='Normal note',
        )
        csv_out = tm.export_transactions_csv()
        rows = list(csv.DictReader(csv_out.splitlines()))
        assert rows, 'expected exported transactions'
        descriptions = [r['description'] for r in rows]
        assert '=CMD(calc)' not in descriptions
        assert "'=CMD(calc)" in descriptions
        assert 'Normal note' in [r['notes'] for r in rows]

    def test_export_transactions_csv_no_transactions(self, managers):
        cm, am, tm = managers
        csv_out = tm.export_transactions_csv()
        assert csv_out.startswith('id,date,type,amount,')