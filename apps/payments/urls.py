from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [

    path(
        "start/<int:order_id>/",
        views.start_payment,
        name="start_payment"
    ),

    path(
        "success/",
        views.payment_success,
        name="payment_success"
    ),

    path(
        "failed/<int:order_id>/",
        views.payment_failed,
        name="payment_failed"
    ),

]