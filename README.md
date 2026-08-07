# GameWear

A full-featured Django e-commerce platform for gaming apparel and merchandise. Built with Django 4.2, PostgreSQL, and modern frontend tooling.

---

## 🎮 About the Project

GameWear is a complete e-commerce solution built for selling gaming-themed apparel and merchandise. It implements a modular Django architecture with custom user authentication (email/OTP + Google OAuth), a full product catalog with variant support (size/color), dynamic pricing with offers/coupons, cart/wishlist, wallet system, Razorpay payments, order management with returns/cancellations, and a custom admin panel with PDF sales reports.

Built as a learning project to master Django architecture, authentication systems, payment integration, and e-commerce domain modeling.

---

## ✨ Features

### 🔐 Authentication & Users
- **Custom User Model** — Email as username, profile image, gender, DOB, role (user/admin), referral system
- **Email + OTP Verification** — Signup, login, forgot password, email change with 6-digit OTP (expiry, resend limits)
- **Google OAuth 2.0** — Via `django-allauth`
- **Profile Management** — Avatar upload (Cloudinary), address book with default, email change with verification
- **Referral System** — Unique referral codes, ₹10 reward to both referrer & referee on first order (atomic, `F()` expressions)

### 🛍️ Product Catalog
- **Categories & Brands** — Hierarchical organization with slugs, images, active/inactive states
- **Products** — Name, slug, description, featured/listed flags, average rating, review count, rating breakdown (1–5★)
- **Product Variants** — Size + Color combinations, auto-generated SKU (`JER-{PREFIX}-{SIZE}-{COLOR}-{UUID4_HEX4}`), stock tracking, auto `is_active` based on stock
- **Primary Images** — One primary image per variant (enforced via unique constraint)
- **Dynamic Pricing** — Real-time offer price calculation: checks active ProductOffers & CategoryOffers, applies higher discount

### 🛒 Cart & Wishlist
- **Cart** — One-to-one per user, atomic `add_to_cart`/`update_cart_item` with stock validation, max quantity (5), price snapshots
- **Wishlist** — Toggle via `toggle_wishlist()`, unique per user/product/variant

### 🎁 Offers & Coupons
- **Product Offers** — Percentage discount, date range, overlap validation
- **Category Offers** — Same, applied to all products in category
- **Referral Offers** — Configurable reward amount, minimum order threshold
- **Coupons** — Unique codes, percentage discount, min/max amounts, usage limits, date validity
- **Validation Services** — Date overlap prevention, usage limit enforcement, atomic coupon application

### 💳 Wallet System
- **Wallet** — One-to-one per user, balance tracking
- **Transactions** — Credit/Debit with descriptions, unique reference IDs, full audit trail
- **Top-ups** — Razorpay-powered wallet funding with order/payment tracking
- **Referral Rewards** — Atomic credit via `post_save` signal on Order (`select_for_update` + `F()`)

### 💰 Payments (Razorpay)
- **Order Creation** — Server-side Razorpay order ID generation
- **Payment Verification** — Signature verification (`HMAC-SHA256`), idempotent via unique `razorpay_payment_id`
- **Webhooks** — `payment.captured`, `payment.failed`, `order.paid` handling with signature verification
- **COD Support** — Cash on delivery as alternative payment method
- **Failure Handling** — Dedicated failure page, order status rollback

### 📦 Order Management
- **Lifecycle** — `PENDING → CONFIRMED → SHIPPED → DELIVERED` / `CANCELLED` / `RETURNED` / `REFUNDED` / `RETURN_REQUESTED` / `PARTIAL_*`
- **Aggregated Status** — `Order.update_status()` rolls up from `OrderItem` statuses with priority logic
- **Snapshots** — `OrderItem` stores price at purchase; `OrderAddress` stores shipping snapshot
- **Cancellation/Return** — Per-item with reason, refund amount calculation, wallet credit
- **Invoice Generation** — PDF invoices via ReportLab (ReportLab)

### 📊 Admin Panel (Custom — Not Django Admin)
- **Dashboard** — Stats cards, recent orders, revenue chart
- **Products** — CRUD with variant management, image uploads (Cloudinary), bulk actions
- **Categories/Brands** — Full CRUD with slug auto-generation
- **Orders** — List with search, status filter, sort, pagination; detail view; status update workflow
- **Offers/Coupons** — CRUD with date overlap validation
- **Customers** — User list, block/unblock, detail view
- **Sales Reports** — Date-range PDF reports (ReportLab): order count, revenue, COD/Online breakdown, top products

### 📈 Sales Reports (PDF)
- **ReportLab** generation
- **Filters** — Date range, order status
- **Metrics** — Total orders, revenue, COD vs Online, average order value, top-selling products
- **Download** — Direct PDF response

