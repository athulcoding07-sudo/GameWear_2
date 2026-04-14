from django.shortcuts import render,redirect,get_object_or_404
from django.core.paginator import Paginator
from .models import Category,ProductImage,Product,ProductVariant,Review,ReviewImage
from .forms import ProductForm
from django.views.decorators.http import require_POST
from django.contrib import messages
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from django.db.models import Q,Count,Sum,Prefetch,Min,Avg
from django.db import transaction
from django.contrib.auth.decorators import login_required
from apps.common.decorators import admin_required



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

from django.views.decorators.http import require_POST
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages

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
            Q(description__icontains=search) |
            Q(brand__icontains=search)
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

    # =========================
    # POST
    # =========================
    if request.method == "POST":
        name = request.POST.get("name")
        category_id = request.POST.get("category")
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
                resized_img = resize_image(img)  # ⭐ resize applied

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

    # =========================
    # POST
    # =========================
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        highlights = request.POST.get("highlights")
        category_id = request.POST.get("category")
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
        return redirect("products:product_list")

    # =========================
    # GET
    # =========================
    context = {
        "product": product,
        "variants": variants,
        "categories": categories,
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
            # 🔥 Prefetch Reviews (Approved Only)
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
    # 🚨 INVALID PRODUCT
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
    # ⭐ REVIEWS SECTION
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