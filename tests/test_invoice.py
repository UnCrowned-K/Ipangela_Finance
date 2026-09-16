"""Tests for invoice_core — verifying the fix for missing computed properties."""

import json
import os
import tempfile

import pytest

from invoice_core import (
    InvoiceCore, InvoicePDFGenerator, InvoiceEmailSender,
    LineItem, Invoice, ClientDetails, Currency, PaymentStatus,
)
from .conftest import authenticate


# ---------------------------------------------------------------------------
# Unit tests – invoice_core model properties
# ---------------------------------------------------------------------------

class TestLineItemProperties:
    def test_subtotal(self):
        item = LineItem(description="Widget", quantity=3, unit_price=100)
        assert item.subtotal == 300

    def test_discount_amount(self):
        item = LineItem(description="Widget", quantity=2, unit_price=200, discount_percent=10)
        # 2*200=400 subtotal, 10% = 40
        assert item.discount_amount == 40

    def test_tax_amount(self):
        item = LineItem(description="Widget", quantity=1, unit_price=1000, tax_percent=15)
        assert item.tax_amount == 150

    def test_total_with_discount_and_tax(self):
        item = LineItem(description="W", quantity=2, unit_price=100, discount_percent=10, tax_percent=15)
        # subtotal=200, discount=20, discounted=180, tax=27, total=207
        assert item.total == 207

    def test_to_dict_includes_computed_fields(self):
        item = LineItem(description="X", quantity=1, unit_price=50)
        d = item.to_dict()
        assert d['subtotal'] == 50
        assert d['discount_amount'] == 0
        assert d['tax_amount'] == 0
        assert d['total'] == 50


class TestInvoiceProperties:
    def _make_invoice(self, **overrides):
        client = ClientDetails(name="Test", email="test@example.com")
        raw_items = overrides.pop('line_items', [{"description": "S", "quantity": 1, "unit_price": 100, "tax_percent": 10}])
        items = [LineItem(**i) for i in raw_items]
        return Invoice(invoice_number="INV-001", client=client, line_items=items, **overrides)

    def test_subtotal(self):
        inv = self._make_invoice(line_items=[
            {"description": "A", "quantity": 2, "unit_price": 100},
            {"description": "B", "quantity": 1, "unit_price": 50},
        ])
        assert inv.subtotal == 250

    def test_total_discount(self):
        inv = self._make_invoice(line_items=[
            {"description": "A", "quantity": 1, "unit_price": 200, "discount_percent": 10},
        ])
        assert inv.total_discount == 20

    def test_total_tax(self):
        inv = self._make_invoice(line_items=[
            {"description": "A", "quantity": 1, "unit_price": 1000, "tax_percent": 15},
        ])
        assert inv.total_tax == 150

    def test_grand_total(self):
        inv = self._make_invoice(line_items=[
            {"description": "A", "quantity": 1, "unit_price": 1000, "discount_percent": 10, "tax_percent": 15},
        ])
        # subtotal=1000, discount=100, discounted=900, tax=135, grand=1035
        assert inv.grand_total == 1035

    def test_currency_info_default(self):
        inv = self._make_invoice(currency="USD")
        assert inv.currency_info == Currency.USD.value

    def test_currency_info_zar(self):
        inv = self._make_invoice(currency="ZAR")
        assert inv.currency_info == Currency.ZAR.value

    def test_is_overdue_when_past_due(self):
        inv = self._make_invoice(due_date="2020-01-01", status="sent")
        assert inv.is_overdue is True

    def test_is_overdue_not_when_paid(self):
        inv = self._make_invoice(due_date="2020-01-01", status="paid")
        assert inv.is_overdue is False

    def test_is_overdue_not_when_no_date(self):
        inv = self._make_invoice(due_date="", status="sent")
        assert inv.is_overdue is False

    def test_days_until_due_negative(self):
        inv = self._make_invoice(due_date="2020-01-01")
        assert inv.days_until_due < 0

    def test_update_status_marks_overdue(self):
        inv = self._make_invoice(due_date="2020-01-01", status="sent")
        inv.update_status()
        assert inv.status == PaymentStatus.OVERDUE.value

    def test_update_status_keeps_paid(self):
        inv = self._make_invoice(due_date="2020-01-01", status="paid")
        inv.update_status()
        assert inv.status == PaymentStatus.PAID.value

    def test_to_dict_includes_all_new_fields(self):
        inv = self._make_invoice(due_date="2020-01-01", status="sent")
        d = inv.to_dict()
        assert 'subtotal' in d
        assert 'total_discount' in d
        assert 'total_tax' in d
        assert 'grand_total' in d
        assert 'currency_info' in d
        assert 'is_overdue' in d
        assert 'days_until_due' in d
        assert 'payment_instructions' in d


# ---------------------------------------------------------------------------
# Integration tests – InvoiceCore CRUD
# ---------------------------------------------------------------------------

@pytest.fixture
def invoice_core():
    with tempfile.TemporaryDirectory() as d:
        yield InvoiceCore(storage_dir=d)


def _basic_client_data():
    return {"name": "Jane Doe", "email": "jane@example.com"}


