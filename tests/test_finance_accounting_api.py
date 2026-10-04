"""Tests for the ledger, compliance, forecast and statement API endpoints."""

import hashlib
import json

import pytest

from .conftest import authenticate


def _post(client, url, payload=None):
    return client.post(url, data=json.dumps(payload or {}),
                       content_type="application/json")


def _put(client, url, payload):
    return client.put(url, data=json.dumps(payload), content_type="application/json")


@pytest.fixture()
def account(client, request):
    """An authenticated client with a bank account.

    Uses a username unique to the test so data never leaks between tests, and
    authenticates once so tests using this fixture must not authenticate again.
    """
    unique = hashlib.sha1(request.node.name.encode()).hexdigest()[:8]
    authenticate(client, f'acct_{unique}')
    resp = _post(client, "/api/finance/account",
                 {"name": "Cheque", "type": "checking",
                  "initial_balance": 50000, "currency": "ZAR"})
    return resp.get_json()['account']['id']


class TestContactEndpoints:
    def test_create_and_search(self, client, app_instance):
        authenticate(client, 'fin_contact_1')
        resp = _post(client, "/api/finance/contact",
                     {"name": "Acme Ltd", "role": "customer",
                      "contact_person": "Jane", "email": "jane@acme.test"})
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()['contact']['name'] == "Acme Ltd"

        _post(client, "/api/finance/contact",
              {"name": "Steelworks", "role": "supplier"})

        found = client.get("/api/finance/contacts?q=acme").get_json()
        assert len(found['contacts']) == 1

        suppliers = client.get("/api/finance/contacts?role=supplier").get_json()
        assert [c['name'] for c in suppliers['contacts']] == ["Steelworks"]

    def test_duplicate_name_rejected(self, client, app_instance):
        authenticate(client, 'fin_contact_2')
        _post(client, "/api/finance/contact", {"name": "Acme"})
        resp = _post(client, "/api/finance/contact", {"name": "Acme"})
        assert resp.status_code == 400
        assert 'already exists' in resp.get_json()['message']

    def test_update(self, client, app_instance):
        authenticate(client, 'fin_contact_3')
        contact = _post(client, "/api/finance/contact",
                        {"name": "Acme"}).get_json()['contact']
        resp = _put(client, f"/api/finance/contact/{contact['id']}",
                    {"phone": "0111234567"})
        assert resp.status_code == 200
        assert resp.get_json()['contact']['phone'] == "0111234567"

    def test_delete_blocked_while_invoice_open(self, client, app_instance, account):
        contact = _post(client, "/api/finance/contact",
                        {"name": "Acme"}).get_json()['contact']
        _post(client, "/api/finance/receivable", {
            "contact_id": contact['id'], "amount": 5000,
            "issue_date": "2026-01-10", "account_id": account,
        })
        resp = client.delete(f"/api/finance/contact/{contact['id']}")
        assert resp.status_code == 400
        assert 'open ledger entries' in resp.get_json()['message']


