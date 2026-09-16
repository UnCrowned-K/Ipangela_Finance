"""Tests for finance API endpoints (categories, alerts, export) and per-user isolation."""

import json
import os

from .conftest import authenticate


def _post(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def test_category_create_and_list(client, app_instance):
    authenticate(client, 'fin_api_user1')
    resp = _post(client, "/api/finance/category",
                 {"name": "Coffee", "type": "expense", "color": "#a0522d"})
    assert resp.status_code == 200, resp.get_json()
    cat = resp.get_json()['category']
    assert cat['name'] == "Coffee"
    assert cat['is_system'] is False

    data = client.get("/api/finance/data").get_json()['data']
    assert any(c['name'] == "Coffee" for c in data['categories'])


def test_category_update(client, app_instance):
    authenticate(client, 'fin_api_user2')
    cat = _post(client, "/api/finance/category",
                {"name": "Groceries", "type": "expense"}).get_json()['category']
    resp = client.put(f"/api/finance/category/{cat['id']}",
                      data=json.dumps({"color": "#ff0000"}),
                      content_type="application/json")
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()['category']['color'] == "#ff0000"


def test_category_delete_removes_custom_category(client, app_instance):
    authenticate(client, 'fin_api_user3')
    cat = _post(client, "/api/finance/category",
                {"name": "Temp Cat", "type": "expense"}).get_json()['category']
    resp = client.delete(f"/api/finance/category/{cat['id']}")
    assert resp.status_code == 200, resp.get_json()
    data = client.get("/api/finance/data").get_json()['data']
    assert not any(c['name'] == "Temp Cat" for c in data['categories'])


def test_system_category_delete_hides_it(client, app_instance):
    authenticate(client, 'fin_api_user4')
    # 'exp_other' is a system category
    client.delete("/api/finance/category/exp_other")
    data = client.get("/api/finance/data").get_json()['data']
    assert not any(c['id'] == "exp_other" for c in data['categories'])


def test_alerts_roundtrip(client, app_instance):
    authenticate(client, 'fin_api_user5')
    # No alerts by default
    resp = client.get("/api/finance/alerts")
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True

    # Manually create an alert, then mark all read
    from finance_core import create_finance_core as factory
    with client.session_transaction() as sess:
        user_id = sess['user_id']
    storage_dir = os.path.join(app_instance.config['FINANCE_DATA_FOLDER'], user_id)
    core = factory(storage_dir)
    core.alert_manager.create_alert('test', 'Budget warning', severity='warning')
    core.alert_manager.create_alert('test', 'Low balance', severity='critical')

    alerts = client.get("/api/finance/alerts").get_json()['alerts']
    assert len(alerts) == 2
    assert all(a['is_read'] is False for a in alerts)

    resp = client.post("/api/finance/alerts/read")
    assert resp.get_json()['updated'] == 2
    alerts = client.get("/api/finance/alerts").get_json()['alerts']
    assert all(a['is_read'] is True for a in alerts)


def test_finance_export_json(client, app_instance):
    authenticate(client, 'fin_api_user6')
    _post(client, "/api/finance/account",
          {"name": "Savings", "type": "savings", "balance": 1000})
    resp = _post(client, "/api/finance/export", {"format": "json"})
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body['success'] is True
    assert any(a['name'] == "Savings" for a in body['data']['accounts'])


def test_finance_export_csv(client, app_instance):
    authenticate(client, 'fin_api_user7')
    resp = _post(client, "/api/finance/export/csv", {})
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()['success'] is True
    assert "date,type,amount,category" in resp.get_json()['data']


def create_account_authenticated(client, name):
    resp = _post(client, "/api/finance/account",
                 {"name": name, "type": "checking", "balance": 500})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()['account']


def test_finance_data_is_isolated_between_users(client, app_instance):
    authenticate(client, 'fin_api_user8')
    create_account_authenticated(client, "Private Account A")

    other = app_instance.test_client()
    authenticate(other, 'fin_api_user9')
    accounts = other.get("/api/finance/data").get_json()['data']['accounts']
    assert accounts == []
    budgets = other.get("/api/finance/data").get_json()['data']['budgets']
    assert budgets == []


def test_transactions_are_isolated_between_users(client, app_instance):
    authenticate(client, 'fin_api_user10')
    acct = create_account_authenticated(client, "Acct A")
    _post(client, "/api/finance/transaction",
          {"account_id": acct['id'], "type": "expense", "amount": 99,
           "description": "isolated txn"})

    other = app_instance.test_client()
    authenticate(other, 'fin_api_user11')
    txns = other.get("/api/finance/data").get_json()['data']['transactions']
    assert txns == []