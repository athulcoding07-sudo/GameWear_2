"""docstring"""
import re
from django.core.exceptions import ValidationError


def validate_name(value):
    """
    Validates that a name contains only letters and spaces.
    Numbers and special characters are not allowed.
    """
    if not isinstance(value, str):
        raise ValidationError("Invalid name format.")

    value = value.strip()  # Remove leading and trailing spaces

    if not re.fullmatch(r"[A-Za-z]+(?: [A-Za-z]+)*", value):
        raise ValidationError(
            "Name must contain only letters and spaces. Numbers and special characters are not allowed."
        )