### 🛠 Technical Highlights
- **Custom Middleware** — `DisableCacheMiddleware` (no-cache for auth users), `AdminAccessMiddleware` (protects `/adminpanel/*` requiring staff)
- **Atomic Operations** — `select_for_update`, `F()` expressions for wallet/referral concurrency safety
- **Services Layer** — Business logic extracted from views (`products/services.py`, `offers/services/`, `coupons/services/`, `wallet/services/`)
- **Validators** — Reusable validators in `core/validators.py` + app-specific (`offers/validators/`, `coupons/validators/`, `wallet/validators/`)
- **Cloudinary** — Media storage (product images, avatars) via `django-cloudinary-storage`
- **PostgreSQL** — Production DB with `psycopg2`
- **Environment Config** — `python-dotenv` + `os.getenv()` for all secrets

---

## 🏗 Tech Stack

| Layer | Technology |
|-------|------------|
| **Framework** | Django 4.2.27 (Python 3.x) |
| **Database** | PostgreSQL (psycopg2-binary) |
| **Auth** | Custom User (AbstractBaseUser), django-allauth (Google OAuth), OTP email |
| **Storage** | Cloudinary (`django-cloudinary-storage`) |
| **Payments** | Razorpay (orders, payments, webhooks) |
| **PDF** | ReportLab 4.4.10 |
| **Frontend** | Django Templates, Tailwind CSS (CDN), Inter font, dark theme |
| **Email** | Gmail SMTP (TLS 587) |
| **Code Quality** | Black, isort, flake8, pylint, mypy (django-stubs) |
| **Testing** | pytest (implied via test files) |

---

## 📁 Project Structure

```
gamewear_2/
├── config/                      # Django project config
│   ├── settings.py              # Main settings (env-driven)
│   ├── urls.py                  # Root URLConf
│   ├── middleware.py            # Custom middleware
│   ├── wsgi.py / asgi.py
│
├── apps/                        # Modular apps
│   ├── users/                   # Auth, profiles, addresses, referrals
│   ├── adminpanel/              # Custom admin dashboard
│   ├── home/                    # Homepage
│   ├── otp/                     # OTP generation, verification, email
│   ├── products/                # Catalog, variants, cart, wishlist, orders, reviews
│   ├── offers/                  # Product/category/referral offers
│   ├── coupons/                 # Coupon codes
│   ├── wallet/                  # Wallet, transactions, top-ups
│   ├── payments/                # Razorpay integration
│   ├── sales_report/            # PDF sales reports
│   └── core/                    # Shared validators
│
├── templates/                   # Global templates
│   ├── base.html                # Public base (dark theme, Tailwind)
│   ├── users/
│   │   └── user_dashboard_base.html
│   ├── adminpanel/
│   │   └── dashboard.html       # Admin base (sidebar + header)
│   ├── home/, payments/, users/{cart,checkout,orders,profile,wallet,wishlist,products}
│   └── adminpanel/{products,orders,coupons,offers,customers,sales_report}
│
├── static/                      # Static assets (images)
├── media/                       # Local media (dev only)
├── manage.py
├── requirements.txt
├── .env                         # Environment variables (not committed)
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis (optional, for caching/sessions in production)
- Cloudinary account (for media storage)
- Razorpay account (for payments)
- Gmail App Password (for SMTP)

### Installation

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd gamewear_2

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env  # Create .env.example first (see below)
# Edit .env with your credentials

# 5. Run migrations
python manage.py migrate

# 6. Create superuser (for Django admin access if needed)
python manage.py createsuperuser

# 7. Collect static files
python manage.py collectstatic

# 8. Start development server
python manage.py runserver
```

### Environment Variables (`.env`)

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL)
DB_NAME=gamewear
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

# Email (Gmail SMTP)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password  # Not your regular password!

# Cloudinary
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Google OAuth (via allauth)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Razorpay
RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=your-razorpay-secret
RAZORPAY_WEBHOOK_SECRET=your-webhook-secret

# Site
SITE_ID=2
```

---

## 🧪 Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.users
python manage.py test apps.products

# With coverage (if configured)
coverage run --source='apps' manage.py test
coverage report
```

---

## 🧹 Code Quality

```bash
# Format with Black
black apps/ config/

# Sort imports
isort apps/ config/

# Lint with flake8
flake8 apps/ config/

# Type check with mypy
mypy apps/ config/
```

---

## 🔐 Authentication Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌────────────┐
│   Signup    │────▶│  OTP Sent    │────▶│ Verify OTP  │────▶│  Active    │
│ (email, pwd)│     │  (6-digit)   │     │  (expires)  │     │  Account   │
└─────────────┘     └──────────────┘     └─────────────┘     └────────────┘
       │                    │                    │                    │
       ▼                    ▼                    ▼                    ▼
  Referral code         Resend limit         Max attempts        Dashboard
  generated             (cooldown)           (lockout)           access
