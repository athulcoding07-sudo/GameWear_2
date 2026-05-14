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
from django.db.models import Avg, Count, Min, Prefetch, Q, Sum
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
)
from .services import (
    add_to_cart,
    calculate_cart_totals,
    get_or_create_cart,
    move_to_cart,
    remove_cart_item,
    remove_wishlist_item,
    toggle_wishlist,
    update_cart_item,
)

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

    paginator = Paginator(categories, 5)
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

    if not name:
        messages.error(request, "Category name is required")
        return redirect('products:category_list')

    # =========================
    # CHECK IMAGE TYPE 
    # =========================
    if image:
        if not image.content_type.startswith('image/'):
            messages.error(request, "Please upload a valid image file (jpg, png, jpeg, webp)")
            return redirect('products:category_list')

    qs = Category.objects.filter(name__iexact=name)

    if cat_id:
        qs = qs.exclude(id=cat_id)

    if qs.exists():
        messages.error(request, "Category name already exists")
        return redirect('products:category_list')

    # =========================
    # RESIZE IF IMAGE EXISTS
    # =========================
    resized_image = resize_image(image) if image else None

    # =========================
    # UPDATE
    # =========================
    if cat_id:
        category = get_object_or_404(Category, id=cat_id)
        category.name = name
        category.description = description

        if resized_image:
            category.image = resized_image

        category.save()
        messages.success(request, "Category updated successfully")

    # =========================
    # CREATE
    # =========================
    else:
        Category.objects.create(
            name=name,
            description=description,
            image=resized_image,
            is_active=True
        )
        messages.success(request, "Category added successfully")

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
        highlights = request.POST.get("highlights")


        p_status = request.POST.get("product_status", "active")
        p_is_active = p_status == "active"

        sizes = request.POST.getlist("sizes")
        colors = request.POST.getlist("colors")
        skus = request.POST.getlist("skus")
        prices = request.POST.getlist("prices")
        discount_percentage =request.POST.getlist("discount_percentage")
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

        # each variant needs 3 images
        expected_images = len(valid_variant_indexes) * 3
        if len(images) < expected_images:
            messages.error(request, "Each variant must have 3 images.")
            return redirect("products:product_add")

        # =========================
        # CREATE PRODUCT
        # =========================
        product = Product.objects.create(
            name=name,
            category_id=category_id,
            brand_id=brand_id if brand_id else None,
            description=description,
            highlights=highlights,
            is_active=p_is_active,
        )

        # =========================
        # CREATE VARIANTS + IMAGES
        # =========================
        image_index = 0

        for i in valid_variant_indexes:

            discount = 0
            if i < len(discount_percentage):
                discount = int(discount_percentage[i]) if discount_percentage[i] else 0

            


            variant = ProductVariant.objects.create(
                product=product,
                size=sizes[i],
                color=colors[i],
                sku=skus[i],
                price=float(prices[i]) if prices[i] else 0,
                discount_percentage=discount,
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
        discount_percentage = request.POST.getlist("discount_percentage")
        stocks = request.POST.getlist("stocks")
        variant_statuses = request.POST.getlist("variant_status")
        delete_ids = request.POST.getlist("delete_variant_ids")

        category = get_object_or_404(Category, id=category_id)

        # =========================
        # SAVE / UPDATE PRODUCT FIRST
        # =========================
        if product:
            product.name = name
            product.description = description
            product.highlights = highlights
            product.category = category
            product.brand_id = brand_id if brand_id else None
            product.save()
        else:
            product = Product.objects.create(
                name=name,
                description=description,
                highlights=highlights,
                category=category,
                is_active=True,  # temporary
            )

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
                variant.discount_percentage = (
                    int(discount_percentage[i])
                    if i < len(discount_percentage) and discount_percentage[i]
                    else 0
                )
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
                    discount_percentage=(
                        int(discount_percentage[i])
                        if i < len(discount_percentage) and discount_percentage[i]
                        else 0
                    ),
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
                queryset=ProductVariant.objects.prefetch_related("images")
            )
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

    #  Search
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

    context = {
        'brands': brands,
        'search_query': search_query,
        'status_filter': status_filter
    }

    return render(request, 'adminpanel/products/brand/brand_list.html', context)

