from apps.payments.models import Payment


def get_payment_by_razorpay_order_id(order_id):

    return Payment.objects.select_related(
        "order",
        "user"
    ).get(
        razorpay_order_id=order_id
    )