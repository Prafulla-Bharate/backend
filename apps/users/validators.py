"""
User Validators
===============
Custom password and field validators.
"""

import re
from typing import Optional

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PasswordComplexityValidator:
    """
    Validate that the password meets complexity requirements.
    
    Requirements:
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    
    def __init__(
        self,
        min_uppercase: int = 1,
        min_lowercase: int = 1,
        min_digits: int = 1,
        min_special: int = 1,
    ):
        self.min_uppercase = min_uppercase
        self.min_lowercase = min_lowercase
        self.min_digits = min_digits
        self.min_special = min_special

    def validate(self, password: str, user=None) -> None:
        """Validate the password complexity."""
        errors = []
        
        # Check uppercase
        if len(re.findall(r"[A-Z]", password)) < self.min_uppercase:
            errors.append(
                _("Password must contain at least %(count)d uppercase letter(s).")
                % {"count": self.min_uppercase}
            )
        
        # Check lowercase
        if len(re.findall(r"[a-z]", password)) < self.min_lowercase:
            errors.append(
                _("Password must contain at least %(count)d lowercase letter(s).")
                % {"count": self.min_lowercase}
            )
        
        # Check digits
        if len(re.findall(r"\d", password)) < self.min_digits:
            errors.append(
                _("Password must contain at least %(count)d digit(s).")
                % {"count": self.min_digits}
            )
        
        # Check special characters
        special_chars = r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\\/`~;']"
        if len(re.findall(special_chars, password)) < self.min_special:
            errors.append(
                _("Password must contain at least %(count)d special character(s).")
                % {"count": self.min_special}
            )
        
        if errors:
            raise ValidationError(errors)

    def get_help_text(self) -> str:
        """Return help text for the validator."""
        return _(
            "Your password must contain at least: "
            "%(uppercase)d uppercase letter(s), "
            "%(lowercase)d lowercase letter(s), "
            "%(digits)d digit(s), and "
            "%(special)d special character(s)."
        ) % {
            "uppercase": self.min_uppercase,
            "lowercase": self.min_lowercase,
            "digits": self.min_digits,
            "special": self.min_special,
        }


def validate_phone_number(value: str) -> None:
    """Validate phone number format."""
    if value:
        # Remove common formatting characters
        cleaned = re.sub(r"[\s\-\(\)\.]", "", value)
        
        # Check if it's a valid phone number (digits only, with optional + prefix)
        if not re.match(r"^\+?\d{7,15}$", cleaned):
            raise ValidationError(
                _("Enter a valid phone number (7-15 digits, optional + prefix).")
            )


def validate_linkedin_url(value: str) -> None:
    """Validate LinkedIn URL format."""
    if value:
        pattern = r"^https?://(www\.)?linkedin\.com/(in|company)/[\w\-]+/?$"
        if not re.match(pattern, value, re.IGNORECASE):
            raise ValidationError(
                _("Enter a valid LinkedIn profile URL (e.g., https://linkedin.com/in/username).")
            )


def validate_github_url(value: str) -> None:
    """Validate GitHub URL format."""
    if value:
        pattern = r"^https?://(www\.)?github\.com/[\w\-]+/?$"
        if not re.match(pattern, value, re.IGNORECASE):
            raise ValidationError(
                _("Enter a valid GitHub profile URL (e.g., https://github.com/username).")
            )
