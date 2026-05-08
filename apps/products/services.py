from .models import Cart, CartItem,WishlistItem
from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP



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

# ===================
# Whislist
# ===================

def toggle_wishlist(user, product, variant=None):
    item, created = WishlistItem.objects.get_or_create(
        user=user,
        product=product,
        variant=variant
    )

    if not created:
        item.delete()
        return _response(False, "Removed from wishlist")

    return _response(True, "Added to wishlist")


def remove_wishlist_item(user, item_id):
    try:
        item = WishlistItem.objects.get(id=item_id, user=user)
        item.delete()
        return _response(True, "Removed from wishlist")
    except WishlistItem.DoesNotExist:
        return _response(False, "Item not found")


def move_to_cart(user, item, get_or_create_cart):
    cart = get_or_create_cart(user)

    # ✅ Get correct price
    if item.variant:
        price = item.variant.price
    else:
        return _response(False, "Variant required for this product")

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=item.product,
        variant=item.variant,
        defaults={
            "quantity": 1,
            "price": price
        }
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save(update_fields=["quantity"])

    # Delete wishlist item after moving
    item.delete()

    return _response(True, "Moved to cart")





def calculate_cart_totals(cart_items):
    subtotal = sum(item.quantity * item.price for item in cart_items)

    subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    tax = (subtotal * Decimal("0.05")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    shipping = Decimal("50.00") if subtotal < Decimal("1000.00") else Decimal("0.00")
    discount = Decimal("0.00")

    final = (subtotal + tax + shipping - discount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return {
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping,
        "discount": discount,
        "final": final
    }