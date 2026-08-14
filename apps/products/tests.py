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


class WalletPaymentAndRefundTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from apps.wallet.models import Wallet
        from apps.products.models import Cart, CartItem, Order, OrderItem, Address, OrderAddress
        
        self.Cart = Cart
        self.CartItem = CartItem
        self.Order = Order
        self.OrderItem = OrderItem
        self.Address = Address
        self.OrderAddress = OrderAddress
        
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            email="testuser@example.com",
            password="testpassword",
            full_name="John Doe"
        )
        # Create wallet and set balance
        self.wallet, _ = Wallet.objects.get_or_create(user=self.user)
        self.wallet.balance = Decimal("2000.00")
        self.wallet.save()

        # Create product
        self.category = Category.objects.create(
            name="Test Jerseys",
            description="Test Category Description"
        )
        self.product = Product.objects.create(
            category=self.category,
            name="Gaming Jersey",
            description="High quality gaming jersey"
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size="L",
            color="Black",
            price=Decimal("1000.00"),
            stock=15,
            is_active=True
        )

        # Create Address
        self.address = self.Address.objects.create(
            user=self.user,
            full_name="John Doe",
            phone="1234567890",
            address_line_1="123 Main St",
            city="Metropolis",
            state="NY",
            postal_code="10001",
            country="India"
        )

        # Create Cart and add item
        self.cart, _ = self.Cart.objects.get_or_create(user=self.user)
        self.cart_item = self.CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            variant=self.variant,
            quantity=1,
            price=Decimal("1000.00")
        )

    def test_place_order_with_wallet_success(self):
        from django.urls import reverse
        self.client.login(email="testuser@example.com", password="testpassword")
        
        # Place order
        response = self.client.post(
            reverse("products:place_order"),
            {
                "address": self.address.id,
                "payment_method": "WALLET"
            }
        )
        
        # Verify redirect to order success
        self.assertEqual(response.status_code, 302)
        
        # Reload wallet
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("950.00")) # 2000 - 1050 (1000 subtotal + 50 tax) = 950
        
        # Check order was created and is CONFIRMED
        order = self.Order.objects.filter(user=self.user).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "CONFIRMED")
        self.assertEqual(order.payment_method, "WALLET")
        
        # Check stock was decremented
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 14)

    def test_place_order_with_wallet_insufficient_funds(self):
        from django.urls import reverse
        # Set wallet balance to low amount
        self.wallet.balance = Decimal("100.00")
        self.wallet.save()
        
        self.client.login(email="testuser@example.com", password="testpassword")
        
        # Place order
        response = self.client.post(
            reverse("products:place_order"),
            {
                "address": self.address.id,
                "payment_method": "WALLET"
            }
        )
        
        # Should redirect back to checkout
        self.assertEqual(response.status_code, 302)
        
        # Wallet balance should be unchanged
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("100.00"))
        
        # No order should have been created
        self.assertFalse(self.Order.objects.filter(user=self.user).exists())

    def test_cancel_wallet_paid_order_refunds_to_wallet(self):
        from django.urls import reverse
        self.client.login(email="testuser@example.com", password="testpassword")
        
        # Place order first
        self.client.post(
            reverse("products:place_order"),
            {
                "address": self.address.id,
                "payment_method": "WALLET"
            }
        )
        
        order = self.Order.objects.filter(user=self.user).first()
        order_item = order.items.first()
        
        # Verify wallet balance is 950.00
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("950.00"))
        
        # Cancel order item
        response = self.client.post(
            reverse("products:cancel_order_item", kwargs={"item_id": order_item.id})
        )
        self.assertEqual(response.status_code, 302)
        
        # Verify wallet was refunded
        self.wallet.refresh_from_db()
        # Item price + tax = 1050.00, so wallet should be refunded 1050.00 restoring to 2000.00
        self.assertEqual(self.wallet.balance, Decimal("2000.00"))
        
        # Verify item status updated to CANCELLED
        order_item.refresh_from_db()
        self.assertEqual(order_item.status, "CANCELLED")
        
        # Verify stock restored
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 15)

    def test_admin_cancel_wallet_paid_order_refunds_to_wallet(self):
        from django.urls import reverse
        # Create an admin user
        admin_user = self.User.objects.create_superuser(
            email="admin@example.com",
            password="adminpassword",
            full_name="Admin User"
        )
        
        self.client.login(email="testuser@example.com", password="testpassword")
        
        # Place order first
        self.client.post(
            reverse("products:place_order"),
            {
                "address": self.address.id,
                "payment_method": "WALLET"
            }
        )
        
        order = self.Order.objects.filter(user=self.user).first()
        
        # Verify wallet balance is 950.00
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("950.00"))
        
        # Login as admin
        self.client.login(email="admin@example.com", password="adminpassword")
        
        # Cancel order via admin
        response = self.client.post(
            reverse("products:admin_update_order_status", kwargs={"order_id": order.id}),
            {
                "status": "CANCELLED"
            }
        )
        self.assertEqual(response.status_code, 302)
        
        # Verify wallet was refunded
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("2000.00"))
        
        # Verify item status updated to CANCELLED
        order_item = order.items.first()
        order_item.refresh_from_db()
        self.assertEqual(order_item.status, "CANCELLED")
        
        # Verify stock restored
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 15)

