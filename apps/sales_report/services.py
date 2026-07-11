from datetime import timedelta
from decimal import Decimal

from django.db.models import (
    Count,
    Sum,
    Value,
    DecimalField,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.products.models import Order


SALES_STATUS = "DELIVERED"


def get_report_date_range(
    report_type,
    start_date=None,
    end_date=None,
):
    today = timezone.localdate()

    if report_type == "daily":
        return today, today

    if report_type == "weekly":
        week_start = today - timedelta(
            days=today.weekday()
        )

        week_end = week_start + timedelta(
            days=6
        )

        return week_start, week_end

    if report_type == "yearly":
        year_start = today.replace(
            month=1,
            day=1,
        )

        year_end = today.replace(
            month=12,
            day=31,
        )

        return year_start, year_end

    return start_date, end_date


def get_sales_queryset(
    start_date,
    end_date,
):
    return (
        Order.objects
        .filter(
            status=SALES_STATUS,
            created_at__date__range=(
                start_date,
                end_date,
            ),
        )
        .select_related(
            "user",
        )
        .order_by(
            "-created_at",
        )
    )


def get_sales_summary(queryset):
    zero_decimal = Value(
        Decimal("0.00"),
        output_field=DecimalField(
            max_digits=12,
            decimal_places=2,
        ),
    )

    return queryset.aggregate(
        sales_count=Count("id"),

        order_amount=Coalesce(
            Sum("total_amount"),
            zero_decimal,
        ),

        total_discount=Coalesce(
            Sum("discount"),
            zero_decimal,
        ),

        final_sales=Coalesce(
            Sum("final_amount"),
            zero_decimal,
        ),
    )


def get_sales_report(
    report_type,
    start_date=None,
    end_date=None,
):
    start_date, end_date = (
        get_report_date_range(
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
        )
    )

    orders = get_sales_queryset(
        start_date=start_date,
        end_date=end_date,
    )

    summary = get_sales_summary(orders)

    return {
        "orders": orders,
        "summary": summary,
        "start_date": start_date,
        "end_date": end_date,
        "report_type": report_type,
    }