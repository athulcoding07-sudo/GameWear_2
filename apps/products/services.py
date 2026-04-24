from .models import Cart, CartItem
from django.db import transaction



# ===================
# Cart management
# ===================

MAX_QUANTITY = 5


# -------------------------
# Helpers
# -------------------------
def _response(status, message):
    return {
        "status": status,
        "message": message
    }


def get_or_create_cart(user):
    return Cart.objects.get_or_create(user=user)[0]


# -------------------------
# Add to Cart
# -------------------------
@transaction.atomic
def add_to_cart(user, product, variant, quantity=1):
    # Product validation
    if not product.is_active:
        return _response(False, "Product not available")

    # Stock validation
    if variant.stock <= 0:
        return _response(False, "Out of stock")

    if quantity > variant.stock:
        return _response(False, "Stock limit exceeded")

    if quantity > MAX_QUANTITY:
        return _response(False, "Max limit reached")

    # Get cart
    cart = get_or_create_cart(user)

    # Lock row for safety (avoid race condition)
    cart_item, created = CartItem.objects.select_for_update().get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        defaults={
            "price": variant.price,
            "quantity": 0
        }
    )

    new_quantity = cart_item.quantity + quantity

    # Re-check limits
    if new_quantity > variant.stock:
        return _response(False, "Stock limit exceeded")

    if new_quantity > MAX_QUANTITY:
        return _response(False, "Max limit reached")

    cart_item.quantity = new_quantity
    cart_item.save()

    return _response(True, "Added to cart")

# -------------------------
# Update Quantity
# -------------------------
def update_cart_item(cart_item, action):
    variant = cart_item.variant

    if action == "increase":
        new_quantity = cart_item.quantity + 1

        if new_quantity > variant.stock:
            return _response(False, "Stock exceeded")

        if new_quantity > MAX_QUANTITY:
            return _response(False, "Max limit reached")

        cart_item.quantity = new_quantity
        cart_item.save()
        return _response(True, "Cart updated")

    elif action == "decrease":
        new_quantity = cart_item.quantity - 1

        if new_quantity <= 0:
            cart_item.delete()
            return _response(True, "Item removed")

        cart_item.quantity = new_quantity
        cart_item.save()
        return _response(True, "Cart updated")

    return _response(False, "Invalid action")


# -------------------------
# Remove Item
# -------------------------
def remove_cart_item(user, cart_item):
    if cart_item.cart.user != user:
        return _response(False, "Unauthorized")

    cart_item.delete()
    return _response(True, "Item removed")