from decimal import Decimal
from apps.coupons.models import Coupon


class CouponService:

    @staticmethod
    def apply_coupon(
        request,
        cart_total,
        code
    ):

        default_response = {
            "success": False,
            "message": None,
            "coupon": None,
            "discount": Decimal("0.00")
        }

        try:

            coupon = Coupon.objects.get(
                code__iexact=code.strip()
            )

        except Coupon.DoesNotExist:

            return {
                **default_response,
                "message":
                    "Invalid coupon code"
            }

        if not coupon.is_valid:

            return {
                **default_response,
                "message":
                    "Coupon expired or inactive"
            }

        if cart_total < coupon.minimum_amount:

            return {
                **default_response,
                "message":
                    f"Minimum amount ₹{coupon.minimum_amount}"
            }

        discount = (
            cart_total *
            Decimal(
                coupon.discount_percentage
            ) / 100
        )

        if coupon.maximum_discount:

            discount = min(
                discount,
                coupon.maximum_discount
            )

        request.session[
            "coupon_id"
        ] = coupon.id

        request.session[
            "coupon_code"
        ] = coupon.code

        return {
            "success": True,
            "message":
                "Coupon applied successfully",
            "coupon":
                coupon,
            "discount":
                discount
        }