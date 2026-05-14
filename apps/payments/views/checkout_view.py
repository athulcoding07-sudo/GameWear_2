from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings

from apps.products.models import Order
from apps.payments.services.payment_service import PaymentService


@login_required
def checkout_view(request, order_id):

    order = Order.objects.select_related(
        "user"
    ).get(
        id=order_id,
        user=request.user
    )

    payment = PaymentService.initialize_payment(order)

    context = {
        "order": order,
        "payment": payment,
        "razorpay_key_id":
            settings.RAZORPAY_KEY_ID,
    }

    return render(
        request,
        "payments/checkout.html",
        context
    )