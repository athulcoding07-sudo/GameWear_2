from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.offers.models import CategoryOffer
from apps.offers.models import ProductOffer


class OfferValidator:

    @staticmethod
    def validate(data,instance = None):

        name = data.get("name", "").strip()
        discount = data.get("discount_percentage")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if not name:
            raise ValidationError("Offer name is required.")

        if len(name) < 3:
            raise ValidationError(
                "Offer name must contain at least 3 characters."
            )

        if len(name) > 100:
            raise ValidationError(
                "Offer name cannot exceed 100 characters."
            )
        
        # Duplicate validation
        category_offer = CategoryOffer.objects.filter(
            name__iexact=name
        )

        product_offer = ProductOffer.objects.filter(
            name__iexact=name
        )

        if instance:
            if isinstance(instance, CategoryOffer):
                category_offer = category_offer.exclude(pk=instance.pk)

            elif isinstance(instance, ProductOffer):
                product_offer = product_offer.exclude(pk=instance.pk)


        if category_offer or product_offer:
            raise ValidationError(
                "An offer with this name already exists."
            )

        if discount in (None, ""):
            raise ValidationError(
                "Discount percentage is required."
            )

        discount = Decimal(discount)

        if discount <= 0:
            raise ValidationError(
                "Discount percentage must be greater than 0."
            )

        if discount > 90:
            raise ValidationError(
                "Discount percentage cannot exceed 90%."
            )

        if not start_date:
            raise ValidationError(
                "Start date is required."
            )

        if not end_date:
            raise ValidationError(
                "End date is required."
            )

        start = timezone.datetime.fromisoformat(start_date)
        end = timezone.datetime.fromisoformat(end_date)
        if timezone.is_naive(start):
            start = timezone.make_aware(start)

        if timezone.is_naive(end):
            end = timezone.make_aware(end)
            
        if start >= end:
            raise ValidationError(
                "End date must be later than the start date."
            )

        if end <= timezone.now():
            raise ValidationError(
                "End date must be in the future."
            )
        return start, end
        
    @staticmethod
    def validate_product(product, start, end, instance=None):

        offers = ProductOffer.objects.filter(
            product=product,
            is_active=True
        )

        if instance:
            offers = offers.exclude(pk=instance.pk)

        for offer in offers:
            if start < offer.end_date and end > offer.start_date:
                raise ValidationError(
                    "An active offer already exists for this product during the selected period."
                )
        

    @staticmethod
    def validate_category(category, start, end, instance=None):

        offers = CategoryOffer.objects.filter(
            category=category,
            is_active=True
        )

        if instance:
            offers = offers.exclude(pk=instance.pk)

        for offer in offers:
            if start < offer.end_date and end > offer.start_date:
                raise ValidationError(
                    "An active offer already exists for this category during the selected period."
                )