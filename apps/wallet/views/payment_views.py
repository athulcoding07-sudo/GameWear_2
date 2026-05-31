import json
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render,redirect
from django.views.decorators.http import require_POST

from apps.wallet.models import WalletTopUp
from apps.wallet.services.wallet_payment_service import (
    WalletPaymentService
)


@login_required
def add_money_page(request):
    """
    Render wallet add money page
    """

    return render(
        request,
        "users/wallet/add_money.html"
    )


@login_required
@require_POST
def create_razorpay_order(request):
    """
    Create Razorpay order
    """

    try:
        data = json.loads(request.body)

        amount = Decimal(
            str(data.get("amount"))
        )

        order = WalletPaymentService.create_topup(
            user=request.user,
            amount=amount
        )

        return JsonResponse({
            "success": True,
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key": settings.RAZORPAY_KEY_ID
        })

    except Exception as e:

        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=400)




@login_required
@require_POST
@transaction.atomic
def payment_success(request):
    """
    Verify Razorpay payment
    and credit wallet
    """

    try:

        order_id = request.POST.get(
            "razorpay_order_id"
        )

        payment_id = request.POST.get(
            "razorpay_payment_id"
        )

        signature = request.POST.get(
            "razorpay_signature"
        )

        topup = WalletTopUp.objects.get(
            razorpay_order_id=order_id,
            user=request.user
        )

        credited = (
            WalletPaymentService.verify_and_credit(
                topup=topup,
                payment_id=payment_id,
                razorpay_signature=signature
            )
        )

        if credited:

            return render(
                request,
                "users/wallet/payment_success.html"
            )

        return redirect(
            "wallet:dashboard"
        )

    except WalletTopUp.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message": "Invalid order"
            },
            status=404
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": str(e)
            },
            status=400
        )