"""Tests for the ledger, compliance and statement modules."""

import pytest
from datetime import date

from finance_core.storage import DataStorage
from finance_core.managers import CategoryManager, AccountManager, TransactionManager
from finance_core.ledger import ContactManager, ReceivableManager, PayableManager
from finance_core.compliance import (
    TaxManager, PayrollManager, EntityManager, ForecastManager
)
from finance_core.statements import StatementBuilder
from finance_core import periods


@pytest.fixture()
def books(tmp_path):
    """A fully wired set of finance managers on throwaway storage."""
    storage = DataStorage(str(tmp_path / 'data'))
    cm = CategoryManager(storage)
    am = AccountManager(storage)
    tm = TransactionManager(storage, cm, am)
    ct = ContactManager(storage)
    rm = ReceivableManager(storage, ct, tm)
    pm = PayableManager(storage, ct, tm)
    em = EntityManager(storage)
    bank = am.create_account('Cheque', 'checking', 50000.0, 'ZAR')
    return {
        'storage': storage, 'cm': cm, 'am': am, 'tm': tm,
        'ct': ct, 'rm': rm, 'pm': pm, 'em': em,
        'tax': TaxManager(storage, tm, em),
        'payroll': PayrollManager(storage),
        'forecast': ForecastManager(storage, tm, am),
        'bank': bank,
    }


@pytest.fixture()
def builder(books):
    return StatementBuilder(
        transaction_manager=books['tm'], account_manager=books['am'],
        receivable_manager=books['rm'], payable_manager=books['pm'],
        category_manager=books['cm'], tax_manager=books['tax'],
        payroll_manager=books['payroll'], entity_manager=books['em'],
    )


def spend(b, amount, date_str, category='exp_food', desc='Costs', payee=''):
    return b['tm'].create_transaction(
        b['bank'].id, 'expense', amount, category, desc,
        date_str=date_str, payee=payee)


def earn(b, amount, date_str, desc='Sales', category='inc_other'):
    return b['tm'].create_transaction(
        b['bank'].id, 'income', amount, category, desc, date_str=date_str)