def _basic_line_items():
    return [
        {"description": "Web Dev", "quantity": 1, "unit_price": 1500, "tax_percent": 10},
        {"description": "Hosting", "quantity": 5, "unit_price": 50, "discount_percent": 10},
    ]


def test_create_invoice(invoice_core):
    inv, msg = invoice_core.create_invoice(
        _basic_client_data(), _basic_line_items(),
        currency="USD", business_name="Acme", payment_instructions="Pay within 30 days",
    )
    assert inv is not None
    assert inv.invoice_number.startswith("INV-")
    # 1500 + 250 = 1750 subtotal, discount=25, tax on discounted = (1500+(5*50-25))*0.1
    assert float(inv.grand_total) > 0


def test_get_invoice(invoice_core):
    inv, _ = invoice_core.create_invoice(
        _basic_client_data(), _basic_line_items(), currency="ZAR",
    )
    loaded, msg = invoice_core.get_invoice(inv.invoice_id)
    assert loaded is not None
    assert loaded.invoice_number == inv.invoice_number
    assert loaded.grand_total == inv.grand_total


def test_list_invoices(invoice_core):
    invoice_core.create_invoice(_basic_client_data(), _basic_line_items())
    invoice_core.create_invoice(_basic_client_data(), _basic_line_items())
    items = invoice_core.list_invoices()
    assert len(items) == 2
    assert all('grand_total' in i for i in items)


def test_update_invoice_status(invoice_core):
    inv, _ = invoice_core.create_invoice(
        _basic_client_data(), _basic_line_items(),
        currency="USD", status="draft",
    )
    updated, msg = invoice_core.update_invoice(inv.invoice_id, status="sent")
    assert updated is not None
    assert updated.status == "sent"


def test_mark_as_paid(invoice_core):
    inv, _ = invoice_core.create_invoice(
        _basic_client_data(), _basic_line_items(),
        currency="USD", status="draft",
    )
    paid, msg = invoice_core.mark_as_paid(inv.invoice_id)
    assert paid is not None
    assert paid.status == PaymentStatus.PAID.value
    assert paid.is_overdue is False  # paid → not overdue even if past due


def test_delete_invoice(invoice_core):
    inv, _ = invoice_core.create_invoice(_basic_client_data(), _basic_line_items())
    ok, msg = invoice_core.delete_invoice(inv.invoice_id)
    assert ok is True
    loaded, _ = invoice_core.get_invoice(inv.invoice_id)
    assert loaded is None


def test_pdf_preview(invoice_core):
    inv, _ = invoice_core.create_invoice(
        _basic_client_data(), _basic_line_items(), currency="USD",
    )
    html = InvoicePDFGenerator().generate_html_preview(inv)
    assert inv.invoice_number in html
    assert "INVOICE" in html


def test_email_default_body(invoice_core):
    inv, _ = invoice_core.create_invoice(
        _basic_client_data(), _basic_line_items(),
        currency="USD", business_name="Acme Co", payment_instructions="EFT",
    )
    sender = InvoiceEmailSender(from_email="billing@acme.com", from_name="Acme")
    ok, msg = sender.send_invoice_email(invoice=inv, to_email="jane@example.com")
    assert ok is True
    assert "SMTP not configured" in msg


def test_email_with_custom_body(invoice_core):
    inv, _ = invoice_core.create_invoice(
        _basic_client_data(), _basic_line_items(), currency="ZAR",
    )
    sender = InvoiceEmailSender(from_email="x@y.com", from_name="Test")
    ok, msg = sender.send_invoice_email(
        invoice=inv, to_email="jane@example.com", body="Custom body",
    )
    assert ok is True


# ---------------------------------------------------------------------------
# Integration tests – blueprint /api/profile endpoint
# ---------------------------------------------------------------------------

def _authenticate(client):
    return authenticate(client, "profile_test_user")


def test_profile_get_returns_real_stats(client, app_instance):
    username = _authenticate(client)
    resp = client.get("/api/profile")
    data = resp.get_json()
    assert data['success'] is True
    d = data['data']
    assert d['username'] == username
    assert 'stats' in d
    assert isinstance(d['stats']['invoices'], int)
    assert isinstance(d['stats']['optimizations'], int)
    assert isinstance(d['stats']['months_active'], int)
    assert 'preferences' in d
    assert d['preferences']['dark_mode'] is False  # default


def test_profile_post_updates_name_and_company(client, app_instance):
    _authenticate(client)
    resp = client.post("/api/profile",
                       data=json.dumps({"name": "Bongani", "company": "Ipangela"}),
                       content_type="application/json")
    data = resp.get_json()
    assert data['success'] is True
    assert data['profile']['name'] == "Bongani"
    assert data['profile']['company'] == "Ipangela"

    # GET reflects the update
    resp2 = client.get("/api/profile")
    d2 = resp2.get_json()['data']
    assert d2['name'] == "Bongani"
    assert d2['company'] == "Ipangela"


def test_profile_post_updates_preferences(client, app_instance):
    _authenticate(client)
    client.post("/api/profile",
                data=json.dumps({"dark_mode": True, "auto_save": False}),
                content_type="application/json")
    resp = client.get("/api/profile")
    prefs = resp.get_json()['data']['preferences']
    assert prefs['dark_mode'] is True
    assert prefs['auto_save'] is False