@admin_required
def brand_save(request):
    if request.method != 'POST':
        return redirect('products:brand_list')

    brand_id = request.POST.get('brand_id')
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()

    # Validation
    if not name:
        messages.error(request, "Brand name is required")
        return redirect('products:brand_list')

    if not re.match(r'^[A-Za-z\s]+$', name):
        messages.error(request, "Brand name must contain only letters and spaces")
        return redirect('products:brand_list')

    #  Update
    if brand_id:
        brand = get_object_or_404(Brand, id=brand_id)
        brand.name = name
        brand.description = description
        brand.save()
        messages.success(request, "Brand updated successfully")

    #  Create
    else:
        if Brand.objects.filter(name__iexact=name).exists():
            messages.error(request, "Brand already exists")
            return redirect('products:brand_list')

        Brand.objects.create(
            name=name,
            description=description
        )
        messages.success(request, "Brand added successfully")

    return redirect('products:brand_list')


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
    
 
    # ── Coupon handling (POST) ────────────────────────────────────────────────
    coupon_message = None
    coupon_valid   = False
    applied_coupon = request.session.get("coupon_code", "")
    discount_amount = Decimal("0.00")
 
    if request.method == "POST" and request.POST.get("action") == "apply_coupon":
        code = request.POST.get("coupon_code", "").strip().upper()
 
        if code:
            # ── Stub: replace with real Coupon model lookup when ready ────────
            # try:
            #     coupon = Coupon.objects.get(code=code, is_active=True)
            #     request.session["coupon_code"] = code
            #     coupon_message = f'"{code}" applied — {coupon.discount_percentage}% off!'
            #     coupon_valid   = True
            # except Coupon.DoesNotExist:
            #     request.session.pop("coupon_code", None)
            #     coupon_message = "Invalid or expired promo code."
            #     coupon_valid   = False
            # ── End stub ─────────────────────────────────────────────────────
 
            # Temporary placeholder response until Coupon model exists:
            coupon_message = "Promo codes are not active yet. Check back soon!"
            coupon_valid   = False
        else:
            request.session.pop("coupon_code", None)
            applied_coupon = ""
 
    # ── Items ────────────────────────────────────────────────────────────────
    # select_related pulls product, variant, category, and variant images
    # in as few queries as possible.
    items = (
        cart.items
            .select_related("product", "product__category", "variant")
            .prefetch_related("variant__images")   # for primary image in template
    )
 
    # ── Totals ───────────────────────────────────────────────────────────────
    # item.subtotal  = item.quantity * item.price  (model property)
    subtotal = sum(item.subtotal for item in items)
 
    # Apply coupon discount (stub — wire up to real Coupon model later)
    # if coupon_valid:
    #     discount_amount = (subtotal * coupon.discount_percentage) / 100
 
    grand_total = subtotal - discount_amount
 
    # Shipping / tax are calculated at checkout; pass None so the template
    # renders "Calculated at checkout" gracefully.
    shipping_cost = None
    tax_amount    = None
 
    return render(request, "users/cart_management/cart_view.html", {
        "cart_items":      items,
 
        # ── Summary ──────────────────────────────────────────────────────────
        "subtotal":        subtotal,
        "discount_amount": discount_amount if discount_amount else None,
        "shipping_cost":   shipping_cost,
        "tax_amount":      tax_amount,
        "grand_total":     grand_total,
 
        # ── Coupon ───────────────────────────────────────────────────────────
        "applied_coupon":  applied_coupon,
        "coupon_message":  coupon_message,
        "coupon_valid":    coupon_valid,
    })

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
        cart__user=request.user
    )

    # Save cart reference BEFORE potential delete (decrease to 0 deletes the item)
    cart = cart_item.cart

    result = update_cart_item(cart_item, action)

    #  Fix #1: helper returns "status", not "success"
    if not result.get("status"):
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "error": result.get("message", "Update failed.")},
                status=400
            )
        return redirect("products:cart_view")

    # AJAX path
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":

        #  Fix #2: item may have been deleted by decrease-to-zero
        removed = False
        new_quantity = 0
        new_subtotal = "0.00"

        try:
            cart_item.refresh_from_db()
            new_quantity = cart_item.quantity
            #  Fix #3: compute subtotal manually — don't assume a model property
            new_subtotal = "{:.2f}".format(cart_item.quantity * cart_item.price)
            removed = False
        except CartItem.DoesNotExist:
            removed = True

        #  Fix #2: use the correct function name and key names
        cart_items = cart.items.select_related("variant").all()
        totals = calculate_cart_totals(cart_items)

        return JsonResponse({
            "success":         True,
            "removed":         removed,
            "item_id":         item_id,
            "quantity":        new_quantity,
            "subtotal":        new_subtotal,
            #  map to what the JS expects
            "cart_subtotal":   "{:.2f}".format(totals["subtotal"]),
            "discount_amount": "{:.2f}".format(totals["discount"]),
            "grand_total":     "{:.2f}".format(totals["final"]),
            "item_count":      cart_items.count(),
        })

    return redirect("products:cart_view")

