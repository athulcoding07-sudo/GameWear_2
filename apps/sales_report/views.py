from django.shortcuts import render

# Create your views here.
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect, render

from openpyxl import Workbook

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .services import get_sales_report
from .validations import validate_report_filters
from django.core.paginator import Paginator


def admin_required(user):
    return user.is_authenticated and user.is_staff


def _get_report_from_request(request):
    filters = validate_report_filters(
        request.GET
    )

    return get_sales_report(
        report_type=filters["report_type"],
        start_date=filters["start_date"],
        end_date=filters["end_date"],
    )


@login_required
@user_passes_test(admin_required)
def sales_report_view(request):
    try:
        report = _get_report_from_request(request)

    except ValidationError as error:
        messages.error(request, error.messages[0])
        return redirect("sales_report:sales_report")

    orders = report.get("orders", [])

    paginator = Paginator(orders, 10)
    page_number = request.GET.get("page")
    report["orders"] = paginator.get_page(page_number)

    context = {
        **report,
        "selected_start_date": request.GET.get("start_date", ""),
        "selected_end_date": request.GET.get("end_date", ""),
    }

    return render(
        request,
        "adminpanel/sales_report/sales_report_list.html",
        context,
    )


@login_required
@user_passes_test(admin_required)
def export_sales_excel(request):
    try:
        report = _get_report_from_request(
            request
        )

    except ValidationError as error:
        messages.error(
            request,
            error.messages[0],
        )

        return redirect(
            "sales_report:sales_report"
        )

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Sales Report"

    worksheet.append([
        "Sales Report",
    ])

    worksheet.append([
        "Period",
        f"{report['start_date']} to {report['end_date']}",
    ])

    worksheet.append([])

    worksheet.append([
        "Sales Count",
        report["summary"]["sales_count"],
    ])

    worksheet.append([
        "Order Amount",
        float(
            report["summary"]["order_amount"]
        ),
    ])

    worksheet.append([
        "Total Discount",
        float(
            report["summary"]["total_discount"]
        ),
    ])

    worksheet.append([
        "Final Sales",
        float(
            report["summary"]["final_sales"]
        ),
    ])

    worksheet.append([])

    worksheet.append([
        "Order ID",
        "Date",
        "Customer",
        "Order Amount",
        "Discount",
        "Final Amount",
    ])

    for order in report["orders"]:
        worksheet.append([
            order.order_id,
            order.created_at.strftime(
                "%d-%m-%Y"
            ),
            order.user.email,
            float(order.total_amount),
            float(order.discount),
            float(order.final_amount),
        ])

    for column in worksheet.columns:
        max_length = 0
        column_letter = column[0].column_letter

        for cell in column:
            if cell.value is not None:
                max_length = max(
                    max_length,
                    len(str(cell.value)),
                )

        worksheet.column_dimensions[
            column_letter
        ].width = max_length + 3

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )

    response[
        "Content-Disposition"
    ] = 'attachment; filename="sales_report.xlsx"'

    workbook.save(response)

    return response


@login_required
@user_passes_test(admin_required)
def export_sales_pdf(request):
    try:
        report = _get_report_from_request(
            request
        )

    except ValidationError as error:
        messages.error(
            request,
            error.messages[0],
        )

        return redirect(
            "sales_report:sales_report"
        )

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()

    elements = [
        Paragraph(
            "Sales Report",
            styles["Title"],
        ),
        Spacer(1, 12),
        Paragraph(
            (
                f"Period: {report['start_date']} "
                f"to {report['end_date']}"
            ),
            styles["Normal"],
        ),
        Spacer(1, 15),
    ]

    summary_data = [
        [
            "Sales Count",
            "Order Amount",
            "Discount",
            "Final Sales",
        ],
        [
            str(
                report["summary"]["sales_count"]
            ),
            f"Rs. {report['summary']['order_amount']}",
            f"Rs. {report['summary']['total_discount']}",
            f"Rs. {report['summary']['final_sales']}",
        ],
    ]

    summary_table = Table(
        summary_data,
        repeatRows=1,
    )

    summary_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.black,
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white,
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey,
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER",
            ),
            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8,
            ),
        ])
    )

    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    order_data = [[
        "Order ID",
        "Date",
        "Customer",
        "Order Amount",
        "Discount",
        "Final Amount",
    ]]

    for order in report["orders"]:
        order_data.append([
            order.order_id,
            order.created_at.strftime(
                "%d-%m-%Y"
            ),
            order.user.email,
            f"Rs. {order.total_amount}",
            f"Rs. {order.discount}",
            f"Rs. {order.final_amount}",
        ])

    order_table = Table(
        order_data,
        repeatRows=1,
    )

    order_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.black,
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white,
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey,
            ),
            (
                "PADDING",
                (0, 0),
                (-1, -1),
                7,
            ),
        ])
    )

    elements.append(order_table)

    document.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(
        pdf,
        content_type="application/pdf",
    )

    response[
        "Content-Disposition"
    ] = 'attachment; filename="sales_report.pdf"'

    return response