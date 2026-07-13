from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from io import BytesIO
from typing import TYPE_CHECKING

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, Min, Prefetch, Q, Sum,F
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from apps.coupons.models import Coupon
from apps.coupons.services.coupon_services import CouponService
from apps.common.decorators import admin_required
from apps.users.models import Address

from .forms import ProductForm
from .models import (
    Brand,
    Cart,
    CartItem,
    Category,
    Order,
    OrderItem,
    Product,
    ProductImage,
    ProductVariant,
    Review,
    ReviewImage,
    WishlistItem,
    OrderAddress,
)
from .services import (
    add_to_cart,
    
    get_or_create_cart,
    move_to_cart,
    remove_cart_item,
    remove_wishlist_item,
    toggle_wishlist,
    update_cart_item,
)
from .utilitys import validate_cart,get_pricing,calculate_cart_totals
from django.utils import timezone
from apps.offers.models import ProductOffer
from apps.core.validators import validate_name
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

from weasyprint import HTML

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)



@admin_required
def category_list(request):
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status') or 'all'


    categories = Category.objects.all().annotate(
        product_count=Count('products')
    )

    if search:
        categories = categories.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    if status == 'active':
        categories = categories.filter(is_active=True)
    elif status == 'archived':
        categories = categories.filter(is_active=False)

    categories = categories.order_by('-id')

    paginator = Paginator(categories, 3)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'adminpanel/products/categories/category_list.html',
        {
            'categories': page_obj,
            'search_query': search,
            'status_filter': status,
        }
    )
def resize_image(image_file, size=(800, 800)):
    image = Image.open(image_file)
    image = image.convert("RGB")
    image.thumbnail(size)

    output = BytesIO()
    image.save(output, format="JPEG", quality=85)
    output.seek(0)

    return InMemoryUploadedFile(
        output,
        field_name="ImageField",
        name=f"{image_file.name.split('.')[0]}.jpg",
        content_type="image/jpeg",
        size=output.tell(),
        charset=None,
    )


@admin_required
@require_POST
def category_save(request):
    cat_id = request.POST.get('category_id')
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    image = request.FILES.get('category_image')

    # =========================
    # CHECK IMAGE TYPE
    # =========================
    if image and not image.content_type.startswith('image/'):
        messages.error(
            request,
            "Please upload a valid image file (jpg, png, jpeg, webp)."
        )
        return redirect('products:category_list')

    # =========================
    # CHECK DUPLICATE NAME
    # =========================
    qs = Category.objects.filter(name__iexact=name)

    if cat_id:
        qs = qs.exclude(id=cat_id)

    if qs.exists():
        messages.error(request, "Category name already exists.")
        return redirect('products:category_list')

    # =========================
    # RESIZE IMAGE
    # =========================
    resized_image = resize_image(image) if image else None

    try:
        # =========================
        # UPDATE
        # =========================
        if cat_id:
            category = get_object_or_404(Category, id=cat_id)

            category.name = name
            category.description = description

            if resized_image:
                category.image = resized_image

            success_message = "Category updated successfully."

        # =========================
        # CREATE
        # =========================
        else:
            category = Category(
                name=name,
                description=description,
                image=resized_image,
                is_active=True
            )

            success_message = "Category added successfully."

        # =========================
        # MODEL VALIDATION + SAVE
        # =========================
        category.full_clean()
        category.save()

        messages.success(request, success_message)

    except ValidationError as error:
        messages.error(request, error.messages[0])

    return redirect('products:category_list')

@admin_required
def category_toggle(request, pk):
    category = get_object_or_404(Category, id=pk)
    category.is_active = not category.is_active
    category.save()

    messages.success(
        request,
        f"Category {'activated' if category.is_active else 'archived'} successfully"
    )
    return redirect('products:category_list')


@admin_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)

    category.delete()

    messages.success(request, "Category deleted successfully.")
    return redirect('products:category_list')




@admin_required
def product_list(request):
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "all")
    category_id = request.GET.get("category")

    # =========================
    # BASE QUERY (FIXED + OPTIMIZED)
    # =========================
    products = (
        Product.objects
        .select_related("category")
        .prefetch_related(
            Prefetch(
                "variants",
                queryset=ProductVariant.objects.prefetch_related("images")
            )
        )
        .annotate(
            variant_count=Count("variants", distinct=True),
            total_stock=Sum("variants__stock"),
        )
    )

    # =========================
    # SEARCH
    # =========================
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) 
            
        )

    # =========================
    # STATUS FILTER
    # =========================
    if status == "active":
        products = products.filter(is_active=True)
    elif status == "archived":
        products = products.filter(is_active=False)

    # =========================
    # CATEGORY FILTER
    # =========================
    selected_category = None
    if category_id:
        try:
            selected_category = int(category_id)
            products = products.filter(category_id=selected_category)
        except (ValueError, TypeError):
            selected_category = None

    # =========================
    # ORDERING
    # =========================
    products = products.order_by("-created_at")

    # =========================
    # PAGINATION
    # =========================
    paginator = Paginator(products, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # =========================
    # CATEGORY LIST
    # =========================
    categories = Category.objects.filter(is_active=True)

    # =========================
    # RESPONSE
    # =========================
    return render(
        request,
        "adminpanel/products/products/product_list.html",
        {
            "products": page_obj,
            "categories": categories,
            "search_query": search,
            "status_filter": status,
            "selected_category": selected_category,
        },
    )






@admin_required
@transaction.atomic
def product_add(request):
    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    # =========================
    # POST
    # =========================
    if request.method == "POST":
        name = request.POST.get("name")
        category_id = request.POST.get("category")
        brand_id = request.POST.get("brand")
        description = request.POST.get("description")
        # highlights = request.POST.get("highlights")


        p_status = request.POST.get("product_status", "active")
        p_is_active = p_status == "active"

        sizes = request.POST.getlist("sizes")
        colors = request.POST.getlist("colors")
        skus = request.POST.getlist("skus")
        prices = request.POST.getlist("prices")
        stocks = request.POST.getlist("stocks")
        images = request.FILES.getlist("images")

        v_status = request.POST.get("variant_status", "active")
        v_is_active = v_status == "active"

        

        # -------------------------
        # IMAGE VALIDATION 
        # -------------------------
        allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]

        for img in images:
            if img.content_type not in allowed_types:
                messages.error(request, "Only image files (JPG, PNG, WEBP) are allowed.")
                return redirect("products:product_add")

            if img.size > 5 * 1024 * 1024:
                messages.error(request, "Image size must be less than 5MB.")
                return redirect("products:product_add")

        # -------------------------
        # VALIDATION
        # -------------------------
        if not name or not category_id:
            messages.error(request, "Name and category are required.")
            return redirect("products:product_add")

        if Product.objects.filter(name__iexact=name).exists():
            messages.error(request, "Product already exists!")
            return redirect("products:product_add")

        valid_variant_indexes = [i for i, s in enumerate(sizes) if s]

        if not valid_variant_indexes:
            messages.error(request, "At least one variant is required.")
            return redirect("products:product_add")
        # -------------------------
        # DUPLICATE VARIANT CHECK
        # -------------------------
        seen_variants = set()

        for i in valid_variant_indexes:

            size = sizes[i].strip().lower() if sizes[i] else ""
            color = colors[i].strip().lower() if colors[i] else ""

            variant_key = (size, color)

            if variant_key in seen_variants:
                messages.error(
                    request,
                    f"Duplicate variant found: Size '{sizes[i]}' and Color '{colors[i]}'."
                )
                return redirect("products:product_add")

            seen_variants.add(variant_key)
        
        

        # each variant needs 3 images
        expected_images = len(valid_variant_indexes) * 3
        if len(images) < expected_images:
            messages.error(request, "Each variant must have 3 images.")
            return redirect("products:product_add")

        # =========================
        # CREATE PRODUCT
        # =========================
        try:
            product = Product(
                name=name,
                category_id=category_id,
                brand_id=brand_id if brand_id else None,
                description=description,
                # highlights=highlights,
                is_active=p_is_active,
            )

            # Runs name and description validators
            product.full_clean()

            # Save only after validation passes
            product.save()

        except ValidationError as error:
            messages.error(request, error.messages[0])
            return redirect("products:product_add")

        # =========================
        # CREATE VARIANTS + IMAGES
        # =========================
        image_index = 0

        for i in valid_variant_indexes:

            
    

            variant = ProductVariant.objects.create(
                product=product,
                size=sizes[i],
                color=colors[i],
                sku=skus[i],
                price=float(prices[i]) if prices[i] else 0,
                
                stock=int(stocks[i]) if stocks[i] else 0,
                is_active=v_is_active,
            )

            # take 3 images for this variant
            variant_images = images[image_index:image_index + 3]

            for idx, img in enumerate(variant_images):
                resized_img = resize_image(img)  #  resize applied

                ProductImage.objects.create(
                    variant=variant,
                    image=resized_img,
                    is_primary=(idx == 0),
                )

            image_index += 3

        messages.success(request, "Product created successfully.")
        return redirect("products:product_list")

    # =========================
    # GET
    # =========================
    context = {
        "categories": categories,
        "variants": [],
        "product": None,
        'brands': brands,
    }

    return render(
        request,
        "adminpanel/products/products/product_add.html",
        context,
    )


