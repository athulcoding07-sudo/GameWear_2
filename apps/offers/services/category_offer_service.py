from django.shortcuts import get_object_or_404

from apps.offers.models import CategoryOffer
from apps.products.models import Category
from apps.offers.validators.offer_validator import OfferValidator


class CategoryOfferService:

    @staticmethod
    def get_all():
        return CategoryOffer.objects.select_related(
            "category"
        ).order_by("-id")

    @staticmethod
    def get_by_id(offer_id):
        return get_object_or_404(
            CategoryOffer,
            id=offer_id
        )

    @staticmethod
    def create(data):

        category = get_object_or_404(
            Category,
            id=data.get("category")
        )
        start, end = OfferValidator.validate(data)

        OfferValidator.validate_category(
            category,
            start,
            end
    )

        return CategoryOffer.objects.create(
            category=category,
            name=data.get("name"),
            discount_percentage=data.get("discount_percentage"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
        )

    @staticmethod
    def update(offer, data):

        offer.category = get_object_or_404(
            Category,
            id=data.get("category")
        )

        start, end = OfferValidator.validate(data,offer)

        OfferValidator.validate_category(
            offer.category,
            start,
            end,
            offer
        )

        offer.name = data.get("name")
        offer.discount_percentage = data.get("discount_percentage")
        offer.start_date = data.get("start_date")
        offer.end_date = data.get("end_date")

        offer.save()

        return offer

    @staticmethod
    def toggle(offer):

        offer.is_active = not offer.is_active
        offer.save(update_fields=["is_active"])

        return offer

    @staticmethod
    def delete(offer):

        offer.delete()