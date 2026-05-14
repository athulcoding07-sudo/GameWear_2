import json
import logging

import razorpay

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone

from apps.payments.services.razorpay_service import (
    RazorpayService
)

from apps.payments.selectors.payment_selector import (
    get_payment_by_razorpay_order_id
)


logger = logging.getLogger(__name__)


@require_POST
@transaction.atomic
def verify_payment_view(request):

    body = json.loads(request.body)

    razorpay_order_id = body.get(
        "razorpay_order_id"
    )

    razorpay_payment_id = body.get(
        "razorpay_payment_id"
    )

    razorpay_signature = body.get(
        "razorpay_signature"
    )

    payment = get_payment_by_razorpay_order_id(
        razorpay_order_id
    )

    # Prevent duplicate processing
    if payment.status == "success":

        return JsonResponse({
            "message": "Already Processed"
        })

    razorpay_service = RazorpayService()

    try:

        # Verify Razorpay signature
        razorpay_service.verify_signature({

            "razorpay_order_id": razorpay_order_id,

            "razorpay_payment_id": razorpay_payment_id,

            "razorpay_signature": razorpay_signature,
        })

        # Update payment
        payment.razorpay_payment_id = (
            razorpay_payment_id
        )

        payment.razorpay_signature = (
            razorpay_signature
        )

        payment.status = "success"

        payment.paid_at = timezone.now()

        payment.save()

        # Update order
        order = payment.order

        order.status = "CONFIRMED"

        order.save()

        return JsonResponse({
            "message": "Payment Successful",
            "order_id": order.id

        })

    except razorpay.errors.SignatureVerificationError:

        payment.status = "failed"

        payment.save()

        logger.exception(
            "Razorpay Signature Verification Failed"
        )

        return JsonResponse({

            "message": "Payment Verification Failed"

        }, status=400)