# -------------------------
# Remove Item
# -------------------------
@login_required
@require_POST
def remove_cart_view(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )
    cart = cart_item.cart

    # Use the service — it also checks ownership
    result = remove_cart_item(request.user, cart_item)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if not result.get("status"):
            return JsonResponse(
                {"success": False, "error": result.get("message", "Remove failed.")},
                status=400
            )

        # Item is deleted — recount remaining items
        cart_items = cart.items.select_related("variant").all()
        totals = calculate_cart_totals(cart_items)

        return JsonResponse({
            "success":         True,
            "removed":         True,
            "item_id":         item_id,
            "cart_subtotal":   "{:.2f}".format(totals["subtotal"]),
            "discount_amount": "{:.2f}".format(totals["discount"]),
            "grand_total":     "{:.2f}".format(totals["final"]),
            "item_count":      cart_items.count(),
        })

    return redirect("products:cart_view")

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
    cart = get_or_create_cart(request.user)
    items = cart.items.all()

    addresses = Address.objects.filter(user=request.user)

    totals = calculate_cart_totals(items)

    context = {
        "items": items,
        "addresses": addresses,
        "totals": totals
    }

    return render(request, "users/checkout/checkout.html", context)


@login_required
def place_order(request):

    if request.method != "POST":
        return redirect("products:checkout")

    cart = get_or_create_cart(request.user)
    items = cart.items.select_related(
        "product",
        "variant"
    )

    if not items.exists():
        return redirect("products:cart_view")

    payment_method = request.POST.get(
        "payment_method"
    )

    address = Address.objects.get(
        id=request.POST.get("address"),
        user=request.user
    )

    totals = calculate_cart_totals(items)

    order = Order.objects.create(
        user=request.user,
        address=address,
        total_amount=totals["subtotal"],
        tax=totals["tax"],
        shipping=totals["shipping"],
        discount=totals["discount"],
        final_amount=totals["final"],
        payment_method=payment_method,
    )

    for item in items:

        OrderItem.objects.create(
            order=order,
            product=item.product,
            variant=item.variant,
            quantity=item.quantity,
            price=item.price
        )

        item.variant.stock -= item.quantity
        item.variant.save()

    items.delete()

    if payment_method == "COD":

        return redirect(
            "products:order_success",
            order_id=order.id
        )

    return redirect(
        "payments:checkout",
        order_id=order.id
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
        .filter(user=request.user)
        .prefetch_related("items__product", "items__variant")
        .order_by("-created_at")
    )

    statuses = Order.STATUS_CHOICES

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
 
INVOICE_BLOCKED_STATUSES: frozenset[str] = frozenset(
    {
        "PENDING",
        "CANCELLED",
        "RETURN_REQUESTED",
        "RETURNED",
        "REFUNDED",
    }
)
 
# Brand palette
_BRAND_BLACK = colors.HexColor("#111111")
_BRAND_ACCENT = colors.HexColor("#1a1a2e")
_HEADER_BG = colors.HexColor("#f5f5f5")
_BORDER = colors.HexColor("#cccccc")
 