class TestContacts:
    def test_duplicate_name_rejected(self, books):
        books['ct'].create_contact('Acme', 'customer')
        with pytest.raises(ValueError, match='already exists'):
            books['ct'].create_contact('acme', 'customer')

    def test_search_by_role_and_text(self, books):
        books['ct'].create_contact('Acme Ltd', 'customer', contact_person='Jane')
        books['ct'].create_contact('Steelworks', 'supplier', contact_person='John')
        assert len(books['ct'].search_contacts('acme')) == 1
        assert len(books['ct'].search_contacts(role='supplier')) == 1
        assert len(books['ct'].search_contacts(role='customer')) == 1
        assert len(books['ct'].search_contacts()) == 2

    def test_delete_refuses_while_entry_open(self, books):
        contact = books['ct'].create_contact('Acme', 'customer')
        books['rm'].create_receivable(
            contact.id, 5000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        with pytest.raises(ValueError, match='open ledger entries'):
            books['ct'].delete_contact(contact.id)

    def test_delete_refuses_while_history_exists(self, books):
        contact = books['ct'].create_contact('Acme', 'customer')
        entry = books['rm'].create_receivable(
            contact.id, 5000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        books['rm'].record_payment(entry.id, 5000, date_str='2026-01-20')
        with pytest.raises(ValueError, match='ledger entries'):
            books['ct'].delete_contact(contact.id)

    def test_delete_unused_contact(self, books):
        contact = books['ct'].create_contact('Unused', 'supplier')
        assert books['ct'].delete_contact(contact.id) is True
        assert books['ct'].get_contact(contact.id) is None


class TestReceivables:
    def test_create_uses_default_terms(self, books):
        contact = books['ct'].create_contact('Acme', 'customer')
        entry = books['rm'].create_receivable(
            contact.id, 10000, issue_date='2026-01-10', account_id=books['bank'].id)
        assert entry.issue_date == '2026-01-10'
        assert entry.due_date == '2026-02-09'

    def test_partial_payments_accumulate(self, books):
        contact = books['ct'].create_contact('Acme', 'customer')
        entry = books['rm'].create_receivable(
            contact.id, 10000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        books['rm'].record_payment(entry.id, 4000, date_str='2026-01-20')
        books['rm'].record_payment(entry.id, 6000, date_str='2026-01-25')
        row = books['rm'].list_entries()[0]
        assert row['amount_paid'] == 10000
        assert row['outstanding'] == 0
        assert row['status'] == 'paid'

    def test_overpayment_rejected(self, books):
        contact = books['ct'].create_contact('Acme', 'customer')
        entry = books['rm'].create_receivable(
            contact.id, 10000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        with pytest.raises(ValueError):
            books['rm'].record_payment(entry.id, 10001, date_str='2026-01-20')

    def test_settlement_posts_bank_transaction(self, books):
        contact = books['ct'].create_contact('Acme', 'customer')
        before = books['am'].get_account(books['bank'].id).balance
        entry = books['rm'].create_receivable(
            contact.id, 10000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        books['rm'].record_payment(entry.id, 10000, date_str='2026-01-20')
        after = books['am'].get_account(books['bank'].id).balance
        assert round(after - before, 2) == 10000

    def test_settlement_transaction_is_tagged(self, books):
        """The accrual figures rely on this tag to avoid double counting."""
        contact = books['ct'].create_contact('Acme', 'customer')
        entry = books['rm'].create_receivable(
            contact.id, 10000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        result = books['rm'].record_payment(
            entry.id, 10000, date_str='2026-01-20')
        tags = result['transaction']['tags']
        assert 'settlement' in tags and 'receivable' in tags

    def test_amount_cannot_drop_below_paid(self, books):
        contact = books['ct'].create_contact('Acme', 'customer')
        entry = books['rm'].create_receivable(
            contact.id, 10000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        books['rm'].record_payment(entry.id, 6000, date_str='2026-01-20')
        with pytest.raises(ValueError, match='already paid'):
            books['rm'].update_receivable(entry.id, amount=5000)

    def test_rejected_edit_does_not_partially_apply(self, books):
        """A bad due_date must not leave a mutated amount behind."""
        contact = books['ct'].create_contact('Acme', 'customer')
        entry = books['rm'].create_receivable(
            contact.id, 100000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        with pytest.raises(ValueError, match='due_date'):
            books['rm'].update_receivable(
                entry.id, amount=50000, due_date='2025-01-01')
        stored = books['rm'].get_entry(entry.id)
        assert stored.amount == 100000
        assert stored.due_date == '2026-02-09'

    def test_overdue_status_and_aging(self, books):
        contact = books['ct'].create_contact('Acme', 'customer')
        books['rm'].create_receivable(
            contact.id, 10000, issue_date='2025-12-01', due_date='2025-12-31',
            account_id=books['bank'].id)
        ref = date(2026, 3, 1)
        row = books['rm'].list_entries(reference=ref)[0]
        assert row['status'] == 'overdue'
        assert row['days_overdue'] == 60
        aging = books['rm'].aging(ref)
        assert aging['total'] == 10000
        assert sum(bucket['amount'] for bucket in aging['buckets']) == 10000

    def test_write_off_clears_outstanding(self, books):
        contact = books['ct'].create_contact('Acme', 'customer')
        entry = books['rm'].create_receivable(
            contact.id, 10000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        books['rm'].write_off(entry.id, reason='customer dissolved')
        row = books['rm'].list_entries()[0]
        assert row['outstanding'] == 0
        assert row['status'] == 'written_off'

    def test_settlement_without_account_rejected(self, books):
        contact = books['ct'].create_contact('Acme', 'customer')
        entry = books['rm'].create_receivable(
            contact.id, 10000, issue_date='2026-01-10', due_date='2026-02-09')
        with pytest.raises(ValueError, match='account is required'):
            books['rm'].record_payment(entry.id, 10000, date_str='2026-01-20')

    def test_delete_refuses_when_part_paid(self, books):
        contact = books['ct'].create_contact('Acme', 'customer')
        entry = books['rm'].create_receivable(
            contact.id, 10000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        books['rm'].record_payment(entry.id, 4000, date_str='2026-01-20')
        with pytest.raises(ValueError):
            books['rm'].delete_receivable(entry.id)


class TestPayables:
    def test_payment_reduces_outstanding(self, books):
        contact = books['ct'].create_contact('Steel', 'supplier')
        entry = books['pm'].create_payable(
            contact.id, 8000, issue_date='2026-01-08', due_date='2026-02-07',
            account_id=books['bank'].id)
        books['pm'].record_payment(entry.id, 3000, date_str='2026-01-20')
        row = books['pm'].list_entries()[0]
        assert row['outstanding'] == 5000
        assert row['status'] == 'partial'

    def test_payment_debits_bank(self, books):
        contact = books['ct'].create_contact('Steel', 'supplier')
        before = books['am'].get_account(books['bank'].id).balance
        entry = books['pm'].create_payable(
            contact.id, 8000, issue_date='2026-01-08', due_date='2026-02-07',
            account_id=books['bank'].id)
        books['pm'].record_payment(entry.id, 8000, date_str='2026-01-20')
        after = books['am'].get_account(books['bank'].id).balance
        assert round(after - before, 2) == -8000

    def test_totals_split_billed_settled_outstanding(self, books):
        contact = books['ct'].create_contact('Steel', 'supplier')
        entry = books['pm'].create_payable(
            contact.id, 8000, issue_date='2026-01-08', due_date='2026-02-07',
            account_id=books['bank'].id)
        books['pm'].record_payment(entry.id, 3000, date_str='2026-01-20')
        totals = books['pm'].totals(date(2026, 1, 31))
        assert totals['billed'] == 8000
        assert totals['settled'] == 3000
        assert totals['outstanding'] == 5000


class TestPeriods:
    def test_default_year_end_is_february(self):
        assert periods.DEFAULT_YEAR_END_MONTH == 2

    def test_financial_year_bounds_march_to_february(self):
        start, end = periods.financial_year_bounds('2026-06-15')
        assert start == date(2026, 3, 1)
        assert end == date(2027, 2, 28)

    def test_leap_year_financial_year_end(self):
        _, end = periods.financial_year_bounds('2024-06-15')
        assert end == date(2025, 2, 28)

    def test_vat_periods_tile_the_year(self):
        found = periods.vat_periods(reference='2026-06-15', interval='bi_monthly')
        assert found[0]['period_start'] == '2026-03-01'
        assert found[-1]['period_end'] == '2027-02-28'
        for earlier, later in zip(found, found[1:]):
            gap = periods.add_days(periods.require_date(earlier['period_end']), 1)
            assert gap == periods.require_date(later['period_start'])

    def test_quarterly_vat_periods(self):
        found = periods.vat_periods(reference='2026-06-15', interval='quarterly')
        assert len(found) == 4

    def test_days_in_month_handles_short_months(self):
        assert periods.days_in_month(2026, 2) == 28
        assert periods.days_in_month(2024, 2) == 29
        assert periods.days_in_month(2026, 1) == 31

    def test_add_months_clamps_to_month_end(self):
        assert periods.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)

    def test_iter_months_count(self):
        months = list(periods.iter_months(date(2026, 3, 1), 4))
        assert [m.month for m in months] == [3, 4, 5, 6]

    def test_require_range_rejects_reversed_dates(self):
        with pytest.raises(ValueError):
            periods.require_range('2026-03-01', '2026-01-01')

    def test_require_date_rejects_garbage(self):
        with pytest.raises(ValueError):
            periods.require_date('not-a-date', 'due_date')


class TestTax:
    def test_vat_estimate_uses_rate(self, books):
        earn(books, 150000, '2026-01-20')
        spend(books, 30000, '2026-01-22')
        result = books['tax'].estimate_vat('2026-01-01', '2026-01-31')
        assert result['net_vat_payable'] == 18000
        assert result['is_estimated'] is True

    def test_only_overdue_records_counted_as_overdue(self, books):
        """A PAYE bill due in June must not inherit VAT's overdue status."""
        books['tax'].create_record(
            tax_type='vat', period_start='2026-01-01', period_end='2026-01-31',
            taxable_amount=100000, tax_amount=15000, due_date='2026-02-28')
        books['tax'].create_record(
            tax_type='paye', period_start='2026-01-01', period_end='2026-01-31',
            taxable_amount=100000, tax_amount=30000, due_date='2026-06-30')
        totals = books['tax'].totals_for_period(
            '2026-01-01', '2026-12-31', reference=date(2026, 3, 31))
        assert totals['outstanding_tax'] == 45000
        assert totals['overdue_tax'] == 15000
        assert totals['overdue_by_type'] == {'vat': 15000}

    def test_seeding_schedule_twice_is_idempotent(self, books):
        books['em'].update_profile(vat_registered=True)
        schedule = books['tax'].period_schedule(reference=date(2026, 6, 15))
        first = books['tax'].seed_schedule(schedule)
        count_after_first = len(books['tax'].list_records())
        second = books['tax'].seed_schedule(schedule)
        assert first['created'] > 0
        assert second['created'] == 0
        assert len(books['tax'].list_records()) == count_after_first

    def test_marking_paid_clears_obligation(self, books):
        record = books['tax'].create_record(
            tax_type='vat', period_start='2026-01-01', period_end='2026-01-31',
            taxable_amount=100000, tax_amount=15000, due_date='2026-02-28')
        books['tax'].mark_status(record.id, 'paid', paid_date='2026-02-28')
        totals = books['tax'].totals_for_period(
            '2026-01-01', '2026-03-31', reference=date(2026, 3, 31))
        assert totals['outstanding_tax'] == 0

    def test_rejects_invalid_tax_type(self, books):
        with pytest.raises(ValueError):
            books['tax'].create_record(
                tax_type='gift_tax', period_start='2026-01-01',
                period_end='2026-01-31', due_date='2026-02-28')


class TestPayroll:
    def test_employer_cost_and_net_pay(self, books):
        books['payroll'].create_run(
            '2026-01-01', '2026-01-31', '2026-01-30',
            gross_pay=80000, paye=10000, uif=1000, sdl=500, employee_count=4)
        row = books['payroll'].list_runs()[0]
        # Employer cost is gross plus employer-side additions only.
        assert row['employer_cost'] == 80500
        assert row['net_pay'] == 69000

    def test_employer_cost_includes_employer_uif_and_pension(self, books):
        books['payroll'].create_run(
            '2026-01-01', '2026-01-31', '2026-01-30',
            gross_pay=80000, sdl=500, employer_uif=200, employer_pension=1000)
        row = books['payroll'].list_runs()[0]
        assert row['employer_cost'] == 81700

    def test_rejects_deductions_above_gross(self, books):
        with pytest.raises(ValueError, match='cannot exceed gross pay'):
            books['payroll'].create_run(
                '2026-01-01', '2026-01-31', '2026-01-30',
                gross_pay=1000, paye=2000)

    def test_rejects_pay_date_before_period_start(self, books):
        with pytest.raises(ValueError, match='pay_date'):
            books['payroll'].create_run(
                '2026-01-01', '2026-01-31', '2025-12-31', gross_pay=1000)

    def test_allows_pay_date_on_first_day_of_period(self, books):
        books['payroll'].create_run(
            '2026-01-01', '2026-01-31', '2026-01-01', gross_pay=1000)

    def test_rejects_reversed_period(self, books):
        with pytest.raises(ValueError):
            books['payroll'].create_run(
                '2026-01-31', '2026-01-01', '2026-02-05', gross_pay=1000)

    def test_rejects_negative_employee_count(self, books):
        with pytest.raises(ValueError):
            books['payroll'].create_run(
                '2026-01-01', '2026-01-31', '2026-01-30',
                gross_pay=1000, employee_count=-1)


class TestEntityProfile:
    def test_blank_profile_for_new_user(self, books):
        assert books['em'].profile.registered_name == ''

    def test_update_and_persist(self, books):
        books['em'].update_profile(
            registered_name='Acme Trading', vat_registered=True)
        fresh = EntityManager(books['storage'])
        assert fresh.profile.registered_name == 'Acme Trading'
        assert fresh.profile.vat_registered is True

    def test_rejects_unknown_entity_type(self, books):
        with pytest.raises(ValueError):
            books['em'].update_profile(entity_type='llp')

    def test_rejects_unknown_field(self, books):
        """A stale field name must fail loudly, not save nothing."""
        with pytest.raises(ValueError, match='Unknown profile field'):
            books['em'].update_profile(company_name='Acme Trading')

    def test_rejects_out_of_range_year_end(self, books):
        with pytest.raises(ValueError):
            books['em'].update_profile(financial_year_end_month=13)

    def test_checklist_flags_missing_pieces(self, books):
        items = books['em'].structuring_checklist(books['am'])
        assert isinstance(items, list)
        keys = {item['key'] for item in items}
        assert {'registered_name', 'entity_type', 'registration_number'} <= keys


class TestForecast:
    def test_profitable_scenario_has_no_loss_month(self, books):
        for month, inc, exp in [('2026-01-05', 100000, 40000),
                                ('2026-02-05', 120000, 50000),
                                ('2026-03-05', 90000, 45000)]:
            earn(books, inc, month)
            spend(books, exp, month)
        scenario = books['forecast'].create_scenario(
            'Base', projection_months=6, baseline_months=3,
            income_growth_pct=0, expense_growth_pct=0)
        summary = books['forecast'].project(
            scenario.id, reference=date(2026, 3, 31))['summary']
        assert summary['first_loss_month'] is None
        assert summary['goes_negative'] is False
        assert 'Profitable every month' in summary['reading']

    def test_runway_scenario_reports_cash_out_month(self, books):
        for month, inc, exp in [('2026-01-05', 100000, 40000),
                                ('2026-02-05', 120000, 50000),
                                ('2026-03-05', 90000, 45000)]:
            earn(books, inc, month)
            spend(books, exp, month)
        scenario = books['forecast'].create_scenario(
            'Decline', projection_months=12, baseline_months=3,
            income_growth_pct=-40, expense_growth_pct=10)
        summary = books['forecast'].project(
            scenario.id, reference=date(2026, 3, 31))['summary']
        assert summary['goes_negative'] is True
        assert summary['goes_negative_from'] is not None
        assert 'Cash runs out' in summary['reading']

    def test_duplicate_scenario_name_rejected(self, books):
        books['forecast'].create_scenario('Base')
        with pytest.raises(ValueError, match='already exists'):
            books['forecast'].create_scenario('Base')

    def test_rejects_out_of_range_growth(self, books):
        with pytest.raises(ValueError):
            books['forecast'].create_scenario('Bad', income_growth_pct=900)


class TestProfitAndLoss:
    def test_cash_only_business_matches_on_both_bases(self, books, builder):
        earn(books, 100000, '2026-01-10')
        spend(books, 30000, '2026-01-12')
        report = builder.profit_and_loss('2026-01-01', '2026-01-31')
        assert report['cash_basis']['net_profit'] == 70000
        assert report['accrual_basis']['net_profit'] == 70000

    def test_credit_sale_lifts_accrual_above_cash(self, books, builder):
        contact = books['ct'].create_contact('Acme', 'customer')
        books['rm'].create_receivable(
            contact.id, 120000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        spend(books, 20000, '2026-01-12')
        report = builder.profit_and_loss('2026-01-01', '2026-01-31')
        assert report['cash_basis']['net_profit'] == -20000
        assert report['accrual_basis']['net_profit'] == 100000

    def test_settlement_in_same_period_counted_once(self, books, builder):
        """The double-count trap: invoice raised and settled in one month."""
        contact = books['ct'].create_contact('Acme', 'customer')
        entry = books['rm'].create_receivable(
            contact.id, 200000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        books['rm'].record_payment(entry.id, 200000, date_str='2026-01-20')
        spend(books, 50000, '2026-01-15')
        report = builder.profit_and_loss('2026-01-01', '2026-01-31')
        assert report['cash_basis']['net_profit'] == 150000
        assert report['accrual_basis']['net_profit'] == 150000

    def test_supplier_bill_settled_in_period_counted_once(self, books, builder):
        contact = books['ct'].create_contact('Steel', 'supplier')
        entry = books['pm'].create_payable(
            contact.id, 80000, issue_date='2026-01-08', due_date='2026-02-07',
            account_id=books['bank'].id)
        books['pm'].record_payment(entry.id, 80000, date_str='2026-01-20')
        report = builder.profit_and_loss('2026-01-01', '2026-01-31')
        assert report['accrual_basis']['net_profit'] == -80000

    def test_cost_of_sales_separated_from_overhead(self, books, builder):
        cogs = books['cm'].create_category('Cost of Sales', 'expense')
        earn(books, 100000, '2026-01-10')
        books['tm'].create_transaction(
            books['bank'].id, 'expense', 40000, cogs.id, 'Materials',
            date_str='2026-01-11')
        spend(books, 10000, '2026-01-12', category='exp_food')
        report = builder.profit_and_loss('2026-01-01', '2026-01-31')
        cash = report['cash_basis']
        assert cash['cost_of_sales'] == 40000
        assert cash['operating_expenses'] == 10000
        assert cash['gross_profit'] == 60000
        assert cash['net_profit'] == 50000
        assert report['cogs_categories'] == ['Cost of Sales']


class TestBalanceSheet:
    def test_balances_by_construction(self, books, builder):
        earn(books, 150000, '2026-01-20')
        contact = books['ct'].create_contact('Acme', 'customer')
        books['rm'].create_receivable(
            contact.id, 200000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        report = builder.balance_sheet('2026-01-31')
        assert report['checks']['balances'] is True
        assert report['assets']['accounts_receivable'] == 200000
        assert report['liabilities']['total_liabilities'] == 0

    def test_payables_are_liabilities(self, books, builder):
        contact = books['ct'].create_contact('Steel', 'supplier')
        books['pm'].create_payable(
            contact.id, 60000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        report = builder.balance_sheet('2026-01-31')
        assert report['liabilities']['accounts_payable'] == 60000
        assert report['checks']['balances'] is True

    def test_working_capital(self, books, builder):
        earn(books, 100000, '2026-01-20')
        contact = books['ct'].create_contact('Steel', 'supplier')
        books['pm'].create_payable(
            contact.id, 30000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        report = builder.balance_sheet('2026-01-31')
        # 50000 opening + 100000 income = 150000 current assets, less 30000 owed
        assert report['assets']['cash_and_bank'] == 150000
        assert report['equity']['working_capital'] == 120000


class TestCashFlow:
    def test_operating_split(self, books, builder):
        earn(books, 200000, '2026-02-10')
        spend(books, 45000, '2026-02-12')
        report = builder.cash_flow('2026-02-01', '2026-02-28')
        assert report['operating']['cash_in'] == 200000
        assert report['operating']['cash_out'] == 45000
        assert report['operating']['net'] == 155000
        assert report['net_change'] == 155000

    def test_opening_cash_derived_from_closing(self, books, builder):
        earn(books, 100000, '2026-02-10')
        report = builder.cash_flow('2026-02-01', '2026-02-28')
        assert round(report['closing_cash'] - report['opening_cash'], 2) == 100000

    def test_move_to_investment_is_investing_outflow(self, books, builder):
        portfolio = books['am'].create_account('Portfolio', 'investment', 0.0, 'ZAR')
        books['tm'].create_transaction(
            books['bank'].id, 'transfer', 30000, 'transfer', 'To portfolio',
            date_str='2026-02-05', destination_account_id=portfolio.id)
        report = builder.cash_flow('2026-02-01', '2026-02-28')
        assert report['investing']['net'] == -30000
        assert report['operating']['net'] == 0

    def test_move_to_savings_is_not_investing(self, books, builder):
        """Cash moved to savings is still cash, so it nets to nothing."""
        savings = books['am'].create_account('Savings', 'savings', 0.0, 'ZAR')
        books['tm'].create_transaction(
            books['bank'].id, 'transfer', 30000, 'transfer', 'To savings',
            date_str='2026-02-05', destination_account_id=savings.id)
        report = builder.cash_flow('2026-02-01', '2026-02-28')
        assert report['investing']['net'] == 0
        assert report['net_change'] == 0
        assert report['closing_cash'] == report['opening_cash'] == 50000


class TestMoneyPosition:
    def test_answers_the_five_questions(self, books, builder):
        contact = books['ct'].create_contact('Acme', 'customer')
        books['rm'].create_receivable(
            contact.id, 120000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        supplier = books['ct'].create_contact('Steel', 'supplier')
        books['pm'].create_payable(
            supplier.id, 40000, issue_date='2026-01-10', due_date='2026-02-09',
            account_id=books['bank'].id)
        earn(books, 50000, '2026-01-15')
        spend(books, 20000, '2026-01-16')
        report = builder.money_position('2026-01-01', '2026-01-31', reference=date(2026, 1, 31))
        answers = {q['key']: q['amount'] for q in report['questions']}
        assert answers['came_in'] == 50000
        assert answers['went_out'] == 20000
        assert answers['owe'] == 40000
        assert answers['owed'] == 120000
        assert answers['actual_profit'] == 110000

    def test_bases_are_labelled(self, books, builder):
        report = builder.money_position('2026-01-01', '2026-01-31')
        bases = {q['basis'] for q in report['questions']}
        assert {'cash', 'ledger', 'accrual'} <= bases


class TestExpenseAnalysis:
    def test_committed_versus_discretionary(self, books, builder):
        earn(books, 100000, '2026-02-01')
        books['tm'].create_transaction(
            books['bank'].id, 'expense', 30000, 'exp_housing', 'Rent',
            date_str='2026-02-01', is_recurring=True, recurring_frequency='monthly')
        spend(books, 15000, '2026-02-05', category='exp_food')
        report = builder.expense_analysis('2026-02-01', '2026-02-28')
        assert report['total_expenses'] == 45000
        assert report['committed_expenses'] == 30000
        assert report['discretionary_expenses'] == 15000

    def test_largest_expense_identified(self, books, builder):
        spend(books, 500, '2026-02-05', desc='Lunch')
        spend(books, 9000, '2026-02-10', desc='Laptop')
        report = builder.expense_analysis('2026-02-01', '2026-02-28')
        assert report['largest_expense']['description'] == 'Laptop'
        assert report['largest_expense']['amount'] == 9000

    def test_shares_sum_to_total(self, books, builder):
        spend(books, 25000, '2026-02-01', category='exp_housing')
        spend(books, 15000, '2026-02-05', category='exp_food')
        report = builder.expense_analysis('2026-02-01', '2026-02-28')
        assert sum(line['amount'] for line in report['by_category']) == 40000


class TestRecordsHealth:
    def test_well_kept_records_score_high(self, books, builder):
        earn(books, 100000, '2026-01-10')
        spend(books, 1000, '2026-01-11', category='exp_food',
              desc='Stationery', payee='Shop')
        report = builder.records_health(date(2026, 1, 31))
        assert report['score'] == 100
        assert report['band'] == 'good'
        assert report['issues'] == []

    def test_uncategorised_expense_is_critical(self, books, builder):
        """Deleting a category is the realistic way a transaction is orphaned."""
        category = books['cm'].create_category('One-off', 'expense')
        books['tm'].create_transaction(
            books['bank'].id, 'expense', 500, category.id, 'Mystery',
            date_str='2026-01-11')
        books['cm'].delete_category(category.id)
        report = builder.records_health(date(2026, 1, 31))
        failed = {issue['key']: issue for issue in report['issues']}
        assert 'category_coverage' in failed
        assert failed['category_coverage']['severity'] == 'critical'
        assert failed['category_coverage']['count'] == 1

    def test_expense_without_payee_is_flagged(self, books, builder):
        spend(books, 500, '2026-01-11', desc='Mystery', payee='')
        report = builder.records_health(date(2026, 1, 31))
        failed = {issue['key'] for issue in report['issues']}
        assert 'payee_recorded' in failed

    def test_description_counts_as_evidence(self, books, builder):
        """A description is the evidence the check is asking for."""
        spend(books, 500, '2026-01-11', desc='Stationery', payee='Shop')
        report = builder.records_health(date(2026, 1, 31))
        failed = {issue['key'] for issue in report['issues']}
        assert 'expense_evidence' not in failed

    def test_stale_bookkeeping_flagged(self, books, builder):
        earn(books, 100000, '2026-01-10')
        report = builder.records_health(date(2026, 6, 30))
        failed = {issue['key'] for issue in report['issues']}
        assert 'bookkeeping_current' in failed

    def test_every_issue_carries_a_hint(self, books, builder):
        report = builder.records_health(date(2026, 6, 30))
        for issue in report['issues']:
            assert issue['hint']


class TestFundingReadiness:
    def test_no_data_blocks_on_revenue(self, books, builder):
        report = builder.funding_readiness(date(2026, 3, 31), months=3)
        assert report['ready'] is False
        assert 'Revenue over the period' in report['blockers']

    def test_poor_records_block_readiness(self, books, builder):
        """Healthy money but sloppy records should still fail a funder."""
        category = books['cm'].create_category('One-off', 'expense')
        for month in ('2026-01-10', '2026-02-10', '2026-03-10'):
            earn(books, 100000, month)
            books['tm'].create_transaction(
                books['bank'].id, 'expense', 30000, category.id, 'Mystery',
                date_str=month, payee='')
        books['cm'].delete_category(category.id)
        report = builder.funding_readiness(date(2026, 3, 31), months=3)
        assert report['ready'] is False
        assert 'Records completeness' in report['blockers']

    def test_healthy_business_is_ready(self, books, builder):
        for month in ('2026-01-10', '2026-02-10', '2026-03-10'):
            earn(books, 100000, month)
            spend(books, 40000, month, desc='Supplies', payee='Shop')
        report = builder.funding_readiness(date(2026, 3, 31), months=3)
        assert report['blockers'] == []
        assert report['ready'] is True

    def test_metrics_carry_plain_readings(self, books, builder):
        earn(books, 100000, '2026-01-10')
        spend(books, 30000, '2026-01-12', category='exp_food',
              desc='Costs', payee='Shop')
        report = builder.funding_readiness(date(2026, 1, 31), months=3)
        for metric in report['metrics']:
            assert metric['reading']
            assert metric['status'] in ('good', 'warning', 'critical', 'info')

    def test_disclaimer_present(self, books, builder):
        report = builder.funding_readiness(date(2026, 1, 31))
        assert 'not a credit assessment' in report['disclaimer']


class TestCoreWiring:
    def test_finance_core_exposes_new_managers(self, tmp_path):
        from finance_core import create_finance_core

        core = create_finance_core(str(tmp_path / 'core'))
        assert core.contact_manager is not None
        assert core.receivable_manager is not None
        assert core.payable_manager is not None
        assert core.tax_manager is not None
        assert core.payroll_manager is not None
        assert core.entity_manager is not None
        assert core.forecast_manager is not None
        assert core.statement_builder is not None

    def test_ledger_overview_shape(self, tmp_path):
        from finance_core import create_finance_core

        core = create_finance_core(str(tmp_path / 'core'))
        overview = core.get_ledger_overview('2026-01-31')
        for key in ('receivables', 'payables', 'receivable_totals',
                    'payable_totals', 'receivable_aging', 'payable_aging'):
            assert key in overview

    def test_compliance_overview_shape(self, tmp_path):
        from finance_core import create_finance_core

        core = create_finance_core(str(tmp_path / 'core'))
        overview = core.get_compliance_overview('2026-01-31')
        assert set(overview) == {'as_of', 'profile', 'tax', 'payroll', 'structuring'}

    def test_all_report_types_build(self, tmp_path):
        from finance_core import create_finance_core

        core = create_finance_core(str(tmp_path / 'core'))
        for report in ('profit_loss', 'balance_sheet', 'cash_flow',
                       'expense_analysis', 'records_health', 'funding_readiness'):
            result = core.get_financial_statements(
                report, '2026-01-01', '2026-01-31')
            assert result['report_type'] == report

    def test_unknown_report_type_rejected(self, tmp_path):
        from finance_core import create_finance_core

        core = create_finance_core(str(tmp_path / 'core'))
        with pytest.raises(ValueError, match='Unknown report type'):
            core.get_financial_statements('nope', '2026-01-01', '2026-01-31')

    def test_clear_all_data_empties_every_collection(self, tmp_path):
        from finance_core import create_finance_core

        core = create_finance_core(str(tmp_path / 'core'))
        bank = core.account_manager.create_account('Cheque', 'checking', 1000.0, 'ZAR')
        contact = core.contact_manager.create_contact('Acme', 'customer')
        core.transaction_manager.create_transaction(
            bank.id, 'income', 5000, 'inc_other', 'Sales', date_str='2026-01-10')
        core.receivable_manager.create_receivable(
            contact.id, 2000, issue_date='2026-01-10', account_id=bank.id)
        core.entity_manager.update_profile(registered_name='Acme Trading')

        assert core.clear_all_data() is True
        assert core.transaction_manager.transactions == []
        assert core.account_manager.accounts == []
        assert core.contact_manager.contacts == []
        assert core.receivable_manager.list_entries() == []
        assert core.entity_manager.profile.registered_name == ''

    def test_clear_all_data_keeps_default_categories(self, tmp_path):
        from finance_core import create_finance_core

        core = create_finance_core(str(tmp_path / 'core'))
        before = len(core.category_manager.categories)
        core.clear_all_data()
        assert len(core.category_manager.categories) == before
