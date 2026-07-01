from django.shortcuts import get_object_or_404

from apps.offers.models import ProductOffer
from apps.products.models import Product
from apps.offers.validators.offer_validator import OfferValidator


class ProductOfferService:

    @staticmethod
    def get_all():
        return ProductOffer.objects.select_related(
            "product"
        ).order_by("-id")

    @staticmethod
    def get_by_id(offer_id):
        return get_object_or_404(
            ProductOffer,
            id=offer_id
        )

    @staticmethod
    def create(data):

        product = get_object_or_404(
            Product,
            id=data.get("product")
        )
        start, end = OfferValidator.validate(data)

        OfferValidator.validate_product(
            product,
            start,
            end
        )
        return ProductOffer.objects.create(
            product=product,
            name=data.get("name"),
            discount_percentage=data.get("discount_percentage"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
        )

    @staticmethod
    def update(offer, data):

        product = get_object_or_404(
            Product,
            id=data.get("product")
        )

        start, end = OfferValidator.validate(data,offer)

        OfferValidator.validate_product(
            product,
            start,
            end,
            offer
        )

        offer.product = product
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