@admin_required
@transaction.atomic
def product_edit(request, product_id=None):
    product = None
    variants = []

    if product_id:
        product = get_object_or_404(Product, id=product_id)
        variants = product.variants.all()

    categories = Category.objects.all()
    brands = Brand.objects.filter(is_active=True)

    # =========================
    # POST
    # =========================
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        highlights = request.POST.get("highlights")
        category_id = request.POST.get("category")
        brand_id = request.POST.get("brand")
        product_status = request.POST.get("product_status", "active")

        variant_ids = request.POST.getlist("variant_ids")
        sizes = request.POST.getlist("sizes")
        colors = request.POST.getlist("colors")
        skus = request.POST.getlist("skus")
        prices = request.POST.getlist("prices")
        # discount_percentage = request.POST.getlist("discount_percentage")
        stocks = request.POST.getlist("stocks")
        variant_statuses = request.POST.getlist("variant_status")
        delete_ids = request.POST.getlist("delete_variant_ids")

        category = get_object_or_404(Category, id=category_id)

        # =========================
        # SAVE / UPDATE PRODUCT FIRST
        # =========================
        try:
            # =========================
            # PREPARE PRODUCT
            # =========================
            if product:
                # UPDATE EXISTING PRODUCT
                product.name = name
                product.description = description
                product.highlights = highlights
                product.category = category
                product.brand_id = brand_id if brand_id else None
                product.is_active = True

                success_message = "Product updated successfully."

            else:
                # CREATE NEW PRODUCT
                product = Product(
                    name=name,
                    description=description,
                    highlights=highlights,
                    category=category,
                    brand_id=brand_id if brand_id else None,
                    is_active=True,
                )

                success_message = "Product added successfully."

            # =========================
            # MODEL VALIDATION
            # =========================
            product.full_clean()

            # =========================
            # SAVE ONLY IF VALID
            # =========================
            product.save()

            messages.success(request, success_message)

        except ValidationError as error:
            messages.error(request, error.messages[0])
        # =========================
        # DELETE VARIANTS
        # =========================
        if delete_ids:
            ProductVariant.objects.filter(
                id__in=delete_ids, product=product
            ).delete()
            messages.success(request, f"{len(delete_ids)} variants deleted successfully")

        # =========================
        # VARIANTS LOOP (CREATE / UPDATE)
        # =========================
        for i in range(len(skus)):
            sku = skus[i]

            if not sku:
                continue

            v_id = variant_ids[i] if i < len(variant_ids) else None

            # -------------------------
            # DUPLICATE SKU CHECK
            # -------------------------
            exists = ProductVariant.objects.filter(sku=sku)

            if v_id:
                exists = exists.exclude(id=v_id)

            if exists.exists():
                messages.error(request, f"SKU '{sku}' already exists.")
                return redirect(request.path)

            # -------------------------
            # VARIANT STATUS
            # -------------------------
            is_active_flag = (
                variant_statuses[i] == "true"
                if i < len(variant_statuses)
                else True
            )

            # -------------------------
            # UPDATE OR CREATE VARIANT
            # -------------------------
            if v_id:
                variant = get_object_or_404(
                    ProductVariant, id=v_id, product=product
                )

                variant.size = sizes[i]
                variant.color = colors[i]
                variant.sku = sku
                variant.price = float(prices[i]) if prices[i] else 0
                # variant.discount_percentage = (
                #     int(discount_percentage[i])
                #     if i < len(discount_percentage) and discount_percentage[i]
                #     else 0
                # )
                variant.stock = int(stocks[i]) if stocks[i] else 0
                variant.is_active = is_active_flag
                variant.save()

            else:
                variant = ProductVariant.objects.create(
                    product=product,
                    size=sizes[i],
                    color=colors[i],
                    sku=sku,
                    price=float(prices[i]) if prices[i] else 0,
                    # discount_percentage=(
                    #     int(discount_percentage[i])
                    #     if i < len(discount_percentage) and discount_percentage[i]
                    #     else 0
                    # ),
                    stock=int(stocks[i]) if stocks[i] else 0,
                    is_active=is_active_flag,
                )

            # =========================
            # IMAGE HANDLING
            # =========================
            id_for_files = v_id if v_id else f"new_{i}"

            existing_images = list(
                variant.images.all().order_by("id")
            )[:3]

            allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]

            for slot in range(3):
                file_key = f"variant_image_{id_for_files}_{slot}"
                image_file = request.FILES.get(file_key)

                if not image_file:
                    continue

                if image_file.content_type not in allowed_types:
                    messages.error(request, "Only JPG, PNG, WEBP allowed.")
                    return redirect(request.path)

                if image_file.size > 5 * 1024 * 1024:
                    messages.error(request, "Image must be < 5MB.")
                    return redirect(request.path)

                resized_img = resize_image(image_file)

                if len(existing_images) > slot:
                    img_obj = existing_images[slot]
                    img_obj.image = resized_img
                    img_obj.save()
                else:
                    ProductImage.objects.create(
                        variant=variant,
                        image=resized_img,
                        is_primary=(slot == 0),
                    )

        # =========================
        # 🔥 FINAL PRODUCT STATUS FIX
        # =========================
        has_variants = product.variants.exists()

        if not has_variants:
            product.is_active = False
        else:
            product.is_active = (product_status == "active")

        product.save()

        messages.success(request, "Product saved successfully.")
        

    # =========================
    # GET
    # =========================
    context = {
        "product": product,
        "variants": variants,
        "categories": categories,
        "brands": brands, 
    }

    return render(
        request,
        "adminpanel/products/products/product_edit.html",
        context,
    )

    

@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()  #  permanently removes from DB

    messages.success(request, "Product deleted permanently.")
    return redirect("products:product_list")


@admin_required
def product_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save()

    if product.is_active:
        messages.success(request, "Product activated successfully.")
    else:
        messages.success(request, "Product archived successfully.")

    return redirect("products:product_list")




@admin_required
def delete_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    variant.delete()
    messages.success(request, "Variant deleted successfully")
    return redirect(request.META.get('HTTP_REFERER', 'products:product_list'))


