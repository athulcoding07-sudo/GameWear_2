import razorpay

from django.conf import settings
from django.shortcuts import render, get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages

from apps.products.models import Order
from .models import Payment
from apps.products.models import CartItem
from apps.products.models import ProductVariant


@login_required
def start_payment(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    amount = int(order.final_amount * 100)

    razorpay_order = client.order.create({
        "amount": amount,
        "currency": "INR",
        
    })

    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            "amount": order.final_amount
        }
    )

    payment.razorpay_order_id = razorpay_order["id"]
    payment.save()
    print("KEY:", settings.RAZORPAY_KEY_ID)
    print("ORDER:", razorpay_order)

    context = {
        "order": order,
        "payment": payment,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount": amount,
    }

    return render(
        request,
        "payments/payment_page.html",
        context
    )


@login_required
@transaction.atomic
def payment_success(request):

    if request.method != "POST":
        return redirect("home")

    razorpay_order_id = request.POST.get(
        "razorpay_order_id"
    )

    razorpay_payment_id = request.POST.get(
        "razorpay_payment_id"
    )

    razorpay_signature = request.POST.get(
        "razorpay_signature"
    )

    payment = Payment.objects.select_for_update().get(
        razorpay_order_id=razorpay_order_id
    )

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    try:

        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })

    except:

        payment.status = "FAILED"
        payment.save()

        return redirect(
            "payments:payment_failed",
            payment.order.id
        )

    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.status = "SUCCESS"
    payment.save()

    order = payment.order

    for item in order.items.all():

        if item.variant:

            variant = item.variant

            variant.stock -= item.quantity
            variant.save()

    CartItem.objects.filter(
        cart__user=order.user
    ).delete()

    order.payment_status = "PAID"
    order.status = "CONFIRMED"
    order.save()

    messages.success(
        request,
        "Payment successful."
    )

    return redirect(
        "products:order_success",
        order.id
    )



@login_required
def payment_failed(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    order.status = "PAYMENT_FAILED"
    order.save()

    return render(
        request,
        "payments/payments_failed.html",
        {
            "order": order
        }
    )