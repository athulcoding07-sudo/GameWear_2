import re
from django.core.exceptions import ValidationError



def validate_name(value):
    value = value.strip()

    # Empty name
    if not value:
        raise ValidationError(
            "Name is required."
        )

    if len(value) < 3:
        raise ValidationError(
            "Name must be at least 3 characters long."
        )

    if len(value) > 100:
        raise ValidationError(
            "Name cannot exceed 100 characters."
        )

    if value.isdigit():
        raise ValidationError(
            "Name cannot contain only numbers."
        )

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 &'()-]*", value):
        raise ValidationError(
            "Name can only contain letters, numbers, spaces, &, apostrophes, hyphens, and parentheses."

        )
    



def validate_description(value):
    value = value.strip()

    if not value:
        raise ValidationError(
            "Description is required."
        )

    if len(value) < 10:
        raise ValidationError(
            "Description must be at least 10 characters long."
        )

    if len(value) > 500:
        raise ValidationError(
            "Description cannot exceed 500 characters."
        )

    if value.isdigit():
        raise ValidationError(
            "Description cannot contain only numbers."
        )