def user_product_list(request):
    """
    User-side product listing
    Supports search, filter, sort, pagination
    """

    # =====================================================
    # BASE QUERY — hide blocked/unlisted products
    # =====================================================
    products = (
        Product.objects
        .filter(
            is_active=True,
            category__is_active=True,
        )
        .select_related("category")
        .prefetch_related(
            Prefetch(
                "variants",
                queryset=ProductVariant.objects.prefetch_related("images"),
            ),
            Prefetch(
            "offers",
            queryset=ProductOffer.objects.filter(
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now(),
            ),
            to_attr="active_offers",
        ),

        )
        .distinct()
    )

    categories = Category.objects.filter(is_active=True)

    # =====================================================
    # SEARCH
    # =====================================================
    search = request.GET.get("search", "").strip()

    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    # =====================================================
    # CATEGORY FILTER
    # =====================================================
    category_id = request.GET.getlist("category")
    if category_id:
        products = products.filter(category__slug__in=category_id)

    # =====================================================
    # BRAND FILTER (OPTIONAL)
    # =====================================================
    brand = request.GET.get("brand")
    if brand and hasattr(Product, "brand"):
        products = products.filter(brand__iexact=brand)

    # =====================================================
    # PRICE FILTER
    # =====================================================
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    price_field = "variants__price"  # change if using variant pricing

    if min_price:
        products = products.filter(**{f"{price_field}__gte": min_price})

    if max_price:
        products = products.filter(**{f"{price_field}__lte": max_price})

    # =====================================================
    # SORTING
    # =====================================================
    sort = request.GET.get("sort")

    if sort == "price":
        products = products.order_by(price_field, "-id")

    elif sort == "-price":
        products = products.order_by(f"-{price_field}", "-id")

    elif sort == "name":
        products = products.order_by("name", "-id")

    elif sort == "-name":
        products = products.order_by("-name", "-id")

    else:
        products = products.order_by("-id")  # newest first

    # =====================================================
    # PAGINATION (ALWAYS LAST)
    # =====================================================
    paginator = Paginator(products, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # =====================================================
    # CONTEXT
    # =====================================================
    context = {
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "categories": categories,
        "search": search,
        "selected_category": category_id,
        "sort": sort,
        "min_price": min_price,
        "max_price": max_price,
        "brand": brand,
    }

    return render(request, "users/products/products_listing_page.html", context)

def user_product_detail(request, slug):
    # =====================================================
    # PRODUCT QUERY
    # =====================================================
    product = (
        Product.objects
        .filter(
            slug=slug,
            is_active=True,
            category__is_active=True,
        )
        .select_related("category")
        .prefetch_related(
            Prefetch(
                "variants",
                queryset=(
                    ProductVariant.objects
                    .filter(is_active=True)
                    .prefetch_related("images")
                ),
            ),
            #  Prefetch Reviews (Approved Only)
            Prefetch(
                "reviews",
                queryset=(
                    Review.objects
                    .filter(is_approved=True)
                    .select_related("user")
                    .prefetch_related("images")
                    .order_by("-created_at")
                )
            ),
        )
        .first()
    )

    # =====================================================
    # INVALID PRODUCT
    # =====================================================
    if not product:
        messages.error(request, "Product is unavailable.")
        return redirect("products:users_product_listing")

    # =====================================================
    # VARIANTS
    # =====================================================
    variants_qs = product.variants.all()

    has_stock = variants_qs.filter(stock__gt=0).exists()

    default_variant = (
        variants_qs
        .filter(stock__gt=0)
        .order_by("price")
        .first()
    )
    

    if not default_variant:
        default_variant = variants_qs.order_by("price").first()

    pricing = get_pricing(default_variant) if default_variant else None

    # =====================================================
    #  REVIEWS SECTION
    # =====================================================

    all_reviews = product.reviews.all()  # already approved & optimized

    # Pagination (5 reviews per page)
    paginator = Paginator(all_reviews, 5)
    page_number = request.GET.get("page")
    reviews = paginator.get_page(page_number)

    # Average Rating
    avg_rating = all_reviews.aggregate(
        avg=Avg("rating")
    )["avg"] or 0

    # Review Count
    review_count = all_reviews.count()

    # =====================================================
    # RELATED PRODUCTS
    # =====================================================
    related_products = (
        Product.objects
        .filter(
            category=product.category,
            is_active=True,
            category__is_active=True,
            variants__is_active=True,
        )
        .exclude(id=product.id)
        .select_related("category")
        .prefetch_related(
            Prefetch(
                "variants",
                queryset=(
                    ProductVariant.objects
                    .filter(is_active=True)
                    .prefetch_related("images")
                    .order_by("price")
                ),
            )
        )
        .annotate(min_price=Min("variants__price"))
        .order_by("min_price")
        .distinct()
        [:4]
    )

    # =====================================================
    # CONTEXT
    # =====================================================
    context = {
        "product": product,
        "has_stock": has_stock,
        "default_variant": default_variant,
        "related_products": related_products,
        "avg_rating": avg_rating,
        "review_count": review_count,
        "reviews": reviews,
        "pricing": pricing,
    }

    return render(
        request,
        "users/products/products_details_page.html",
        context,
    )

@login_required
def add_or_edit_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)

    review = Review.objects.filter(
        product=product,
        user=request.user
    ).prefetch_related("images").first()

    if request.method == "POST":
        rating = request.POST.get("rating")
        title = request.POST.get("title")
        comment = request.POST.get("comment")
        images = request.FILES.getlist("images")

        if not rating or not comment:
            messages.error(request, "Rating and comment are required.")
            return redirect("products:users_product_detail", slug=product.slug)

        # =====================================================
        #  CREATE REVIEW
        # =====================================================
        if not review:
            if len(images) < 2:
                messages.error(request, "Minimum 2 images required.")
                return redirect("products:users_product_detail", slug=product.slug)

            if len(images) > 5:
                messages.error(request, "Maximum 5 images allowed.")
                return redirect("products:users_product_detail", slug=product.slug)

            review = Review.objects.create(
                product=product,
                user=request.user,
                rating=int(rating),
                title=title,
                comment=comment,
                is_approved=True
            )

            for img in images:
                ReviewImage.objects.create(
                    review=review,
                    image=img
                )

            messages.success(request, "Review added successfully!")

        # =====================================================
        #  UPDATE REVIEW
        # =====================================================
        else:
            review.rating = int(rating)
            review.title = title
            review.comment = comment
            review.save()

            # If new images uploaded → replace old ones
            if images:
                if len(images) < 2:
                    messages.error(request, "Minimum 2 images required.")
                    return redirect("products:users_product_detail", slug=product.slug)

                if len(images) > 5:
                    messages.error(request, "Maximum 5 images allowed.")
                    return redirect("products:users_product_detail", slug=product.slug)

                # Delete old images (Cloudinary auto delete if configured)
                review.images.all().delete()

                for img in images:
                    ReviewImage.objects.create(
                        review=review,
                        image=img
                    )

            messages.success(request, "Review updated successfully!")

        return redirect("products:users_product_detail", slug=product.slug)

    return redirect("products:users_product_detail", slug=product.slug)