```

**Login**: Email + Password → Session → Dashboard  
**Forgot Password**: Email → OTP → Reset Password  
**Google OAuth**: Redirect → Consent → Callback → Session  

---

## 💰 Payment Flow (Razorpay)

```
Cart → Checkout → Order Created (PENDING)
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
   Razorpay Order           COD Order
   Created (₹)              Created
        │                       │
        ▼                       ▼
   Payment Page            Order CONFIRMED
   (Razorpay JS)                  │
        │                       ▼
   User Pays              COD Delivered
        │                       │
        ▼                       ▼
   Webhook:                Order DELIVERED
   payment.captured
        │
        ▼
   Order CONFIRMED
        │
        ▼
   Referral Reward (if applicable)
   Wallet Credit (₹10 each)
```

---

## 📦 Order Status Lifecycle

```
PENDING → CONFIRMED → SHIPPED → DELIVERED
    │         │           │
    │         │           └── RETURN_REQUESTED → RETURNED → REFUNDED
    │         │
    │         └── CANCELLED → REFUNDED (wallet)
    │
    └── PAYMENT_FAILED → PENDING (retry) / CANCELLED
```

**Aggregation Logic** (`Order.update_status()`):
- All items `CANCELLED` → `CANCELLED`
- All items `REFUNDED` → `REFUNDED`
- All items `RETURNED` → `RETURNED`
- Any `RETURN_REQUESTED` → `RETURN_REQUESTED`
- All items `DELIVERED` → `DELIVERED`
- Mixed → `PARTIAL_CANCELLED` / `PARTIAL_RETURNED` / `PARTIAL_DELIVERED`

---

## 🛡 Admin Panel Access

1. Create a user with `is_staff=True` (via Django admin or shell)
2. Visit `/adminpanel/` — protected by `AdminAccessMiddleware`
3. Dashboard shows: total users, orders, revenue, products, recent orders chart

---

## 📄 PDF Sales Reports

**Admin Panel → Sales Report → Generate Report**
- Select date range
- Downloads PDF with:
  - Order count, total revenue
  - COD vs Online revenue split
  - Average order value
  - Top 10 products by quantity sold

---

## 🌐 Deployment Notes

### Production Settings
- `DEBUG=False`
- `ALLOWED_HOSTS` = your domain(s)
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- Use `gunicorn` + `nginx` + `systemd`
- Configure `CSRF_TRUSTED_ORIGINS` for your domain

### Database
```bash
# PostgreSQL production setup
CREATE DATABASE gamewear_prod;
CREATE USER gamewear_user WITH PASSWORD 'strong-password';
GRANT ALL PRIVILEGES ON DATABASE gamewear_prod TO gamewear_user;
```

### Static/Media
- `collectstatic` → serve via nginx or CDN
- Media → Cloudinary (configured via `DEFAULT_FILE_STORAGE`)

### Webhooks
- Configure Razorpay webhook URL: `https://yourdomain.com/payments/webhook/`
- Verify `RAZORPAY_WEBHOOK_SECRET` matches Razorpay dashboard

---

## 📚 Key Implementation Details

### Dynamic Pricing (`products/utilitys.py`)
```python
def get_pricing(variant):
    # Checks active ProductOffer & CategoryOffer
    # Returns higher discount
    # Cached via variant.offer_price property
```

### Atomic Referral Reward (`users/signals.py`)
```python
@receiver(post_save, sender=Order)
def reward_referral_on_order_placed(sender, instance, created, **kwargs):
    if created and instance.user.referred_by:
        with transaction.atomic():
            referrer_wallet = Wallet.objects.select_for_update().get(user=instance.user.referred_by)
            referee_wallet = Wallet.objects.select_for_update().get(user=instance.user)
            # Credit both using F() expressions
```

### Cart Price Snapshots
- `CartItem.price` stores price at add-time
- Refreshed via `variant.offer_price` on cart view
- Order creation uses `CartItem.price` (honors price at add)

### SKU Generation
```python
# ProductVariant.save()
sku = f"JER-{product_prefix}-{size}-{color}-{uuid4().hex[:4].upper()}"
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Code Style**: Follow Black, isort, flake8. Type hints encouraged.

---

## 📄 License

This project is for learning purposes. Feel free to modify and reuse.

---

## 👨‍💻 Author

**Athul George**  
India | Learning Django & Building Things

---

## 🙏 Acknowledgments

- Django Documentation & Community
- django-allauth for OAuth
- Razorpay for payment infrastructure
- Cloudinary for media management
- ReportLab for PDF generation
- Tailwind CSS for styling utility