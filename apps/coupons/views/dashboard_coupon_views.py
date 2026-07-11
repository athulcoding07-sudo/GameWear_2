import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from apps.common.decorators import admin_required

from apps.coupons.forms.coupon_forms import CouponForm

from apps.coupons.selectors.coupon_selectors import (
    get_all_coupons,
    get_coupon_by_id,
)

from apps.coupons.services.dashboard_coupon_services import (
    CouponDashboardService,
)


@admin_required
def coupon_list_view(request):
    coupons = get_all_coupons()

    # AJAX table refresh
    if request.GET.get("ajax"):
        html = render_to_string(
            "adminpanel/coupons/partials/table_rows.html",
            {
                "coupons": coupons,
            },
            request=request,
        )

        return JsonResponse({
            "success": True,
            "html": html,
        })

    context = {
        "coupons": coupons,
    }

    return render(
        request,
        "adminpanel/coupons/coupons_list.html",
        context,
    )


@admin_required
@require_http_methods(["POST"])
def coupon_create_view(request):
    data = json.loads(request.body)

    form = CouponForm(data)

    if not form.is_valid():
        return JsonResponse(
            {
                "success": False,
                "errors": form.errors,
            },
            status=400,
        )
    coupon = form.save(commit=False)
    coupon.is_active = True
    coupon.save()

    CouponDashboardService.create_coupon(
        form.cleaned_data,
    )

    messages.success(
        request,
        "Coupon created successfully",
    )

    return JsonResponse({
        "success": True,
        "message": "Coupon created successfully",
    })


@admin_required
@require_http_methods(["GET", "POST"])
def coupon_update_view(request, coupon_id):
    coupon = get_coupon_by_id(coupon_id)

    # AJAX fetch single coupon
    if request.method == "GET" and request.GET.get("ajax"):

        return JsonResponse({
            "success": True,
            "coupon": {
                "id": coupon.id,
                "code": coupon.code,
                "discount_percentage": str(
                    coupon.discount_percentage
                ),
                "minimum_amount": str(
                    coupon.minimum_amount
                ),
                "maximum_discount": str(
                    coupon.maximum_discount
                ),
                "valid_from": coupon.valid_from.strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                        
                "valid_to": coupon.valid_to.strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "is_active": coupon.is_active,
            }
        })

    # AJAX update coupon
    data = json.loads(request.body)

    form = CouponForm(
        data,
        instance=coupon,
    )

    if not form.is_valid():
        return JsonResponse(
            {
                "success": False,
                "errors": form.errors,
            },
            status=400,
        )
    coupon = form.save(commit=False)
    coupon.is_active = True
    coupon.save()

    CouponDashboardService.update_coupon(
        coupon,
        form.cleaned_data,
    )

    messages.success(
        request,
        "Coupon updated successfully",
    )

    return JsonResponse({
        "success": True,
        "message": "Coupon updated successfully",
    })


@admin_required
@require_http_methods(["DELETE"])
def coupon_delete_view(request, coupon_id):
    CouponDashboardService.delete_coupon(
        coupon_id,
    )

    messages.success(
        request,
        "Coupon deleted successfully",
    )

    return JsonResponse({
        "success": True,
        "message": "Coupon deleted successfully",
    })


@admin_required
@require_http_methods(["POST"])
def coupon_toggle_status_view(request, coupon_id):
    coupon = get_coupon_by_id(coupon_id)

    coupon.is_active = not coupon.is_active
    coupon.save(
        update_fields=["is_active"],
    )

    return JsonResponse({
        "success": True,
        "message": "Coupon status updated successfully",
        "is_active": coupon.is_active,
        
    })