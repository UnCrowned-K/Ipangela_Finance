import pytest
from utils import ValidationUtils


class TestSanitizeString:
    def test_strips_dangerous_chars(self):
        result = ValidationUtils.sanitize_string('<script>alert(1)</script>', 'test')
        assert '<' not in result
        assert '>' not in result
        assert 'script' in result

    def test_none_returns_empty(self):
        assert ValidationUtils.sanitize_string(None, 'test') == ''

    def test_truncates_long_string(self):
        assert len(ValidationUtils.sanitize_string('x' * 1000, 'test', max_length=50)) == 50


class TestSanitizeCsvValue:
    @pytest.mark.parametrize('value', ['=CMD("calc")', '+cmd', '-500', '@SUM(1)', '\thello', '\rworld'])
    def test_prefixes_formula_starters(self, value):
        result = ValidationUtils.sanitize_csv_value(value)
        assert result.startswith("'")

    def test_clean_string_unmodified(self):
        assert ValidationUtils.sanitize_csv_value('hello') == 'hello'

    def test_numbers_unmodified(self):
        assert ValidationUtils.sanitize_csv_value(42) == 42
        assert ValidationUtils.sanitize_csv_value(0) == 0


class TestValidateEmail:
    def test_valid(self):
        assert ValidationUtils.validate_email('a@b.co') == 'a@b.co'

    def test_invalid(self):
        with pytest.raises(ValueError):
            ValidationUtils.validate_email('not-email')

    def test_blank_ok(self):
        assert ValidationUtils.validate_email('') == ''


class TestValidateAmount:
    def test_valid(self):
        assert ValidationUtils.validate_amount('12.5') == 12.5

    def test_invalid(self):
        with pytest.raises(ValueError):
            ValidationUtils.validate_amount('abc')


class TestValidateDate:
    def test_valid(self):
        assert ValidationUtils.validate_date('2025-06-15') == '2025-06-15'

    def test_invalid(self):
        with pytest.raises(ValueError):
            ValidationUtils.validate_date('2025-15-01')


class TestValidateAccountType:
    def test_valid(self):
        assert ValidationUtils.validate_account_type('checking') == 'checking'
        assert ValidationUtils.validate_account_type('savings') == 'savings'

    def test_invalid(self):
        with pytest.raises(ValueError):
            ValidationUtils.validate_account_type('bitcoin')


class TestValidateTransactionType:
    def test_valid(self):
        assert ValidationUtils.validate_transaction_type('expense') == 'expense'
        assert ValidationUtils.validate_transaction_type('income') == 'income'
        assert ValidationUtils.validate_transaction_type('transfer') == 'transfer'

    def test_invalid(self):
        with pytest.raises(ValueError):
            ValidationUtils.validate_transaction_type('transfer2')


class TestPasswordHashing:
    def test_round_trip(self):
        h, salt = ValidationUtils.hash_password('secret')
        assert ValidationUtils.verify_password('secret', h, salt)
        assert not ValidationUtils.verify_password('wrong', h, salt)

    def test_same_password_different_salt(self):
        h1, s1 = ValidationUtils.hash_password('secret')
        h2, s2 = ValidationUtils.hash_password('secret')
        assert s1 != s2
        assert h1 != h2
        assert ValidationUtils.verify_password('secret', h1, s1)
        assert ValidationUtils.verify_password('secret', h2, s2)


class TestGenerateSecureId:
    def test_unique(self):
        ids = {ValidationUtils.generate_secure_id() for _ in range(100)}
        assert len(ids) == 100

    def test_is_uuid_format(self):
        import uuid
        uid = uuid.UUID(ValidationUtils.generate_secure_id())
        assert uid.version == 4
