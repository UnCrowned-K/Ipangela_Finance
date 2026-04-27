import re
import hashlib
import secrets
import uuid
from typing import Any, Dict, Tuple, Optional


class ValidationUtils:
    """Shared validation and sanitization utilities."""
    
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    AMOUNT_REGEX = re.compile(r'^-?\d+(\.\d{1,2})?$')
    
    @staticmethod
    def sanitize_string(value: Any, field_name: str, max_length: int = 500) -> str:
        """Sanitize string input to prevent XSS and injection attacks."""
        if value is None:
            return ""
        if not isinstance(value, str):
            value = str(value)
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\'\\{}|\[\]]', '', str(value))
        return sanitized.strip()[:max_length]
    
    @staticmethod
    def validate_email(email: str, field_name: str = "email") -> str:
        """Validate email format."""
        if not email:
            return ""
        if not ValidationUtils.EMAIL_REGEX.match(email):
            raise ValueError(f"Invalid {field_name} format: {email}")
        return email.lower().strip()
    
    @staticmethod
    def validate_amount(value: Any, field_name: str = "amount") -> float:
        """Validate and convert amount value."""
        try:
            amount = float(value)
            if amount < 0:
                raise ValueError(f"{field_name} cannot be negative")
            return round(amount, 2)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid {field_name}: must be a number") from e
    
    @staticmethod
    def generate_secure_id() -> str:
        """Generate a secure unique identifier."""
        return str(uuid.uuid4())
    
    @staticmethod
    def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
        """Hash a password with salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash_obj.hexdigest(), salt
    
    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """Verify a password against its hash."""
        new_hash, _ = ValidationUtils.hash_password(password, salt)
        return secrets.compare_digest(new_hash, hashed)
