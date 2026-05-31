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