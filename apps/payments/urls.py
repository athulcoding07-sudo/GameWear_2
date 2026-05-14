from django.urls import path
from apps.payments.views.checkout_view import checkout_view
from apps.payments.views.verify_view import verify_payment_view
from apps.payments.views.webhook_view import razorpay_webhook


app_name = "payments"

urlpatterns = [
    path("checkout/<int:order_id>/", checkout_view, name="checkout"),
    path("verify/", verify_payment_view, name="verify_payment"),
    path("webhook/", razorpay_webhook, name="razorpay_webhook"),
]