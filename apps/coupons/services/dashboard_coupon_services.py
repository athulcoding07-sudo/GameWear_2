from apps.coupons.forms.coupon_forms import CouponForm

from apps.coupons.selectors.coupon_selectors import (
    get_coupon_by_id,
)


class CouponDashboardService:

    @staticmethod
    def create_coupon(data):

        form = CouponForm(data)

        if form.is_valid():

            form.save()

            return True, form

        return False, form

    @staticmethod
    def update_coupon(
        coupon,
        data,
    ):

        

        form = CouponForm(
            data,
            instance=coupon,
        )

        if form.is_valid():

            form.save()

            return True, form

        return False, form

    @staticmethod
    def delete_coupon(coupon_id):

        coupon = get_coupon_by_id(coupon_id)

        if coupon:

            coupon.delete()

            return True

        return False