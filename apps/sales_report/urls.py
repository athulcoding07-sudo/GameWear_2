from django.urls import path

from . import views


app_name = "sales_report"


urlpatterns = [
    path(
        "",
        views.sales_report_view,
        name="sales_report",
    ),

    path(
        "export/pdf/",
        views.export_sales_pdf,
        name="export_pdf",
    ),

    path(
        "export/excel/",
        views.export_sales_excel,
        name="export_excel",
    ),
]