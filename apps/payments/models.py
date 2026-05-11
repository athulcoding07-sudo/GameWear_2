from django.db import models
from django.conf import settings
from apps.products.models import Order
from apps.users.models import User


class Payment(models.Model):

    STATUS_CHOICES = (
        ("created", "Created"),
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    GATEWAY_CHOICES = (
        ("razorpay", "Razorpay"),
    )

    PAYMENT_METHOD_CHOICES = (
        ("upi", "UPI"),
        ("card", "Card"),
        ("netbanking", "Net Banking"),
        ("wallet", "Wallet"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    order = models.ForeignKey(
        "products.Order",
        on_delete=models.CASCADE,
        related_name="payments"
    )

    # =====================================
    # Payment Provider
    # =====================================

    gateway = models.CharField(
        max_length=20,
        choices=GATEWAY_CHOICES,
        default="razorpay"
    )

    # =====================================
    # Payment Method Used by Customer
    # =====================================

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=10,
        default="INR"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="created"
    )

    # =====================================
    # Razorpay Data
    # =====================================

    gateway_order_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )

    gateway_payment_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    gateway_signature = models.TextField(
        null=True,
        blank=True
    )

    transaction_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    failure_reason = models.TextField(
        null=True,
        blank=True
    )

    # =====================================
    # Full Razorpay Response
    # =====================================

    raw_response = models.JSONField(
        default=dict,
        blank=True
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = "payments"

        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["gateway"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):

        return f"{self.order.order_id} - {self.status}"
