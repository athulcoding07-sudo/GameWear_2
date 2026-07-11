from datetime import datetime

from django.core.exceptions import ValidationError


ALLOWED_REPORT_TYPES = {
    "daily",
    "weekly",
    "yearly",
    "custom",
}


def parse_date(value, field_name):
    if not value:
        raise ValidationError(
            f"{field_name} is required."
        )

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        raise ValidationError(
            f"Invalid {field_name.lower()}."
        )


def validate_report_filters(params):
    report_type = params.get(
        "report_type",
        "daily",
    ).strip().lower()

    if report_type not in ALLOWED_REPORT_TYPES:
        raise ValidationError(
            "Invalid report type."
        )

    start_date = None
    end_date = None

    if report_type == "custom":
        start_date = parse_date(
            params.get("start_date"),
            "Start date",
        )

        end_date = parse_date(
            params.get("end_date"),
            "End date",
        )

        if start_date > end_date:
            raise ValidationError(
                "Start date cannot be after end date."
            )

    return {
        "report_type": report_type,
        "start_date": start_date,
        "end_date": end_date,
    }