@admin_required
def brand_list(request):
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    brands = Brand.objects.annotate(
        product_count=Count('products')
    ).order_by('-id')
    # Search
    if search_query:
        brands = brands.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    # Filter
    if status_filter == 'active':
        brands = brands.filter(is_active=True)
    elif status_filter == 'archived':
        brands = brands.filter(is_active=False)
    # Paination - 10 brands per page
    paginator = Paginator(brands, 3)
    page_number = request.GET.get('page')
    brands = paginator.get_page(page_number)
    context = {
        'brands': brands,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(
        request,
        'adminpanel/products/brand/brand_list.html',
        context
    )


@admin_required
def brand_save(request):
    if request.method != "POST":
        return redirect("products:brand_list")

    brand_id = request.POST.get("brand_id")
    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()

    try:
        if brand_id:
            brand = get_object_or_404(Brand, id=brand_id)

            brand.name = name
            brand.description = description

            success_message = "Brand updated successfully."

        else:
            brand = Brand(
                name=name,
                description=description,
                is_active=True,
            )

            success_message = "Brand added successfully."

        brand.full_clean()
        brand.save()

        messages.success(request, success_message)

    except ValidationError as error:
        messages.error(request, error.messages[0])

    return redirect("products:brand_list")

@admin_required
def brand_toggle(request, id):
    brand = get_object_or_404(Brand, id=id)

    brand.is_active = not brand.is_active
    brand.save(update_fields=['is_active'])

    return redirect('products:brand_list')
    


@admin_required
def brand_delete(request, id):
    if request.method != 'POST':
        messages.error(request, "Invalid request")
        return redirect('products:brand_list')

    brand = get_object_or_404(Brand, id=id)
    brand.delete()

    messages.success(request, "Brand deleted successfully")
    return redirect('products:brand_list')



# ===============================================
# Cart management
# ===============================================



# -------------------------
# Common handler
# -------------------------
def _handle_message(request, result):
    if result.get("status"):
        messages.success(request, result.get("message"))
    else:
        messages.error(request, result.get("message"))







    



# -------------------------
# Cart Page
# -------------------------
@login_required
def cart_view(request):

    cart = get_or_create_cart(request.user)

    invalid_items = validate_cart(cart)

    if invalid_items:

        for item in invalid_items:
            item.delete()

        messages.warning(
            request,
            "Some unavailable items were removed from your cart."
        )

        return redirect("products:cart_view")

    items = (
        cart.items
        .select_related(
            "product",
            "product__category",
            "variant",
        )
        .prefetch_related(
            "variant__images",
        )
    )

    subtotal = sum(
        item.subtotal
        for item in items
    )

    coupon_data = _handle_coupon(
        request=request,
        subtotal=subtotal,
    )

    totals = calculate_cart_totals(
        cart_items=items,
        discount_amount=coupon_data["discount_amount"],
    )

    context = {
        "cart_items": items,

        "totals": totals,

        "applied_coupon": coupon_data["applied_coupon"],

        "coupon_message": coupon_data["coupon_message"],

        "coupon_valid": coupon_data["coupon_valid"],
    }

    return render(
        request,
        "users/cart_management/cart_view.html",
        context,
    )




def _handle_coupon(
    request,
    subtotal
):

    data = {
        "discount_amount": Decimal("0.00"),
        "applied_coupon": "",
        "coupon_message": None,
        "coupon_valid": False,
    }

    # Apply / Remove actions
    if request.method == "POST":

        action = request.POST.get(
            "action"
        )

        if action == "apply_coupon":

            code = request.POST.get(
                "coupon_code",
                ""
            )

            result = (
                CouponService.apply_coupon(
                    request=request,
                    cart_total=subtotal,
                    code=code
                )
            )

            return _coupon_response(
                result
            )

        elif action == "remove_coupon":

            _clear_coupon_session(
                request
            )

            data.update({
                "coupon_message":
                    "Coupon removed"
            })

            return data


    # Restore existing coupon
    coupon_id = request.session.get(
        "coupon_id"
    )

    if not coupon_id:
        return data

    try:

        coupon = Coupon.objects.get(
            id=coupon_id
        )

        result = (
            CouponService.apply_coupon(
                request=request,
                cart_total=subtotal,
                code=coupon.code
            )
        )

        if not result["success"]:

            _clear_coupon_session(
                request
            )

            return data

        return _coupon_response(
            result
        )

    except Coupon.DoesNotExist:

        _clear_coupon_session(
            request
        )

        return data


def _coupon_response(result):

    return {
        "discount_amount":
            result.get("discount", Decimal("0.00")),

        "applied_coupon":
            (
                result["coupon"].code
                if result.get("coupon")
                else ""
            ),

        "coupon_message":
            result.get("message"),

        "coupon_valid":
            result.get("success", False)
    }


def _clear_coupon_session(
    request
):

    request.session.pop(
        "coupon_id",
        None
    )

    request.session.pop(
        "coupon_code",
        None
    )

# -------------------------
# Add to Cart
# -------------------------

@login_required
def add_to_cart_view(request, product_id):
    
    # Only allow POST
    if request.method != "POST":
        return redirect("product_detail", product_id=product_id)

    

    product = get_object_or_404(Product, id=product_id)

    # Get form data
    variant_id = request.POST.get("variant")
    

    if not variant_id:
        messages.error(request, "Please select a variant")
        return redirect(request.META.get("HTTP_REFERER"))

    # Safe quantity parsing
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1

    # Fetch variant
    variant = product.variants.filter(id=variant_id).first()

    if not variant:
        messages.error(request, "Invalid variant")
        return redirect(request.META.get("HTTP_REFERER"))

    # Call service
    result = add_to_cart(
        user=request.user,
        product=product,
        variant=variant,
        quantity=quantity
    )

    # Handle response
    _handle_message(request, result)

    return redirect("products:cart_view")




# -------------------------
# Update Quantity
# -------------------------
@login_required
@require_POST
def update_cart_view(request, item_id, action):

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user,
    )

    # Save cart before item might be deleted
    cart = cart_item.cart

    result = update_cart_item(
        cart_item,
        action,
    )

    if not result.get("status"):

        if request.headers.get(
            "X-Requested-With"
        ) == "XMLHttpRequest":

            return JsonResponse(
                {
                    "success": False,
                    "error": result.get(
                        "message",
                        "Unable to update cart.",
                    ),
                },
                status=400,
            )

        return redirect(
            "products:cart_view"
        )

    # AJAX response
    if request.headers.get(
        "X-Requested-With"
    ) == "XMLHttpRequest":

        removed = False
        quantity = 0
        item_subtotal = "0.00"

        try:

            cart_item.refresh_from_db()

            quantity = cart_item.quantity

            item_subtotal = "{:.2f}".format(
                cart_item.subtotal
            )

        except CartItem.DoesNotExist:

            removed = True

        # Get latest cart items
        cart_items = (
            cart.items
            .select_related(
                "product",
                "variant",
            )
        )

        # Cart totals
        totals = calculate_cart_totals(
            cart_items=cart_items,
        )

        return JsonResponse(
            {
                "success": True,

                "removed": removed,

                "item_id": item_id,

                "quantity": quantity,

                "subtotal": item_subtotal,

                "cart_subtotal": "{:.2f}".format(
                    totals["subtotal"]
                ),

                "discount_amount": "{:.2f}".format(
                    totals["discount_amount"]
                ),

                "shipping_cost": "{:.2f}".format(
                    totals["shipping_cost"]
                ),

                "tax_amount": "{:.2f}".format(
                    totals["tax_amount"]
                ),

                "grand_total": "{:.2f}".format(
                    totals["grand_total"]
                ),

                "final_amount": "{:.2f}".format(
                    totals["final_amount"]
                ),

                "item_count": cart_items.count(),
            }
        )

    return redirect(
        "products:cart_view"
    )

# -------------------------
# Remove Item
# -------------------------
@login_required
@require_POST
def remove_cart_view(request, item_id):

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user,
    )

    cart = cart_item.cart

    result = remove_cart_item(
        request.user,
        cart_item,
    )

    if request.headers.get(
        "X-Requested-With"
    ) == "XMLHttpRequest":

        if not result.get("status"):

            return JsonResponse(
                {
                    "success": False,
                    "error": result.get(
                        "message",
                        "Remove failed.",
                    ),
                },
                status=400,
            )

        cart_items = (
            cart.items
            .select_related(
                "product",
                "variant",
            )
        )

        subtotal = sum(
            item.subtotal
            for item in cart_items
        )

        coupon_data = _handle_coupon(
            request=request,
            subtotal=subtotal,
        )

        totals = calculate_cart_totals(
            cart_items=cart_items,
            discount_amount=coupon_data[
                "discount_amount"
            ],
        )

        return JsonResponse(
            {
                "success": True,

                "removed": True,

                "item_id": item_id,

                "cart_subtotal": "{:.2f}".format(
                    totals["subtotal"]
                ),

                "discount_amount": "{:.2f}".format(
                    totals["discount_amount"]
                ),

                "shipping_cost": "{:.2f}".format(
                    totals["shipping_cost"]
                ),

                "tax_amount": "{:.2f}".format(
                    totals["tax_amount"]
                ),

                "grand_total": "{:.2f}".format(
                    totals["grand_total"]
                ),

                "final_amount": "{:.2f}".format(
                    totals["final_amount"]
                ),

                "item_count": cart_items.count(),
            }
        )

    return redirect(
        "products:cart_view"
    )

