from django.db import models

# Create your models here.
from django.db import models
from apps.products.models import Order


class Payment(models.Model):

    PAYMENT_STATUS = (
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    )

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment"
    )

    razorpay_order_id = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    razorpay_payment_id = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    razorpay_signature = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="PENDING"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.order_number}"