class TestReceivableEndpoints:
    def test_create_invoice_and_settle(self, client, app_instance, account):
        contact = _post(client, "/api/finance/contact",
                        {"name": "Acme"}).get_json()['contact']

        created = _post(client, "/api/finance/receivable", {
            "contact_id": contact['id'], "amount": 20000,
            "issue_date": "2026-01-10", "account_id": account,
            "description": "Consulting",
        })
        assert created.status_code == 200, created.get_json()
        entry = created.get_json()['receivable']
        assert entry['due_date'] == "2026-02-09"

        paid = _post(client, f"/api/finance/receivable/{entry['id']}/payment", {
            "amount": 20000, "date": "2026-01-20",
        })
        assert paid.status_code == 200, paid.get_json()
        assert paid.get_json()['data']['settled'] is True

        ledger = client.get("/api/finance/ledger?as_of=2026-01-31").get_json()
        assert ledger['data']['receivable_totals']['outstanding'] == 0

    def test_overpayment_rejected(self, client, app_instance, account):
        contact = _post(client, "/api/finance/contact",
                        {"name": "Acme"}).get_json()['contact']
        entry = _post(client, "/api/finance/receivable", {
            "contact_id": contact['id'], "amount": 1000,
            "issue_date": "2026-01-10", "account_id": account,
        }).get_json()['receivable']

        resp = _post(client, f"/api/finance/receivable/{entry['id']}/payment",
                     {"amount": 2000, "date": "2026-01-20"})
        assert resp.status_code == 400

    def test_write_off_clears_balance(self, client, app_instance, account):
        contact = _post(client, "/api/finance/contact",
                        {"name": "Acme"}).get_json()['contact']
        entry = _post(client, "/api/finance/receivable", {
            "contact_id": contact['id'], "amount": 1000,
            "issue_date": "2026-01-10", "account_id": account,
        }).get_json()['receivable']

        resp = _post(client, f"/api/finance/receivable/{entry['id']}/write-off",
                     {"reason": "customer dissolved"})
        assert resp.status_code == 200, resp.get_json()
        ledger = client.get("/api/finance/ledger").get_json()
        assert ledger['data']['receivable_totals']['outstanding'] == 0

    def test_missing_contact_returns_400(self, client, app_instance, account):
        resp = _post(client, "/api/finance/receivable", {
            "contact_id": "nope", "amount": 100,
            "issue_date": "2026-01-10", "account_id": account,
        })
        assert resp.status_code == 400
        assert 'Contact not found' in resp.get_json()['message']


class TestPayableEndpoints:
    def test_create_bill_and_pay(self, client, app_instance, account):
        contact = _post(client, "/api/finance/contact",
                        {"name": "Steelworks", "role": "supplier"}
                        ).get_json()['contact']
        entry = _post(client, "/api/finance/payable", {
            "contact_id": contact['id'], "amount": 8000,
            "issue_date": "2026-01-08", "account_id": account,
            "description": "Raw material",
        }).get_json()['payable']

        resp = _post(client, f"/api/finance/payable/{entry['id']}/payment",
                     {"amount": 8000, "date": "2026-01-20"})
        assert resp.status_code == 200, resp.get_json()
        ledger = client.get("/api/finance/ledger").get_json()
        assert ledger['data']['payable_totals']['outstanding'] == 0


