"""docstring"""
import re
from django.core.exceptions import ValidationError


def validate_name(value):
    """
    Validates user name. Allows letters, numbers, spaces, and standard characters.
    Does not strictly require spaces in name text.
    """
    if not isinstance(value, str):
        raise ValidationError("Invalid name format.")

    value = value.strip()  # Remove leading and trailing spaces

    if not value:
        raise ValidationError("Name is required.")

    if value.isdigit():
        raise ValidationError("Name cannot contain only numbers.")

    if not re.fullmatch(r"[A-Za-z0-9\s'&()-]+", value):
        raise ValidationError(
            "Name can only contain letters, numbers, spaces, &, apostrophes, hyphens, and parentheses."
        )

