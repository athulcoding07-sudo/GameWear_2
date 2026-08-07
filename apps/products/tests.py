from django.test import TestCase
from decimal import Decimal
from apps.products.models import Category, Product, ProductVariant

class ProductVariantModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Test Category",
            description="Test Category Description"
        )
        self.product = Product.objects.create(
            category=self.category,
            name="Test Product",
            description="Test Product Description"
        )

    def test_variant_retains_active_status_when_stock_is_zero(self):
        # Create a variant with stock = 0 and is_active = True
        variant = ProductVariant.objects.create(
            product=self.product,
            size="M",
            color="Red",
            price=Decimal("999.00"),
            stock=0,
            is_active=True
        )
        # Reload from DB
        variant.refresh_from_db()
        
        # Verify that it remains active even with 0 stock
        self.assertTrue(variant.is_active)
        self.assertEqual(variant.stock, 0)

    def test_variant_can_be_manually_deactivated_with_stock(self):
        # Create a variant with stock > 0 but is_active = False
        variant = ProductVariant.objects.create(
            product=self.product,
            size="L",
            color="Blue",
            price=Decimal("1200.00"),
            stock=10,
            is_active=False
        )
        # Reload from DB
        variant.refresh_from_db()

        # Verify that it remains inactive despite having stock
        self.assertFalse(variant.is_active)
        self.assertEqual(variant.stock, 10)