# ---------------------------------------------------------------------------
# Invoice builder
# ---------------------------------------------------------------------------
 
 
@dataclass
class InvoiceBuilder:
    """
    Builds a ReportLab PDF invoice for a given Order.
 
    Keeps all PDF-generation logic isolated from the view layer so it can
    be reused in management commands, async tasks, or tests without an
    HTTP request in scope.
 
    Usage::
 
        builder = InvoiceBuilder(order)
        builder.build(response)   # writes PDF bytes into *response*
    """
 
    order: "Order"
    _styles: dict = field(default_factory=dict, init=False, repr=False)
 
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
 
    def build(self, buffer) -> None:
        """Render the full invoice PDF into *buffer*."""
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=12 * mm,
        )
        self._styles = self._build_styles()
        doc.build(self._collect_elements())
 
    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
 
    def _build_styles(self) -> dict:
        base = getSampleStyleSheet()
        extra = {
            "brand_title": ParagraphStyle(
                "brand_title",
                parent=base["Title"],
                fontSize=26,
                textColor=_BRAND_BLACK,
                spaceAfter=2,
                fontName="Helvetica-Bold",
            ),
            "brand_subtitle": ParagraphStyle(
                "brand_subtitle",
                parent=base["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#666666"),
                spaceAfter=0,
            ),
            "section_heading": ParagraphStyle(
                "section_heading",
                parent=base["Heading2"],
                fontSize=11,
                textColor=_BRAND_BLACK,
                spaceBefore=10,
                spaceAfter=4,
                fontName="Helvetica-Bold",
            ),
            "body": ParagraphStyle(
                "body",
                parent=base["Normal"],
                fontSize=9,
                leading=14,
            ),
            "footer": ParagraphStyle(
                "footer",
                parent=base["Normal"],
                fontSize=8,
                textColor=colors.HexColor("#888888"),
                alignment=1,  # centre
            ),
        }
        base.add(extra["brand_title"])
        base.add(extra["brand_subtitle"])
        base.add(extra["section_heading"])
        base.add(extra["body"])
        base.add(extra["footer"])
        return base
 
    def _collect_elements(self) -> list:
        elements: list = []
        elements += self._header_section()
        elements += self._invoice_meta_section()
        elements += self._customer_section()
        elements += self._address_section()
        elements += self._line_items_section()
        elements += self._totals_section()
        elements += self._footer_section()
        return elements
 
    # ---- Header -----------------------------------------------------------
 
    def _header_section(self) -> list:
        return [
            Paragraph("GAMEWEAR", self._styles["brand_title"]),
            Paragraph("Premium Fashion Store", self._styles["brand_subtitle"]),
            Spacer(1, 4 * mm),
            HRFlowable(
                width="100%",
                thickness=1.5,
                color=_BRAND_BLACK,
                spaceAfter=4 * mm,
            ),
        ]
 
    # ---- Invoice meta -----------------------------------------------------
 
    def _invoice_meta_section(self) -> list:
        order = self.order
        data = [
            ["Invoice Number", str(order.order_id)],
            ["Order Date", order.created_at.strftime("%d %B %Y")],
            ["Order Status", order.get_status_display()],
            ["Payment Method", order.payment_method],
        ]
        table = Table(data, colWidths=[60 * mm, 110 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (0, -1), _HEADER_BG),
                    ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.white]),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return [table, Spacer(1, 6 * mm)]
 
    # ---- Customer ---------------------------------------------------------
 
    def _customer_section(self) -> list:
        user = self.order.user
        return [
            Paragraph("Bill To", self._styles["section_heading"]),
            Paragraph(
                f"<b>{getattr(user, 'full_name', str(user))}</b>",
                self._styles["body"],
            ),
            Paragraph(user.email, self._styles["body"]),
            Spacer(1, 4 * mm),
        ]
 
    # ---- Shipping address -------------------------------------------------
 
    def _address_section(self) -> list:
        """Render shipping address from the order.address FK."""
        address = self.order.address
        if not address:
            return []
        # Build a readable single line from Address fields — adjust field
        # names below if your Address model uses different attribute names.
        parts = [
            getattr(address, "full_name", ""),
            getattr(address, "address_line1", "") or getattr(address, "street", ""),
            getattr(address, "address_line2", "") or "",
            getattr(address, "city", ""),
            getattr(address, "state", ""),
            getattr(address, "pincode", "") or getattr(address, "postal_code", ""),
        ]
        address_str = ", ".join(p for p in parts if p)
        return [
            Paragraph("Ship To", self._styles["section_heading"]),
            Paragraph(address_str or str(address), self._styles["body"]),
            Spacer(1, 4 * mm),
        ]
 
    # ---- Line items -------------------------------------------------------
 
    def _line_items_section(self) -> list:
        header = [["#", "Product", "Qty", "Unit Price", "Total"]]
        rows = [
            [
                str(idx),
                item.product.name,
                str(item.quantity),
                f"\u20b9{item.price:,.2f}",
                f"\u20b9{item.price * item.quantity:,.2f}",
            ]
            for idx, item in enumerate(self.order.items.select_related("product"), 1)
        ]
        col_widths = [10 * mm, 80 * mm, 20 * mm, 35 * mm, 35 * mm]
        table = Table(header + rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    # Header row
                    ("BACKGROUND", (0, 0), (-1, 0), _BRAND_ACCENT),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    # Data rows
                    ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _HEADER_BG]),
                    ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return [
            Paragraph("Order Items", self._styles["section_heading"]),
            table,
            Spacer(1, 4 * mm),
        ]
 
    # ---- Totals -----------------------------------------------------------
 
    def _totals_section(self) -> list:
        order = self.order
        rows: list[list] = []
 
        # order.total_amount = subtotal before discount/tax/shipping
        rows.append(["Subtotal", f"\u20b9{order.total_amount:,.2f}"])
 
        if order.discount:
            rows.append(["Discount", f"- \u20b9{order.discount:,.2f}"])
 
        if order.tax:
            rows.append(["Tax / GST", f"\u20b9{order.tax:,.2f}"])
 
        if order.shipping:
            rows.append(["Shipping", f"\u20b9{order.shipping:,.2f}"])
 
        rows.append(["Total Payable", f"\u20b9{order.final_amount:,.2f}"])
 
        col_widths = [110 * mm, 70 * mm]
        table = Table(rows, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    # Highlight total row
                    ("BACKGROUND", (0, -1), (-1, -1), _BRAND_ACCENT),
                    ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ]
            )
        )
        return [table, Spacer(1, 8 * mm)]
 
    # ---- Footer -----------------------------------------------------------
 
    def _footer_section(self) -> list:
        return [
            HRFlowable(width="100%", thickness=0.5, color=_BORDER, spaceAfter=3 * mm),
            Paragraph(
                "Thank you for shopping with GAMEWEAR.",
                self._styles["footer"],
            ),
            Paragraph(
                "This is a computer-generated invoice and does not require a signature.",
                self._styles["footer"],
            ),
        ]
 
 
# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------
 
 
@login_required
def download_invoice(request: HttpRequest, order_id: int) -> HttpResponse:
    """
    Stream a PDF invoice for *order_id* to the authenticated user.
 
    Returns a 302 redirect with an error message when the order
    is not in a billable state.
    """
    order: Order = get_object_or_404(Order, id=order_id, user=request.user)
 
    if order.status in INVOICE_BLOCKED_STATUSES:
        messages.error(request, "Invoice is not available for this order.")
        return redirect("products:order_detail", order_id=order.id)  # adjust kwarg to match your order_detail URL
 
    try:
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="Invoice-{order.order_id}.pdf"'
        )
        InvoiceBuilder(order).build(response)
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
        return redirect("products:order_detail", order_id=order.id)
 
    return response





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
        Order.objects.prefetch_related("items"),
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

    context = {
        "order": order,
        "steps": steps
    }

    return render(
        request,
        "adminpanel/orders/order_detail.html",
        context
    )

@admin_required
def admin_update_order_status(request, order_id):

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
                "status_choices": Order.STATUS_CHOICES
            }
        )

    new_status = request.POST.get("status")

    valid_statuses = dict(Order.STATUS_CHOICES)

    if new_status not in valid_statuses:
        messages.error(request, "Invalid status.")
        return redirect(
            "products:admin_order_detail",
            order_id=order.id
        )

    if order.status == "CANCELLED":
        messages.error(
            request,
            "Cancelled orders cannot be modified."
        )
        return redirect(
            "products:admin_order_detail",
            order_id=order.id
        )

    with transaction.atomic():

        if (
            new_status == "CANCELLED"
            and order.status != "CANCELLED"
        ):

            for item in order.items.all():

                if item.variant:
                    item.variant.stock = F("stock") + item.quantity
                    item.variant.save()

                item.status = "CANCELLED"
                item.save()

        elif (
            new_status == "RETURNED"
            and order.status != "RETURNED"
        ):

            return_items = order.items.filter(
                status="RETURN_REQUESTED"
            )

            for item in return_items:

                if item.variant:
                    item.variant.stock = F("stock") + item.quantity
                    item.variant.save()

                item.status = "RETURNED"
                item.save()

        else:

            order.items.exclude(
                status__in=["CANCELLED", "RETURNED"]
            ).update(
                status=new_status
            )

        order.status = new_status
        order.save()

    messages.success(
        request,
        "Order status updated successfully."
    )

    return redirect(
        "products:admin_order_detail",
        order_id=order.id
    )