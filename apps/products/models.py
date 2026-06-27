import uuid
from django.db import models, transaction
from django.utils.text import slugify
from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db.models import Avg
from django.core.exceptions import ValidationError
from apps.users.models import User,Address

# Create your models here.



User = settings.AUTH_USER_MODEL

# =========================
# Category
# =========================

class Category(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(unique=True, blank=True, db_index=True)
    description = models.TextField(blank=True)

    #  Make image optional (VERY IMPORTANT)
    image = CloudinaryField(
        "category",
        folder="category/images",
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):   # 👈 WRITE HERE
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1

        while Brand.objects.filter(slug=slug).exclude(id=self.id).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# =========================
# Product
# =========================
class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
    )
    brand = models.ForeignKey(
        'Brand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True, db_index=True)
    description = models.TextField(blank=True)
    highlights = models.TextField(blank=True, null=True)
    

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_listed = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "is_listed"]),
        ]
    @property
    def average_rating(self):
        return self.reviews.filter(is_approved=True).aggregate(
            avg=Avg("rating")
        )["avg"] or 0

    @property
    def review_count(self):
        return self.reviews.filter(is_approved=True).count()

    #  Bonus: Rating Breakdown
    def rating_breakdown(self):
        return {
            star: self.reviews.filter(is_approved=True, rating=star).count()
            for star in range(1, 6)
        }

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name





class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )

    size = models.CharField(max_length=20)
    color = models.CharField(max_length=50)

    sku = models.CharField(max_length=100, unique=True, blank=True, db_index=True)

    # original price
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # discount percentage
    discount_percentage = models.PositiveIntegerField(default=0)

    # final price after discount
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    stock = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "size", "color"],
                name="unique_variant_per_product",
            )
        ]
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["product", "is_active"]),
        ]

    def generate_sku(self):
        product_part = (self.product.name[:3] if self.product else "PRD").upper()
        size_part = (self.size or "NA").upper()
        color_part = (self.color or "NA").upper()
        return f"JER-{product_part}-{size_part}-{color_part}-{uuid.uuid4().hex[:4].upper()}"

    def clean(self):
        if self.discount_percentage > 100:
            raise ValidationError("Discount percentage cannot be more than 100")

    def save(self, *args, **kwargs):

        if not self.sku:
            self.sku = self.generate_sku()

        # calculate discount price
        if self.discount_percentage > 0:
            discount_amount = (self.price * self.discount_percentage) / 100
            self.discount_price = self.price - discount_amount
        else:
            self.discount_price = self.price

        # auto deactivate if stock is zero
        self.is_active = self.stock > 0

        super().save(*args, **kwargs)


    @property
    def final_price(self):
        return self.discount_price or self.price

    def __str__(self):
        return f"{self.product.name} - {self.size} - {self.color}"




class ProductImage(models.Model):
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = CloudinaryField("product_image", folder="products/images")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["variant"],
                condition=models.Q(is_primary=True),
                name="one_primary_image_per_variant",
            )
        ]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_primary:
                ProductImage.objects.filter(
                    variant=self.variant,
                    is_primary=True,
                ).exclude(pk=self.pk).update(is_primary=False)

            super().save(*args, **kwargs)

    def __str__(self):
        return f"Image of {self.variant.product.name}"


class Review(models.Model):
    RATING_CHOICES = [
        (1, "1 Star"),
        (2, "2 Stars"),
        (3, "3 Stars"),
        (4, "4 Stars"),
        (5, "5 Stars"),
    ]

    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=150, blank=True)
    comment = models.TextField()

    is_approved = models.BooleanField(default=True)  # For admin moderation
    is_verified_purchase = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("product", "user")  # One review per product per user
        indexes = [
            models.Index(fields=["product", "rating"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.product} ({self.rating}★)"


class ReviewImage(models.Model):
    review = models.ForeignKey(
        "Review",
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = CloudinaryField("r_image", folder="products/r_images")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Image for Review {self.review.id}"


# =========================
# Cart management
# =========================


class Cart(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

    def __str__(self):
        return f"Cart({self.user})"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        "Cart",
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        related_name="cart_items"
    )
    variant = models.ForeignKey(
    "ProductVariant",
    on_delete=models.CASCADE,
    null=True,
    blank=True
)

    quantity = models.PositiveIntegerField(default=1)

    # snapshot price (important for price consistency)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product", "variant"],  
                name="unique_cart_product_variant"
            )
        ]
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"

    def __str__(self):
        return f"{self.product.name} ({self.variant}) x {self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.price


class WishlistItem(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="wishlist_items"
    )
    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        related_name="wishlist_products"
    )
    variant = models.ForeignKey(
        "ProductVariant",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product", "variant"],
                name="unique_user_product_variant_wishlist"
            )
        ]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self):
        return f"{self.user} ❤️ {self.product} ({self.variant})"





class Order(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("CONFIRMED", "Confirmed"),
        ("PACKED", "Packed"),
        ("SHIPPED", "Shipped"),
        ("OUT_FOR_DELIVERY", "Out for Delivery"),
        ("DELIVERED", "Delivered"),

        ("CANCELLED", "Cancelled"),
        ("PARTIAL_CANCELLED", "Partial Cancelled"),

        ("RETURN_REQUESTED", "Return Requested"),
        ("RETURNED", "Returned"),
        ("PARTIAL_RETURNED", "Partial Returned"),

        ("REFUNDED", "Refunded"),
    )

    PAYMENT_METHOD_CHOICES = (
        ("COD", "Cash On Delivery"),
        ("RAZORPAY", "Razorpay"),
    )

    order_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    shipping_address = models.OneToOneField(
        "OrderAddress",
        on_delete=models.PROTECT,
        related_name="order",
        null=True,
        blank=True,
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    shipping = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    final_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="COD"
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def update_status(self):
        items = self.items.all()

        if all(item.status == "CANCELLED" for item in items):
            self.status = "CANCELLED"

        elif any(item.status == "CANCELLED" for item in items):
            self.status = "PARTIAL_CANCELLED"

        elif all(item.status == "RETURNED" for item in items):
            self.status = "RETURNED"

        elif any(item.status == "RETURNED" for item in items):
            self.status = "PARTIAL_RETURNED"

        elif all(item.status == "DELIVERED" for item in items):
            self.status = "DELIVERED"

        self.save()

    def __str__(self):
        return self.order_id


class OrderItem(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("CONFIRMED", "Confirmed"),
        ("PACKED", "Packed"),
        ("SHIPPED", "Shipped"),
        ("OUT_FOR_DELIVERY", "Out for Delivery"),
        ("DELIVERED", "Delivered"),

        ("CANCELLED", "Cancelled"),

        ("RETURN_REQUESTED", "Return Requested"),
        ("RETURNED", "Returned"),

        ("REFUNDED", "Refunded"),
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True
    )

    quantity = models.PositiveIntegerField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    cancellation_reason = models.TextField(
        blank=True,
        null=True
    )

    return_reason = models.TextField(
        blank=True,
        null=True
    )
    @property
    def total_price(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.order.order_id} - {self.product.name}"
    

class OrderAddress(models.Model):

    full_name = models.CharField(
        max_length=255
    )

    phone = models.CharField(
        max_length=20
    )

    address_line_1 = models.CharField(
        max_length=255
    )

    address_line_2 = models.CharField(
        max_length=255,
        blank=True
    )

    city = models.CharField(
        max_length=100
    )

    state = models.CharField(
        max_length=100
    )

    postal_code = models.CharField(
        max_length=20
    )

    country = models.CharField(
        max_length=100,
        default="India"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.full_name} - {self.city}"