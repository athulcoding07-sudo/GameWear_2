from apps.coupons.models import Coupon


def get_coupon_by_id(coupon_id):

    return Coupon.objects.filter(
        id=coupon_id
    ).first()


def get_coupon_by_code(code):

    return Coupon.objects.filter(
        code__iexact=code
    ).first()


def get_all_coupons(status=None):

    queryset = Coupon.objects.all()

    if status == 'active':
        queryset = queryset.filter(is_active=True)
    elif status == 'inactive':
        queryset = queryset.filter(is_active=False)
    # 'all' or None returns all coupons

    return queryset