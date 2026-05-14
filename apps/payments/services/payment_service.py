from apps.payments.models import Payment
from apps.payments.services.razorpay_service import RazorpayService


class PaymentService:

    @staticmethod
    def initialize_payment(order):

        razorpay_service = RazorpayService()

        amount = int(order.final_amount * 100)

        razorpay_order = razorpay_service.create_order(
            amount=amount,
            receipt=order.order_id
        )

        payment = Payment.objects.create(
            user=order.user,
            order=order,
            gateway="razorpay",
            amount=order.final_amount,
            status="pending",
            razorpay_order_id=razorpay_order["id"],
            raw_response=razorpay_order
        )

        return payment