class TestComplianceEndpoints:
    def test_overview_shape(self, client, app_instance, account):
        authenticate(client, 'fin_comp_1')
        _post(client, "/api/finance/transaction", {
            "account_id": account, "type": "income", "amount": 100000,
            "category_id": "inc_other", "date": "2026-01-20",
        })
        resp = client.get("/api/finance/compliance?as_of=2026-01-31")
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()['data']
        assert set(data) == {'as_of', 'profile', 'tax', 'payroll', 'structuring'}

    def test_entity_profile_update(self, client, app_instance):
        authenticate(client, 'fin_comp_2')
        resp = _post(client, "/api/finance/entity-profile", {
            "registered_name": "Acme Trading", "entity_type": "private_company",
            "vat_registered": True,
        })
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()['profile']['registered_name'] == "Acme Trading"

    def test_entity_profile_rejects_unknown_field(self, client, app_instance):
        authenticate(client, 'fin_comp_3')
        resp = _post(client, "/api/finance/entity-profile",
                     {"company_name": "Acme Trading"})
        assert resp.status_code == 400
        assert 'Unknown profile field' in resp.get_json()['message']

    def test_tax_schedule_seeding_is_idempotent(self, client, app_instance):
        authenticate(client, 'fin_comp_4')
        _post(client, "/api/finance/entity-profile", {"vat_registered": True})

        schedule = client.get("/api/finance/tax-schedule").get_json()['data']
        first = _post(client, "/api/finance/tax-schedule/seed").get_json()['data']
        second = _post(client, "/api/finance/tax-schedule/seed").get_json()['data']

        assert first['created'] > 0
        assert second['created'] == 0

        records = client.get("/api/finance/compliance").get_json()['data']['tax']['records']
        assert len(records) == first['created']
        assert len(schedule['periods']) >= first['created']

    def test_tax_record_lifecycle(self, client, app_instance):
        authenticate(client, 'fin_comp_5')
        created = _post(client, "/api/finance/tax", {
            "tax_type": "vat", "period_start": "2026-01-01",
            "period_end": "2026-01-31", "due_date": "2026-02-28",
            "taxable_amount": 100000, "tax_amount": 15000,
        })
        assert created.status_code == 200, created.get_json()
        record = created.get_json()['tax']

        paid = _post(client, f"/api/finance/tax/{record['id']}/status",
                     {"status": "paid", "paid_date": "2026-02-28"})
        assert paid.status_code == 200, paid.get_json()
        assert paid.get_json()['tax']['status'] == "paid"

    def test_vat_estimate(self, client, app_instance, account):
        _post(client, "/api/finance/transaction", {
            "account_id": account, "type": "income", "amount": 150000,
            "category_id": "inc_other", "date": "2026-01-20",
        })
        _post(client, "/api/finance/transaction", {
            "account_id": account, "type": "expense", "amount": 30000,
            "category_id": "exp_food", "date": "2026-01-22",
        })
        resp = client.get("/api/finance/vat-estimate?start=2026-01-01&end=2026-01-31")
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()['data']['net_vat_payable'] == 18000

    def test_payroll_run_lifecycle(self, client, app_instance):
        authenticate(client, 'fin_comp_7')
        created = _post(client, "/api/finance/payroll", {
            "period_start": "2026-01-01", "period_end": "2026-01-31",
            "pay_date": "2026-01-30", "gross_pay": 80000,
            "paye": 10000, "uif": 1000, "sdl": 500, "employee_count": 4,
        })
        assert created.status_code == 200, created.get_json()
        run = created.get_json()['payroll']

        updated = _put(client, f"/api/finance/payroll/{run['id']}",
                       {"status": "processed"})
        assert updated.status_code == 200, updated.get_json()
        assert updated.get_json()['payroll']['status'] == "processed"

        assert client.delete(
            f"/api/finance/payroll/{run['id']}").status_code == 200

    def test_payroll_rejects_impossible_deductions(self, client, app_instance):
        authenticate(client, 'fin_comp_8')
        resp = _post(client, "/api/finance/payroll", {
            "period_start": "2026-01-01", "period_end": "2026-01-31",
            "pay_date": "2026-01-30", "gross_pay": 1000, "paye": 2000,
        })
        assert resp.status_code == 400


class TestForecastEndpoints:
    def test_create_and_project(self, client, app_instance, account):
        for month in ('2026-01-10', '2026-02-10', '2026-03-10'):
            _post(client, "/api/finance/transaction", {
                "account_id": account, "type": "income", "amount": 100000,
                "category_id": "inc_other", "date": month,
            })
            _post(client, "/api/finance/transaction", {
                "account_id": account, "type": "expense", "amount": 40000,
                "category_id": "exp_food", "date": month, "payee": "Shop",
            })

        created = _post(client, "/api/finance/forecast", {
            "name": "Base", "projection_months": 6, "baseline_months": 3,
            "income_growth_pct": 0, "expense_growth_pct": 0,
        })
        assert created.status_code == 200, created.get_json()
        scenario = created.get_json()['scenario']

        projected = _post(
            client, f"/api/finance/forecast/{scenario['id']}/project",
            {"as_of": "2026-03-31"})
        assert projected.status_code == 200, projected.get_json()
        summary = projected.get_json()['data']['summary']
        assert len(projected.get_json()['data']['months']) == 6
        assert summary['reading']

    def test_overrides_do_not_mutate_saved_scenario(self, client, app_instance):
        authenticate(client, 'fin_fc_2')
        scenario = _post(client, "/api/finance/forecast", {
            "name": "Base", "projection_months": 12,
        }).get_json()['scenario']

        _post(client, f"/api/finance/forecast/{scenario['id']}/project",
              {"projection_months": 3, "as_of": "2026-03-31"})

        listed = client.get("/api/finance/forecast").get_json()['scenarios']
        saved = next(s for s in listed if s['id'] == scenario['id'])
        assert saved['projection_months'] == 12

    def test_duplicate_scenario_name_rejected(self, client, app_instance):
        authenticate(client, 'fin_fc_3')
        _post(client, "/api/finance/forecast", {"name": "Base"})
        resp = _post(client, "/api/finance/forecast", {"name": "Base"})
        assert resp.status_code == 400

    def test_unknown_scenario_returns_400(self, client, app_instance):
        authenticate(client, 'fin_fc_4')
        resp = _post(client, "/api/finance/forecast/nope/project", {})
        assert resp.status_code == 400


