from django.db import models

from django.utils import timezone
from apps.core.validators import validate_name


# Create your models here.


class BaseOffer(models.Model):

    name = models.CharField(max_length=100,validators=[validate_name])

    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    start_date = models.DateTimeField()

    end_date = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
    
    @property
    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active
            and self.start_date <= now <= self.end_date
        )

class ProductOffer(BaseOffer):

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="offers"
    )



class CategoryOffer(BaseOffer):

    category = models.ForeignKey(
        "products.Category",
        on_delete=models.CASCADE,
        related_name="offers"
    )


    
class ReferralOffer(models.Model):

    reward_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    minimum_order = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    is_active = models.BooleanField(default=True)