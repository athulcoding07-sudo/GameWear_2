from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.offers.models import (
    ProductOffer,
    CategoryOffer,
    
)

from apps.products.models import Product, Category

from apps.offers.services.product_offer_service import ProductOfferService
from apps.offers.services.category_offer_service import CategoryOfferService
from django.http import JsonResponse



import json

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from apps.products.models import Product, Category
from apps.offers.models import ProductOffer
from apps.offers.services.product_offer_service import ProductOfferService


def _parse_body(request):
    """
    Accepts either JSON body (from fetch()) or a regular POST form body.
    Returns a plain dict either way so it can be handed straight to
    ProductOfferService / OfferValidator unchanged.
    """
    if request.content_type == "application/json":
        try:
            return json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return {}
    return request.POST.dict()


def product_offer_list(request):
    """
    Renders the Product Offers page. If called with ?ajax=1, returns just
    the rendered table body HTML (used by refreshTable() in the JS).
    """
    offers = ProductOfferService.get_all()

    search = request.GET.get("search", "").strip()
    if search:
        offers = offers.filter(name__icontains=search)

    status = request.GET.get("status", "all")
    if status == "active":
        offers = offers.filter(is_active=True)
    elif status == "inactive":
        offers = offers.filter(is_active=False)

    if request.GET.get("ajax") == "1":
        html = render_to_string(
            "adminpanel/offers/partials/product_offer_rows.html",
            {"offers": offers},
            request=request,
        )
        return JsonResponse({"html": html})

    categories = Category.objects.filter(is_active=True)

    return render(
        request,
        "adminpanel/offers/product_offer_list.html",
        {
            "offers": offers,
            "categories": categories,
        },
    )


@require_http_methods(["POST"])
def product_offer_create(request):
    data = _parse_body(request)

    try:
        ProductOfferService.create(data)
    except ValidationError as e:
        return JsonResponse(
            {"success": False, "errors": {"__all__": [str(e.message if hasattr(e, 'message') else e)]}},
            status=400,
        )

    return JsonResponse({"success": True, "message": "Product offer created successfully."})


def product_offer_update(request, pk):
    offer = get_object_or_404(ProductOffer, pk=pk)

    if request.method == "GET" and request.GET.get("ajax") == "1":
        return JsonResponse(
            {
                "offer": {
                    "name": offer.name,
                    "category_id": offer.product.category_id,
                    "product_id": offer.product_id,
                    "discount_percentage": str(offer.discount_percentage),
                    "start_date": offer.start_date.strftime("%Y-%m-%dT%H:%M"),
                    "end_date": offer.end_date.strftime("%Y-%m-%dT%H:%M"),
                    "is_active": offer.is_active,
                }
            }
        )

    if request.method == "POST":
        data = _parse_body(request)
        try:
            ProductOfferService.update(offer, data)
        except ValidationError as e:
            return JsonResponse(
                {"success": False, "errors": {"__all__": [str(e.message if hasattr(e, 'message') else e)]}},
                status=400,
            )
        return JsonResponse({"success": True, "message": "Product offer updated successfully."})

    return JsonResponse({"success": False, "message": "Invalid request."}, status=400)


@require_http_methods(["DELETE"])
def product_offer_delete(request, pk):
    offer = get_object_or_404(ProductOffer, pk=pk)
    ProductOfferService.delete(offer)
    return JsonResponse({"success": True, "message": "Product offer deleted."})


@require_http_methods(["POST"])
def product_offer_toggle(request, pk):
    offer = get_object_or_404(ProductOffer, pk=pk)
    ProductOfferService.toggle(offer)
    status_word = "activated" if offer.is_active else "deactivated"
    return JsonResponse({"success": True, "message": f"Offer {status_word}."})


def products_by_category(request, category_id):
    products = Product.objects.filter(
        category_id=category_id,
        is_active=True,
    ).values("id", "name")
    return JsonResponse({"products": list(products)})


# ============================================================
# Category Offers
# ============================================================

def category_offer_list(request):

    offers = CategoryOfferService.get_all()
    categories = Category.objects.filter(is_active=True)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":

        html = render_to_string(
            "adminpanel/offers/partials/category_offer_rows.html",
            {"offers": offers},
            request=request,
        )

        return JsonResponse({
            "success": True,
            "html": html,
        })

    return render(
        request,
        "adminpanel/offers/category_offer_list.html",
        {
            "offers": offers,
            "categories": categories,
        },
    )


@require_http_methods(["POST"])
def category_offer_add(request):

    try:
        data = json.loads(request.body)

        CategoryOfferService.create(data)

        return JsonResponse({
            "success": True,
            "message": "Category offer created successfully.",
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e),
        }, status=400)


@require_http_methods(["GET", "POST"])
def category_offer_edit(request, pk):

    offer = get_object_or_404(CategoryOffer, pk=pk)

    if request.method == "GET":
        return JsonResponse({
            "offer": {
                "id": offer.id,
                "name": offer.name,
                "category_id": offer.category_id,
                "discount_percentage": str(offer.discount_percentage),
                "start_date": offer.start_date.strftime("%Y-%m-%dT%H:%M") if offer.start_date else "",
                "end_date": offer.end_date.strftime("%Y-%m-%dT%H:%M") if offer.end_date else "",
                "is_active": offer.is_active,
            }
        })

    try:
        data = json.loads(request.body)
        CategoryOfferService.update(offer, data)
        return JsonResponse({
            "success": True,
            "message": "Category offer updated successfully.",
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e),
        }, status=400)


@require_http_methods(["POST"])
def category_offer_toggle(request, pk):
    offer = get_object_or_404(CategoryOffer, pk=pk)

    CategoryOfferService.toggle(offer)

    status_word = (
        "activated"
        if offer.is_active
        else "deactivated"
    )

    return JsonResponse({
        "success": True,
        "message": f"Offer {status_word}.",
    })


@require_http_methods(["DELETE"])
def category_offer_delete(request, pk):

    offer = get_object_or_404(CategoryOffer, pk=pk)

    CategoryOfferService.delete(offer)

    return JsonResponse({
        "success": True,
        "message": "Category offer deleted successfully.",
    })


