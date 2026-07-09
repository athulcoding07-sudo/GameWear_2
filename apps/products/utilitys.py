from decimal import Decimal,ROUND_HALF_UP
from django.utils import timezone

from apps.offers.models import ProductOffer, CategoryOffer


def get_pricing(variant):
    now = timezone.now()

    product_offer = ProductOffer.objects.filter(
        product=variant.product,
        is_active=True,
        start_date__lte=now,
        end_date__gte=now,
    ).first()

    category_offer = CategoryOffer.objects.filter(
        category=variant.product.category,
        is_active=True,
        start_date__lte=now,
        end_date__gte=now,
    ).first()
    print("\n========== OFFER DEBUG ==========")
    print("NOW:", now)

    print("\nALL PRODUCT OFFERS:")
    for offer in ProductOffer.objects.filter(product=variant.product):
        print(
            "NAME:", offer.name,
            "| ACTIVE:", offer.is_active,
            "| START:", offer.start_date,
            "| END:", offer.end_date,
            "| VALID:", offer.is_valid,
        )

    print("\nALL CATEGORY OFFERS:")
    for offer in CategoryOffer.objects.filter(
        category=variant.product.category
    ):
        print(
            "NAME:", offer.name,
            "| ACTIVE:", offer.is_active,
            "| START:", offer.start_date,
            "| END:", offer.end_date,
            "| VALID:", offer.is_valid,
        )

    print("=================================\n")

    offer = None

    if product_offer and category_offer:
        offer = (
            product_offer
            if product_offer.discount_percentage >= category_offer.discount_percentage
            else category_offer
        )
    else:
        offer = product_offer or category_offer

    percentage = Decimal(
        offer.discount_percentage if offer else 0
    )

    original_price = variant.price

    offer_price = (
        original_price -
        (original_price * percentage / Decimal("100"))
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    

    return {
        "original_price": original_price,
        "discount_percentage": percentage,
        "offer_price": offer_price,
        
        "offer": offer,
    }


def validate_cart(cart):
    invalid_items = []

    for item in cart.items.select_related(
        "product",
        "product__category",
        "variant"
    ):

        if (
            not item.product.category.is_active or
            not item.product.is_active or
            not item.variant.is_active or
            item.variant.stock <= 0 or
            item.quantity > item.variant.stock
        ):
            invalid_items.append(item)

    return invalid_items

FREE_SHIPPING_LIMIT = Decimal("1000.00")
SHIPPING_CHARGE = Decimal("50.00")
TAX_RATE = Decimal("0.05")


def calculate_cart_totals(
    cart_items,
    discount_amount=Decimal("0.00"),
):
    """
    Calculate complete cart totals.

    Grand Total = Final payable amount.
    """

    subtotal = sum(
        (item.subtotal for item in cart_items),
        Decimal("0.00"),
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    discount_amount = Decimal(
        discount_amount
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    subtotal_after_discount = max(
        subtotal - discount_amount,
        Decimal("0.00"),
    )

    shipping_cost = (
        Decimal("0.00")
        if subtotal_after_discount >= FREE_SHIPPING_LIMIT
        else SHIPPING_CHARGE
    )

    tax_amount = (
        subtotal_after_discount * TAX_RATE
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    grand_total = (
        subtotal_after_discount
        + shipping_cost
        + tax_amount
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    return {
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "subtotal_after_discount": subtotal_after_discount,
        "shipping_cost": shipping_cost,
        "tax_amount": tax_amount,
        "grand_total": grand_total,
        "final_amount": grand_total,
    }