# ====================================================
# Whislist
# ====================================================

# -------------------------
# Add or Remove item 
# -------------------------
# views.py

@login_required
def toggle_wishlist_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variant_id = request.POST.get("variant_id")

    variant = None
    if variant_id:
        variant = ProductVariant.objects.filter(id=variant_id).first()

    result = toggle_wishlist(request.user, product, variant)

    _handle_message(request, result)

    return redirect(request.META.get("HTTP_REFERER", "home"))

# -------------------------
# Remove item 
# -------------------------

@login_required
def remove_wishlist_view(request, item_id):
    result = remove_wishlist_item(request.user, item_id)

    _handle_message(request, result)

    return redirect("products:wishlist")

# -------------------------
# Move to cart
# -------------------------


@login_required
def move_to_cart_view(request, item_id):
    item = get_object_or_404(WishlistItem, id=item_id, user=request.user)

    result = move_to_cart(
        request.user,
        item,
        get_or_create_cart
    )

    _handle_message(request, result)

    return redirect("products:wishlist")


# -------------------------
# Wishlist page view
# -------------------------

@login_required
def wishlist_view(request):
    items = WishlistItem.objects.filter(user=request.user)\
        .select_related("product", "variant")

    return render(request, "users/wishlist/wishlist.html", {
        "items": items
    })

@login_required
def checkout_view(request):

    cart = get_or_create_cart(
        request.user
    )

    items = (
        cart.items
        .select_related(
            "product",
            "product__category",
            "variant",
        )
    )

    invalid_items = []

    for item in items:

        if (
            not item.product.category.is_active
            or not item.product.is_active
            or not item.variant.is_active
            or item.variant.stock <= 0
        ):
            invalid_items.append(item)

    if invalid_items:

        for item in invalid_items:
            item.delete()

        messages.warning(
            request,
            "Some unavailable items were removed from your cart."
        )

        return redirect(
            "products:cart_view"
        )

    # Calculate subtotal
    subtotal = sum(
        item.subtotal
        for item in items
    )

    # Validate coupon
    coupon_data = _handle_coupon(
        request=request,
        subtotal=subtotal,
    )

    # Calculate all totals
    totals = calculate_cart_totals(
        cart_items=items,
        discount_amount=coupon_data[
            "discount_amount"
        ],
    )

    context = {

        "items": items,

        "addresses": Address.objects.filter(
            user=request.user
        ),

        "totals": totals,

        "applied_coupon":
            coupon_data[
                "applied_coupon"
            ],

        "coupon_message":
            coupon_data[
                "coupon_message"
            ],

        "coupon_valid":
            coupon_data[
                "coupon_valid"
            ],
    }

    return render(
        request,
        "users/checkout/checkout.html",
        context,
    )


@login_required
@transaction.atomic
def place_order(request):

    if request.method != "POST":
        return redirect("products:checkout")

    cart = get_or_create_cart(
        request.user
    )

    items = (
        cart.items
        .select_related(
            "product",
            "variant",
        )
    )

    if not items.exists():
        return redirect(
            "products:cart_view"
        )

    # Validate subtotal for coupon
    subtotal = sum(
        item.subtotal
        for item in items
    )

    coupon_data = _handle_coupon(
        request=request,
        subtotal=subtotal,
    )

    # Calculate final totals
    totals = calculate_cart_totals(
        cart_items=items,
        discount_amount=coupon_data[
            "discount_amount"
        ],
    )

    selected_address = Address.objects.get(
        id=request.POST.get("address"),
        user=request.user,
    )

    order_address = OrderAddress.objects.create(
        full_name=selected_address.full_name,
        phone=selected_address.phone,

        address_line_1=selected_address.address_line_1,
        address_line_2=selected_address.address_line_2,

        city=selected_address.city,
        state=selected_address.state,
        postal_code=selected_address.postal_code,
        country=selected_address.country,
    )

    payment_method = request.POST.get(
        "payment_method"
    )

    order = Order.objects.create(

        user=request.user,

        shipping_address=order_address,

        total_amount=totals[
            "subtotal"
        ],

        discount=totals[
            "discount_amount"
        ],

        shipping=totals[
            "shipping_cost"
        ],

        tax=totals[
            "tax_amount"
        ],

        final_amount=totals[
            "grand_total"
        ],

        payment_method=payment_method,

        status="PENDING",
    )

    for item in items:

        OrderItem.objects.create(

            order=order,

            product=item.product,

            variant=item.variant,

            quantity=item.quantity,

            price=item.price,
        )

    # Clear coupon after successful order
    request.session.pop(
        "coupon_id",
        None,
    )

    # Cash On Delivery
    if payment_method == "COD":

        for item in items:

            item.variant.stock -= (
                item.quantity
            )

            item.variant.save()

        items.delete()

        order.status = "CONFIRMED"

        order.save()

        return redirect(
            "products:order_success",
            order_id=order.id,
        )

    # Razorpay
    return redirect(
        "payments:start_payment",
        order_id=order.id,
    )


@login_required
def order_success(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    return render(
        request,
        "users/checkout/order_success.html",
        {"order": order}
    )


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        id=order_id,
        user=request.user
    )

    return_reasons = [
        "Wrong item received",
        "Damaged / defective product",
        "Size doesn't fit",
        "Changed my mind",
        "Late delivery",
    ]

    context = {
        "order": order,
        "return_reasons": return_reasons,
    }

    return render(
        request,
        "users/checkout/order_detail.html",
        context
    )


@login_required
def order_history(request):

    orders = (
        Order.objects
        .filter(
            user=request.user
        )
        .exclude(
            status__in=[
                "PENDING",
                "FAILED"
            ]
        )
        .prefetch_related(
            "items__product",
            "items__variant"
        )
        .order_by("-created_at")
    )

    statuses = (
        Order.STATUS_CHOICES
    )

    context = {

        "orders": orders,

        "statuses": statuses,
    }

    return render(
        request,
        "users/checkout/order_history.html",
        context
    )

@login_required
@transaction.atomic
def cancel_order_item(request, item_id):
    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order__user=request.user
    )

    # Allow only POST
    if request.method != "POST":
        return redirect(
            "products:order_detail",
            item.order.id
        )

    # Allowed statuses for cancellation
    cancellable_statuses = [
        "PENDING",
        "CONFIRMED",
        "PACKED",
    ]

    # Already cancelled
    if item.status == "CANCELLED":
        messages.warning(
            request,
            "This item is already cancelled."
        )
        return redirect(
            "products:order_detail",
            item.order.id
        )

    # Not allowed to cancel
    if item.status not in cancellable_statuses:
        messages.error(
            request,
            "This item cannot be cancelled now."
        )
        return redirect(
            "products:order_detail",
            item.order.id
        )

    # Cancel item
    item.status = "CANCELLED"
    item.save()

    # Restore stock
    if item.variant:
        item.variant.stock += item.quantity
        item.variant.save()

    # Check active items in same order
    active_items = item.order.items.exclude(
        status="CANCELLED"
    )

    # Update order status
    if active_items.exists():
        item.order.status = "PARTIAL_CANCELLED"
    else:
        item.order.status = "CANCELLED"

    item.order.save()

    messages.success(
        request,
        "Order item cancelled successfully."
    )

    return redirect(
        "products:order_detail",
        item.order.id
    )

