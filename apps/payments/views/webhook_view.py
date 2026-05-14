import json
import hmac
import hashlib

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def razorpay_webhook(request):

    webhook_signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    generated_signature = hmac.new(
        bytes(settings.RAZORPAY_WEBHOOK_SECRET, 'utf-8'),
        request.body,
        hashlib.sha256
    ).hexdigest()

    if generated_signature != webhook_signature:

        return HttpResponse(status=400)

    payload = json.loads(request.body)

    event = payload.get("event")

    if event == "payment.captured":

        # process payment

        pass

    return HttpResponse(status=200)