# Backend Architecture

## Core Models

### users
- **User** (AbstractBaseUser): email (username), full_name, phone, profile_image, gender, dob, role (user/admin), referral_code, referred_by, is_active, is_blocked, is_staff, referral_reward_granted
- **Address**: user FK, full_name, phone, address_line_1/2, city, state, postal_code, country, is_default
- **PendingEmail**: user OneToOne, new_email, created_at

### products
- **Category/Brand**: name, slug, description, image, is_active
- **Product**: category FK, brand FK, name, slug, description, is_active/featured/listed, avg_rating, review_count, rating_breakdown
- **ProductVariant**: product FK, size, color, sku (auto), price, stock, is_active (auto: stock>0), unique (product,size,color), pricing property (dynamic offers)
- **ProductImage**: variant FK, image, is_primary (unique per variant)
- **Review**: product FK, user FK, rating (1-5), title, comment, is_approved, is_verified_purchase, unique (product,user)
- **Cart**: user OneToOne; **CartItem**: cart FK, product/variant FK, quantity, price (snapshot)
- **WishlistItem**: user FK, product FK, variant FK, unique (user,product,variant)
- **Order**: user FK, order_id, shipping_address OneToOne, totals (tax, shipping, discount, final), payment_method (COD/RAZORPAY), status lifecycle, referral_rewarded, update_status() aggregates OrderItems
- **OrderItem**: order FK, product/variant FK, quantity, price, status, cancellation/return_reason, refund_amount property
- **OrderAddress**: shipping address snapshot

### offers
- **BaseOffer** (abstract): name, discount_percentage, start/end_date, is_active, is_valid property
- **ProductOffer/CategoryOffer**: BaseOffer + product/category FK
- **ReferralOffer**: reward_amount, minimum_order, is_active

### coupons
- **Coupon**: code (unique), discount_percentage, minimum_amount, maximum_discount, valid_from/to, is_active, is_valid property

### wallet
- **Wallet**: user OneToOne, balance
- **WalletTransaction**: wallet FK, type (credit/debit), amount, description, reference_id (unique)
- **WalletTopUp**: user FK, amount, razorpay_order_id, razorpay_payment_id, status

### payments
- **Payment**: order OneToOne, razorpay_order_id, razorpay_payment_id, razorpay_signature, amount, status

## Key Services

### products/services.py
- `add_to_cart()`: atomic, stock checks, MAX_QUANTITY=5, snapshots offer_price
- `update_cart_item()`: increase/decrease with stock/max validation
- `toggle_wishlist()`: get_or_create + delete toggle
- `calculate_cart_totals()`: subtotal, discount, shipping (₹50 if <₹1000), tax (5%), grand_total

### products/utilitys.py
- `get_pricing(variant)`: checks active ProductOffer & CategoryOffer, picks higher discount
- `validate_cart(cart)`: invalid items (inactive, out of stock, qty>stock)
- Constants: FREE_SHIPPING_LIMIT=₹1000, SHIPPING_CHARGE=₹50, TAX_RATE=5%

### offers/services/
- **ProductOfferService/CategoryOfferService**: CRUD + toggle; OfferValidator for date overlap & conflicts

### coupons/services/
- **CouponService.apply_coupon()**: validates code, dates, usage_limit, minimum_amount

### wallet/services/
- Selectors + credit/debit with transaction logging

### otp/services.py
- OTP generation (6-digit), email send, verification with expiry/resend limits

### sales_report/services.py
- Date ranges, DELIVERED order queryset, aggregation (Count, Sum), PDF data prep

## Validators
- **core/validators.py**: `validate_name` (3-100 chars), `validate_description` (10-500 chars)
- **offers/validators/**: Date range, overlap prevention, discount range
- **coupons/validators/** / **wallet/validators/**: Domain-specific

## Forms
- **users/forms.py**: UserSignupForm (email/phone uniqueness, password strength, Indian phone, referral), UserEditProfileForm, EmailChangeForm, AddressForm
- **adminpanel/forms.py**: Admin forms for products, orders, offers, coupons

## Signals
- **users/signals.py**: `reward_referral_on_order_placed` (post_save Order) → ₹10 to both wallets atomically (select_for_update, F())
- **wallet/signals.py**: Wallet transaction signals

## Middleware & Decorators
- **DisableCacheMiddleware**: no-cache headers for authenticated users
- **AdminAccessMiddleware**: protects `/adminpanel/*`, requires auth + is_staff
- **@admin_required**: redirect to login or 403 if not staff

## Key Relationships
User→Address (1:M), User→Cart (1:1), User→WishlistItem (1:M), User→Order (1:M), User→Referral (self FK), Category→Product (1:M), Brand→Product (1:M), Product→Variant (1:M, unique size+color), Variant→Image (1:M, one primary), Product→Review (1:M), Product→ProductOffer (1:M), Category→CategoryOffer (1:M), Order→OrderItem (1:M), Order→OrderAddress (1:1), OrderItem→Product/Variant (M:1), User→Wallet (1:1), Wallet→Transaction (1:M)

## Business Logic Highlights
1. **Dynamic Pricing**: `ProductVariant.pricing` → `get_pricing()` checks active offers, applies higher discount
2. **Cart Snapshots**: CartItem stores price at add; refreshed via `variant.offer_price`
3. **Order Lifecycle**: `Order.update_status()` aggregates OrderItems with priority: all CANCELLED→CANCELLED, all REFUNDED→REFUNDED, all RETURNED→RETURNED, any RETURN_REQUESTED→RETURN_REQUESTED, all DELIVERED→DELIVERED, mixed→PARTIAL_*
4. **Referral Reward**: First order by referred user → ₹10 both wallets (atomic, F())
5. **Coupon Application**: Validates code, dates, usage_limit, minimum_amount, caps at maximum_discount
6. **Free Shipping**: Orders ≥₹1000 free, else ₹50
7. **Tax**: 5% on subtotal_after_discount
8. **SKU**: JER-{PRODUCT_PREFIX}-{SIZE}-{COLOR}-{UUID4_HEX4}
9. **Stock Sync**: ProductVariant.is_active auto-set to stock>0 on save