@login_required
def return_order(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    # Allow only POST
    if request.method != "POST":
        return redirect("products:order_history")

    # Return allowed only after delivery
    if order.status != "DELIVERED":
        messages.error(
            request,
            "Return is only available for delivered orders."
        )
        return redirect("products:order_history")

    reason = request.POST.get(
        "reason",
        ""
    ).strip()

    if not reason:
        messages.error(
            request,
            "Return reason is required."
        )
        return redirect("products:order_history")

    # User requests return
    order.items.update(
        status="RETURN_REQUESTED",
        return_reason=reason
    )

    order.status = "RETURN_REQUESTED"
    order.save()

    messages.success(
        request,
        "Return request submitted successfully."
    )

    return redirect(
        "products:order_history"
    )



@login_required
@transaction.atomic
def return_order_item(request, item_id):
    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order__user=request.user
    )

    # Allow only POST
    if request.method != "POST":
        return redirect(
            "products:order_detail",
            order_id=item.order.id
        )

    # Return allowed only if item status is DELIVERED
    if item.status != "DELIVERED":
        messages.error(
            request,
            "This item cannot be returned."
        )
        return redirect(
            "products:order_detail",
            order_id=item.order.id
        )

    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(
            request,
            "Return reason is required."
        )
        return redirect(
            "products:order_detail",
            order_id=item.order.id
        )

    # Update item status
    item.status = "RETURN_REQUESTED"
    item.return_reason = reason
    item.save()

    # Update order status
    item.order.update_status()

    messages.success(
        request,
        f"Return request for {item.product.name} submitted successfully."
    )

    return redirect(
        "products:order_detail",
        order_id=item.order.id
    )



@login_required
def search_orders(request):
    query = request.GET.get("q", "").strip()

    orders = Order.objects.filter(
        user=request.user
    )

    if query:
        orders = orders.filter(
            order_id__icontains=query
        )

    orders = orders.order_by("-created_at")

    return render(
        request,
        "users/checkout/order_history.html",
        {"orders": orders, "query": query}
    )









# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
 
# INVOICE_BLOCKED_STATUSES: frozenset[str] = frozenset(
#     {
#         "PENDING",
#         "CANCELLED",
#         "RETURN_REQUESTED",
#         "RETURNED",
#         "REFUNDED",
#     }
# )
 
# # Brand palette
# _BRAND_BLACK = colors.HexColor("#111111")
# _BRAND_ACCENT = colors.HexColor("#1a1a2e")
# _HEADER_BG = colors.HexColor("#f5f5f5")
# _BORDER = colors.HexColor("#cccccc")
 
# # ---------------------------------------------------------------------------
# # Invoice builder
# # ---------------------------------------------------------------------------
 
 
# @dataclass
# class InvoiceBuilder:
#     """
#     Builds a ReportLab PDF invoice for a given Order.
 
#     Keeps all PDF-generation logic isolated from the view layer so it can
#     be reused in management commands, async tasks, or tests without an
#     HTTP request in scope.
 
#     Usage::
 
#         builder = InvoiceBuilder(order)
#         builder.build(response)   # writes PDF bytes into *response*
#     """
 
#     order: "Order"
#     _styles: dict = field(default_factory=dict, init=False, repr=False)
 
#     # ------------------------------------------------------------------
#     # Public API
#     # ------------------------------------------------------------------
 
#     def build(self, buffer) -> None:
#         """Render the full invoice PDF into *buffer*."""
#         doc = SimpleDocTemplate(
#             buffer,
#             pagesize=A4,
#             rightMargin=15 * mm,
#             leftMargin=15 * mm,
#             topMargin=15 * mm,
#             bottomMargin=12 * mm,
#         )
#         self._styles = self._build_styles()
#         doc.build(self._collect_elements())
 
#     # ------------------------------------------------------------------
#     # Private helpers
#     # ------------------------------------------------------------------
 
#     def _build_styles(self) -> dict:
#         base = getSampleStyleSheet()
#         extra = {
#             "brand_title": ParagraphStyle(
#                 "brand_title",
#                 parent=base["Title"],
#                 fontSize=26,
#                 textColor=_BRAND_BLACK,
#                 spaceAfter=2,
#                 fontName="Helvetica-Bold",
#             ),
#             "brand_subtitle": ParagraphStyle(
#                 "brand_subtitle",
#                 parent=base["Normal"],
#                 fontSize=10,
#                 textColor=colors.HexColor("#666666"),
#                 spaceAfter=0,
#             ),
#             "section_heading": ParagraphStyle(
#                 "section_heading",
#                 parent=base["Heading2"],
#                 fontSize=11,
#                 textColor=_BRAND_BLACK,
#                 spaceBefore=10,
#                 spaceAfter=4,
#                 fontName="Helvetica-Bold",
#             ),
#             "body": ParagraphStyle(
#                 "body",
#                 parent=base["Normal"],
#                 fontSize=9,
#                 leading=14,
#             ),
#             "footer": ParagraphStyle(
#                 "footer",
#                 parent=base["Normal"],
#                 fontSize=8,
#                 textColor=colors.HexColor("#888888"),
#                 alignment=1,  # centre
#             ),
#         }
#         base.add(extra["brand_title"])
#         base.add(extra["brand_subtitle"])
#         base.add(extra["section_heading"])
#         base.add(extra["body"])
#         base.add(extra["footer"])
#         return base
 
#     def _collect_elements(self) -> list:
#         elements: list = []
#         elements += self._header_section()
#         elements += self._invoice_meta_section()
#         elements += self._customer_section()
#         elements += self._address_section()
#         elements += self._line_items_section()
#         elements += self._totals_section()
#         elements += self._footer_section()
#         return elements
 
#     # ---- Header -----------------------------------------------------------
 
#     def _header_section(self) -> list:
#         return [
#             Paragraph("GAMEWEAR", self._styles["brand_title"]),
#             Paragraph("Premium Fashion Store", self._styles["brand_subtitle"]),
#             Spacer(1, 4 * mm),
#             HRFlowable(
#                 width="100%",
#                 thickness=1.5,
#                 color=_BRAND_BLACK,
#                 spaceAfter=4 * mm,
#             ),
#         ]
 
#     # ---- Invoice meta -----------------------------------------------------
 
#     def _invoice_meta_section(self) -> list:
#         order = self.order
#         data = [
#             ["Invoice Number", str(order.order_id)],
#             ["Order Date", order.created_at.strftime("%d %B %Y")],
#             ["Order Status", order.get_status_display()],
#             ["Payment Method", order.payment_method],
#         ]
#         table = Table(data, colWidths=[60 * mm, 110 * mm])
#         table.setStyle(
#             TableStyle(
#                 [
#                     ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
#                     ("FONTSIZE", (0, 0), (-1, -1), 9),
#                     ("BACKGROUND", (0, 0), (0, -1), _HEADER_BG),
#                     ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
#                     ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
#                     ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.white]),
#                     ("TOPPADDING", (0, 0), (-1, -1), 5),
#                     ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
#                 ]
#             )
#         )
#         return [table, Spacer(1, 6 * mm)]
 
#     # ---- Customer ---------------------------------------------------------
 
#     def _customer_section(self) -> list:
#         user = self.order.user
#         return [
#             Paragraph("Bill To", self._styles["section_heading"]),
#             Paragraph(
#                 f"<b>{getattr(user, 'full_name', str(user))}</b>",
#                 self._styles["body"],
#             ),
#             Paragraph(user.email, self._styles["body"]),
#             Spacer(1, 4 * mm),
#         ]
 
#     # ---- Shipping address -------------------------------------------------
 
