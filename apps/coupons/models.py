from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone


class Coupon(models.Model):

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    discount_percentage = models.PositiveIntegerField()

    minimum_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    maximum_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    valid_from = models.DateTimeField()

    valid_to = models.DateTimeField()

    usage_limit = models.PositiveIntegerField(
        default=100,
    )

    used_count = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = ["-created_at"]

    def __str__(self):

        return self.code

    @property
    def is_valid(self):

        now = timezone.now()

        return (
            self.is_active
            and self.valid_from <= now <= self.valid_to
            and self.used_count < self.usage_limit
        )