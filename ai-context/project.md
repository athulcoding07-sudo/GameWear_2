# Project Name
GameWear

# Purpose
Django-based e-commerce platform for gaming apparel/merchandise with email/OTP authentication, Google OAuth, product catalog with variants, cart/wishlist, offers/coupons, wallet system, Razorpay payments, order management, reviews, admin panel, and PDF sales reports.

# Tech Stack
- **Framework**: Django 4.2.27 (Python 3.x)
- **Database**: PostgreSQL (psycopg2)
- **Auth**: Custom User model (email-based), Django Allauth (Google OAuth), OTP email verification
- **Storage**: Cloudinary (media), Cloudinary Storage
- **Payments**: Razorpay (orders, payments, webhooks)
- **PDF Reports**: ReportLab
- **Frontend**: Django Templates, HTML/CSS, Bootstrap (implied)
- **Email**: Gmail SMTP

# Major Apps
| App | Purpose |
|-----|---------|
| `users` | Custom User model, email/OTP auth, profiles, addresses, referral system |
| `adminpanel` | Admin dashboard for products, orders, users, offers, coupons, reports |
| `home` | Homepage |
| `otp` | OTP generation, verification, expiry for email/phone |
| `products` | Categories, brands, products, variants (size/color), images, cart, wishlist, orders, reviews |
| `offers` | Product & category level discount offers |
| `coupons` | Coupon codes with validity, usage limits |
| `wallet` | User wallet with transaction history |
| `payments` | Razorpay integration (orders, payments, verification, webhooks) |
| `sales_report` | PDF sales reports (ReportLab) |
| `core` | Shared validators, utilities |

# Folder Structure
```
gamewear_2/
├── config/                 # Django settings, URLs, WSGI/ASGI, middleware
├── apps/
│   ├── users/              # Auth, profiles, addresses, referrals
│   ├── adminpanel/         # Admin views, forms, dashboard
│   ├── home/               # Homepage
│   ├── otp/                # OTP services
│   ├── products/           # Catalog, cart, wishlist, orders, reviews
│   ├── offers/             # Product/category offers
│   ├── coupons/            # Coupon management
│   ├── wallet/             # Wallet, transactions
│   ├── payments/           # Razorpay integration
│   ├── sales_report/       # PDF report generation
│   └── core/               # Shared validators
├── templates/              # Global templates (base, adminpanel, users, etc.)
├── static/                 # Static assets
├── media/                  # Local media (dev)
├── manage.py
├── requirements.txt
└── .env
```

# High-Level Architecture
- **Pattern**: Django MVT (Model-View-Template) with modular app architecture
- **Auth**: Custom `User` model (email username, OTP verification, referral codes, roles), `allauth` for Google OAuth, custom `AdminAccessMiddleware` for admin route protection
- **Data Flow**: Views → Services/Utils → Models → PostgreSQL; Cloudinary for media; Razorpay for payments
- **Key Features**: Product variants (size/color/SKU), dynamic pricing with offers/coupons, cart/wishlist snapshots, order lifecycle (Pending→Confirmed→Shipped→Delivered/Cancelled/Returned), wallet with referral rewards, PDF sales reports
- **Admin**: Custom admin panel (not Django admin) with role-based access