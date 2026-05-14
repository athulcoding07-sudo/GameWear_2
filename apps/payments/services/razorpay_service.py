import razorpay

from django.conf import settings


class RazorpayService:

    def __init__(self):

        self.client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            )
        )

    def create_order(self, *, amount, receipt):

        data = {
            "amount": amount,
            "currency": "INR",
            "receipt": receipt,
            "payment_capture": 1,
        }

        return self.client.order.create(data=data)

    def verify_signature(self, data):

        return self.client.utility.verify_payment_signature(data)