class TestStatementEndpoints:
    def test_money_position_answers_five_questions(self, client, app_instance, account):
        contact = _post(client, "/api/finance/contact",
                        {"name": "Acme"}).get_json()['contact']
        _post(client, "/api/finance/receivable", {
            "contact_id": contact['id'], "amount": 120000,
            "issue_date": "2026-01-10", "account_id": account,
        })
        _post(client, "/api/finance/transaction", {
            "account_id": account, "type": "income", "amount": 50000,
            "category_id": "inc_other", "date": "2026-01-15",
        })
        _post(client, "/api/finance/transaction", {
            "account_id": account, "type": "expense", "amount": 20000,
            "category_id": "exp_food", "date": "2026-01-16",
        })

        resp = client.get(
            "/api/finance/money-position?start=2026-01-01&end=2026-01-31")
        assert resp.status_code == 200, resp.get_json()
        answers = {q['key']: q['amount']
                   for q in resp.get_json()['data']['questions']}
        assert answers['came_in'] == 50000
        assert answers['went_out'] == 20000
        assert answers['owed'] == 120000
        assert answers['actual_profit'] == 150000

    def test_every_statement_type_builds(self, client, app_instance):
        authenticate(client, 'fin_st_2')
        for report in ('profit_loss', 'balance_sheet', 'cash_flow',
                       'expense_analysis', 'records_health', 'funding_readiness'):
            resp = client.get(
                f"/api/finance/statement?type={report}"
                "&start=2026-01-01&end=2026-01-31")
            assert resp.status_code == 200, (report, resp.get_json())
            assert resp.get_json()['data']['report_type'] == report

    def test_unknown_statement_type_returns_400(self, client, app_instance):
        authenticate(client, 'fin_st_3')
        resp = client.get("/api/finance/statement?type=nope"
                          "&start=2026-01-01&end=2026-01-31")
        assert resp.status_code == 400
        assert 'Unknown report type' in resp.get_json()['message']

    def test_statements_carry_a_basis_note(self, client, app_instance):
        authenticate(client, 'fin_st_4')
        for report in ('profit_loss', 'balance_sheet', 'cash_flow'):
            resp = client.get(f"/api/finance/statement?type={report}"
                              "&start=2026-01-01&end=2026-01-31")
            assert resp.get_json()['data']['basis_note']


class TestPerUserIsolation:
    def test_ledger_is_per_user(self, client, app_instance):
        authenticate(client, 'fin_iso_1')
        account = _post(client, "/api/finance/account", {
            "name": "Cheque", "type": "checking",
            "initial_balance": 0, "currency": "ZAR",
        }).get_json()['account']['id']
        contact = _post(client, "/api/finance/contact",
                        {"name": "Acme"}).get_json()['contact']
        _post(client, "/api/finance/receivable", {
            "contact_id": contact['id'], "amount": 5000,
            "issue_date": "2026-01-10", "account_id": account,
        })
        assert client.get("/api/finance/ledger").get_json()['data'][
            'receivable_totals']['outstanding'] == 5000

        client.get("/api/auth/logout")
        authenticate(client, 'fin_iso_2')
        other = client.get("/api/finance/ledger").get_json()['data']
        assert other['receivable_totals']['outstanding'] == 0
        assert other['contacts'] == []

    def test_endpoints_require_authentication(self, client, app_instance):
        for url in ('/api/finance/ledger', '/api/finance/compliance',
                    '/api/finance/contacts', '/api/finance/forecast'):
            resp = client.get(url)
            assert resp.status_code == 401, (url, resp.status_code)
