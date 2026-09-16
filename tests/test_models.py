import pytest

from finance_core.models import (
    Account,
    Alert,
    Budget,
    Category,
    Transaction,
    ValidationError,
)


class TestSerialization:
    def test_round_trip_preserves_fields(self):
        acct = Account.from_dict(
            {
                "id": "a1",
                "name": "Savings",
                "type": "savings",
                "balance": "1250.50",
                "currency": "ZAR",
            }
        )
        assert acct.balance == 1250.50
        assert isinstance(acct.balance, float)
        restored = Account.from_dict(acct.to_dict())
        assert restored.to_dict() == acct.to_dict()

    def test_unknown_keys_ignored(self):
        cat = Category.from_dict(
            {"id": "c1", "name": "Food", "type": "expense", "future_field": 42}
        )
        assert cat.name == "Food"
        assert "future_field" not in cat.to_dict()

    def test_defaults_applied_for_missing_optionals(self):
        alert = Alert.from_dict(
            {"id": "a1", "type": "low_balance", "message": "low", "severity": "warning"}
        )
        assert alert.is_read is False
        assert alert.data == {}

    def test_bool_coercion(self):
        txn = Transaction.from_dict(
            {
                "id": "t1",
                "account_id": "a1",
                "type": "expense",
                "amount": 10,
                "category_id": "c1",
                "description": "d",
                "date": "2026-01-01",
                "is_recurring": "true",
                "tags": ["x"],
            }
        )
        assert txn.is_recurring is True

    def test_none_rejected_for_non_optional(self):
        with pytest.raises(ValidationError) as exc:
            Transaction.from_dict(
                {
                    "id": "t1",
                    "account_id": "a1",
                    "type": "expense",
                    "amount": None,
                    "category_id": "c1",
                    "description": "d",
                    "date": "2026-01-01",
                }
            )
        assert exc.value.field == "amount"

    def test_missing_required_rejected(self):
        with pytest.raises(ValidationError) as exc:
            Category.from_dict({"id": "c1"})
        assert exc.value.field == "name"

    def test_to_dict_has_no_side_effects_on_updated_at(self):
        acct = Account.from_dict(
            {"id": "a1", "name": "Savings", "type": "savings", "balance": 10}
        )
        before = acct.updated_at
        acct.to_dict()
        assert acct.updated_at == before

    def test_to_dict_deep_copies_mutable_fields(self):
        alert = Alert.from_dict(
            {
                "id": "a1",
                "type": "low_balance",
                "message": "low",
                "severity": "warning",
                "data": {"k": 1},
            }
        )
        payload = alert.to_dict()
        payload["data"]["k"] = 99
        assert alert.data["k"] == 1