#     def _address_section(self) -> list:
#         """Render shipping address from the order.address FK."""
#         address = self.order.shipping_address
#         if not address:
#             return []
#         # Build a readable single line from Address fields — adjust field
#         # names below if your Address model uses different attribute names.
#         parts = [
#             getattr(address, "full_name", ""),
#             getattr(address, "address_line1", "") or getattr(address, "street", ""),
#             getattr(address, "address_line2", "") or "",
#             getattr(address, "city", ""),
#             getattr(address, "state", ""),
#             getattr(address, "pincode", "") or getattr(address, "postal_code", ""),
#         ]
#         address_str = ", ".join(p for p in parts if p)
#         return [
#             Paragraph("Ship To", self._styles["section_heading"]),
#             Paragraph(address_str or str(address), self._styles["body"]),
#             Spacer(1, 4 * mm),
#         ]
 
#     # ---- Line items -------------------------------------------------------
 
#     def _line_items_section(self) -> list:
#         header = [["#", "Product", "Qty", "Unit Price", "Total"]]
#         rows = [
#             [
#                 str(idx),
#                 item.product.name,
#                 str(item.quantity),
#                 f"\u20b9{item.price:,.2f}",
#                 f"\u20b9{item.price * item.quantity:,.2f}",
#             ]
#             for idx, item in enumerate(self.order.items.select_related("product"), 1)
#         ]
#         col_widths = [10 * mm, 80 * mm, 20 * mm, 35 * mm, 35 * mm]
#         table = Table(header + rows, colWidths=col_widths, repeatRows=1)
#         table.setStyle(
#             TableStyle(
#                 [
#                     # Header row
#                     ("BACKGROUND", (0, 0), (-1, 0), _BRAND_ACCENT),
#                     ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
#                     ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
#                     ("FONTSIZE", (0, 0), (-1, -1), 9),
#                     ("ALIGN", (0, 0), (-1, 0), "CENTER"),
#                     # Data rows
#                     ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
#                     ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _HEADER_BG]),
#                     ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
#                     ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
#                     ("TOPPADDING", (0, 0), (-1, -1), 5),
#                     ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
#                 ]
#             )
#         )
#         return [
#             Paragraph("Order Items", self._styles["section_heading"]),
#             table,
#             Spacer(1, 4 * mm),
#         ]
 
#     # ---- Totals -----------------------------------------------------------
 
#     def _totals_section(self) -> list:

#         order = self.order

#         subtotal_after_discount = (
#             order.total_amount - order.discount
#         )

#         rows = [

#             [
#                 "Subtotal",
#                 f"₹{order.total_amount:,.2f}"
#             ],

#             [
#                 "Coupon Discount",
#                 f"- ₹{order.discount:,.2f}"
#             ],

#             [
#                 "Subtotal After Discount",
#                 f"₹{subtotal_after_discount:,.2f}"
#             ],

#             [
#                 "Shipping",
#                 (
#                     "Free"
#                     if order.shipping == 0
#                     else f"₹{order.shipping:,.2f}"
#                 )
#             ],

#             [
#                 "GST (5%)",
#                 f"₹{order.tax:,.2f}"
#             ],

#             [
#                 "Grand Total",
#                 f"₹{order.final_amount:,.2f}"
#             ],
#         ]

#         table = Table(
#             rows,
#             colWidths=[
#                 110 * mm,
#                 70 * mm,
#             ],
#         )

#         table.setStyle(
#             TableStyle(
#                 [

#                     ("FONTSIZE",(0,0),(-1,-1),9),

#                     ("ALIGN",(1,0),(1,-1),"RIGHT"),

#                     ("GRID",(0,0),(-1,-1),0.5,_BORDER),

#                     ("TOPPADDING",(0,0),(-1,-1),5),

#                     ("BOTTOMPADDING",(0,0),(-1,-1),5),

#                     ("BACKGROUND",(0,-1),(-1,-1),_BRAND_ACCENT),

#                     ("TEXTCOLOR",(0,-1),(-1,-1),colors.white),

#                     ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),

#                 ]
#             )
#         )

#         return [
#             table,
#             Spacer(
#                 1,
#                 8 * mm,
#             ),
#         ]
 
#     # ---- Footer -----------------------------------------------------------
 
#     def _footer_section(self) -> list:
#         return [
#             HRFlowable(width="100%", thickness=0.5, color=_BORDER, spaceAfter=3 * mm),
#             Paragraph(
#                 "Thank you for shopping with GAMEWEAR.",
#                 self._styles["footer"],
#             ),
#             Paragraph(
#                 "This is a computer-generated invoice and does not require a signature.",
#                 self._styles["footer"],
#             ),
#         ]
 
 
# # ---------------------------------------------------------------------------
# # View
# # ---------------------------------------------------------------------------
 
 
# @login_required
# def download_invoice(request: HttpRequest, order_id: int) -> HttpResponse:
#     """
#     Stream a PDF invoice for *order_id* to the authenticated user.
 
#     Returns a 302 redirect with an error message when the order
#     is not in a billable state.
#     """
#     order: Order = get_object_or_404(Order, id=order_id, user=request.user)
 
#     if order.status in INVOICE_BLOCKED_STATUSES:
#         messages.error(request, "Invoice is not available for this order.")
#         return redirect("products:order_detail", order_id=order.id)  # adjust kwarg to match your order_detail URL
 
#     try:
#         response = HttpResponse(content_type="application/pdf")
#         response["Content-Disposition"] = (
#             f'attachment; filename="Invoice-{order.order_id}.pdf"'
#         )
#         InvoiceBuilder(order).build(response)
#     except Exception:
#         logger.exception(
#             "Failed to generate invoice for order %s (user=%s)",
#             order.order_id,
#             request.user.id,
#         )
        
        
#         messages.error(
#             request,
#             "We could not generate your invoice right now. Please try again later.",
#         )
#         return redirect("products:order_detail", order_id=order.id)
 
#     return response





INVOICE_BLOCKED_STATUSES: frozenset[str] = frozenset(
    {
        "PENDING",
        "CANCELLED",
        "RETURN_REQUESTED",
        "RETURNED",
        "REFUNDED",
    }
)


@login_required
def download_invoice(request, order_id):

    order = get_object_or_404(
        Order.objects
        .select_related(
            "user",
            "shipping_address",
        )
        .prefetch_related(
            "items__product",
            "items__variant",
        ),
        id=order_id,
        user=request.user,
    )

    if order.status in INVOICE_BLOCKED_STATUSES:
        messages.error(
            request,
            "Invoice is not available for this order."
        )

        return redirect(
            "products:order_detail",
            order_id=order.id,
        )

    try:
        context = {
            "order": order,
            "items": order.items.all(),
        }

        html_string = render_to_string(
            "users/orders/order_invoice_pdf.html",
            context,
            request=request,
        )

        pdf = HTML(
            string=html_string,
            base_url=request.build_absolute_uri("/"),
        ).write_pdf()

        response = HttpResponse(
            pdf,
            content_type="application/pdf",
        )

        response["Content-Disposition"] = (
            f'attachment; filename="Invoice-{order.order_id}.pdf"'
        )

        return response

    except Exception:

        logger.exception(
            "Failed to generate invoice for order %s (user=%s)",
            order.order_id,
            request.user.id,
        )

        messages.error(
            request,
            "We could not generate your invoice right now. Please try again later.",
        )

        return redirect(
            "products:order_detail",
            order_id=order.id,
        )



# -------------------------
# Admin orders listing
# -------------------------

@admin_required
def admin_order_list(request):

    orders = Order.objects.select_related(
        "user"
    ).order_by("-created_at")

    search = request.GET.get("search")

    if search:
        orders = orders.filter(
            Q(order_id__icontains=search) |
            Q(user__email__icontains=search)
        )

    status = request.GET.get("status")

    if status:
        orders = orders.filter(status=status)

    sort = request.GET.get("sort")

    if sort == "oldest":
        orders = orders.order_by("created_at")

    paginator = Paginator(orders, 5)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj
    }

    return render(
        request,
        "adminpanel/orders/order_list.html",
        context
    )


