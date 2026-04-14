"""docstring"""
import re
from django.core.exceptions import ValidationError


def validate_name(value):
    """
    Validates that a name contains only letters (A–Z, a–z),
    no spaces, no digits, and no special characters.
    """
    if not isinstance(value, str):
        raise ValidationError("Invalid name format.")

    if not re.fullmatch(r"[A-Za-z]+", value):
        raise ValidationError(
            "Name must contain only letters. No spaces, numbers, or symbols allowed."
        )