@admin_required
def admin_order_detail(request, order_id):

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items__variant__images",
            "items__variant__product",
        ),
        id=order_id
    )

    steps = [
        "PENDING",
        "CONFIRMED",
        "PACKED",
        "SHIPPED",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
    ]
    return_items = order.items.filter(
        status="RETURN_REQUESTED"
    )

    context = {
        "order": order,
        "steps": steps,
        "return_items": return_items,
    }

    return render(
        request,
        "adminpanel/orders/order_detail.html",
        context
    )

@admin_required
def admin_update_order_status(request, order_id):
    """Handles fulfillment-only status transitions for the whole order.

    Return / refund workflows are handled per-item from the order detail page.
    """

    # Statuses that can be set from this page (fulfillment flow only)
    FULFILLMENT_STATUSES = [
        "PENDING",
        "CONFIRMED",
        "PACKED",
        "SHIPPED",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
        "CANCELLED",
    ]

    FULFILLMENT_CHOICES = [
        (value, label)
        for value, label in Order.STATUS_CHOICES
        if value in FULFILLMENT_STATUSES
    ]

    order = get_object_or_404(
        Order.objects.prefetch_related("items__variant"),
        id=order_id
    )

    if request.method != "POST":
        return render(
            request,
            "adminpanel/orders/update_order_status.html",
            {
                "order": order,
                "status_choices": FULFILLMENT_CHOICES,
            }
        )

    new_status = request.POST.get("status")

    # Guard: only fulfillment statuses are accepted here
    if new_status not in FULFILLMENT_STATUSES:
        messages.error(
            request,
            "Invalid status. Return and refund actions must be performed "
            "from the order detail page."
        )
        return redirect(
            "products:admin_update_order_status",
            order_id=order.id
        )

    ALLOWED_TRANSITIONS = {
        "PENDING":           ["CONFIRMED", "CANCELLED"],
        "CONFIRMED":         ["PACKED", "CANCELLED"],
        "PACKED":            ["SHIPPED", "CANCELLED"],
        "SHIPPED":           ["OUT_FOR_DELIVERY", "CANCELLED"],
        "OUT_FOR_DELIVERY":  ["DELIVERED"],
        "DELIVERED":         [],
        "CANCELLED":         [],
        # Partial-cancelled orders can be pushed forward or fully cancelled
        "PARTIAL_CANCELLED": ["CONFIRMED", "PACKED", "SHIPPED",
                              "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED"],
    }

    current_status = order.status

    # Terminal states that this page cannot modify
    if current_status in ["CANCELLED", "REFUNDED", "PARTIAL_REFUNDED"]:
        messages.error(
            request,
            f"Orders with status '{current_status}' cannot be modified here."
        )
        return redirect(
            "products:admin_update_order_status",
            order_id=order.id
        )

    # Return/refund states should be handled on the order detail page
    if current_status in [
        "RETURN_REQUESTED", "RETURNED",
        "PARTIAL_RETURNED", "PARTIAL_REFUNDED",
    ]:
        messages.error(
            request,
            "This order has an active return/refund process. "
            "Please manage it from the order detail page."
        )
        return redirect(
            "products:admin_order_detail",
            order_id=order.id
        )

    if (
        new_status != current_status and
        new_status not in ALLOWED_TRANSITIONS.get(current_status, [])
    ):
        messages.error(
            request,
            f"Cannot change status from '{current_status}' to '{new_status}'."
        )
        return redirect(
            "products:admin_update_order_status",
            order_id=order.id
        )

    with transaction.atomic():

        if new_status == "CANCELLED":
            # Restore stock for all non-cancelled items
            for item in order.items.exclude(status="CANCELLED"):
                if item.variant:
                    item.variant.__class__.objects.filter(
                        pk=item.variant.pk
                    ).update(
                        stock=F("stock") + item.quantity
                    )
                item.status = "CANCELLED"
                item.save()
            order.update_status()

        else:
            # Normal fulfillment transition — push all non-terminal items forward
            order.items.exclude(
                status__in=["CANCELLED", "RETURNED", "REFUNDED"]
            ).update(status=new_status)
            order.status = new_status
            order.save()

    messages.success(
        request,
        f"Order status updated to '{new_status}' successfully."
    )

    return redirect(
        "products:admin_order_detail",
        order_id=order.id
    )


# -------------------------
# Per-item return / refund actions (called from Order Detail page)
# -------------------------

@admin_required
def admin_approve_return_item(request, item_id):
    """Approve a return request for a single OrderItem.

    - Restores variant stock.
    - Sets item status to RETURNED.
    - Recalculates parent order status.
    """
    if request.method != "POST":
        return redirect("products:admin_order_list")

    item = get_object_or_404(
        OrderItem.objects.select_related("order", "variant"),
        id=item_id
    )
    order = item.order

    if item.status != "RETURN_REQUESTED":
        messages.error(
            request,
            f"Item is not in 'Return Requested' state (current: {item.status})."
        )
        return redirect("products:admin_order_detail", order_id=order.id)

    with transaction.atomic():
        # Restore stock
        if item.variant:
            item.variant.__class__.objects.filter(
                pk=item.variant.pk
            ).update(
                stock=F("stock") + item.quantity
            )

        item.status = "RETURNED"
        item.save()
        order.update_status()

    messages.success(
        request,
        "Return approved. Item marked as Returned and stock restored."
    )
    return redirect("products:admin_order_detail", order_id=order.id)


@admin_required
def admin_reject_return_item(request, item_id):
    """Reject a return request for a single OrderItem.

    - Reverts item status back to DELIVERED.
    - Recalculates parent order status.
    """
    if request.method != "POST":
        return redirect("products:admin_order_list")

    item = get_object_or_404(
        OrderItem.objects.select_related("order"),
        id=item_id
    )
    order = item.order

    if item.status != "RETURN_REQUESTED":
        messages.error(
            request,
            f"Item is not in 'Return Requested' state (current: {item.status})."
        )
        return redirect("products:admin_order_detail", order_id=order.id)

    with transaction.atomic():
        item.status = "DELIVERED"
        item.save()
        order.update_status()

    messages.success(
        request,
        "Return request rejected. Item reverted to Delivered."
    )
    return redirect("products:admin_order_detail", order_id=order.id)


@admin_required
def admin_refund_item(request, item_id):
    """Refund a single returned OrderItem to the customer's wallet.

    - Calculates proportional refund amount using item.refund_amount.
    - Credits the wallet via WalletService.
    - Sets item status to REFUNDED.
    - Recalculates parent order status.
    """
    if request.method != "POST":
        return redirect("products:admin_order_list")

    item = get_object_or_404(
        OrderItem.objects.select_related("order", "order__user"),
        id=item_id
    )
    order = item.order

    if item.status != "RETURNED":
        messages.error(
            request,
            f"Item must be in 'Returned' state to issue a refund "
            f"(current: {item.status})."
        )
        return redirect("products:admin_order_detail", order_id=order.id)

    from decimal import Decimal
    from apps.wallet.models import Wallet
    from apps.wallet.services.wallet_service import WalletService
    import uuid as _uuid

    refund_amount = item.refund_amount

    with transaction.atomic():
        item.status = "REFUNDED"
        item.save()

        wallet, _ = Wallet.objects.get_or_create(user=order.user)

        WalletService.credit_wallet(
            wallet=wallet,
            amount=refund_amount,
            description=(
                f"Refund for item '{item.variant.product.name if item.variant else 'Unknown'}' "
                f"from order {order.order_id}"
            ),
            reference_id=f"REF-{_uuid.uuid4().hex[:8].upper()}",
        )

        order.update_status()

    messages.success(
        request,
        f"\u20b9{refund_amount} refunded to customer's wallet for item "
        f"'{item.variant.product.name if item.variant else 'Unknown'}'."
    )
    return redirect("products:admin_order_detail", order_id=order.id)