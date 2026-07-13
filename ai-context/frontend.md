# Frontend Architecture

## Base Templates

**`templates/base.html`** — Global base for public pages. Dark theme (black bg, white text), Tailwind CDN, Inter font, custom scrollbar. Blocks: `title`, `extra_head`, `header`, `content`, `footer`, `extra_js`. Centered `<main>` with min-h-screen flex centering.

**`templates/users/user_dashboard_base.html`** — Authenticated user dashboard base. Extends nothing; self-contained HTML. Adds toast notifications (slide-in/fade-out, progress bar auto-dismiss 4s), sticky header with logo, wishlist/cart badges, user avatar dropdown. Blocks: `title`, `extra_head`, `content`, `extra_js`.

**`templates/adminpanel/dashboard.html`** — Admin panel base. Full-screen layout: sticky header (73px), sticky desktop sidebar (`position: sticky; top: 73px; height: calc(100vh-73px)`), mobile slide-out sidebar. Toast system identical to user base. Chart shell responsive heights. Blocks: `title`, `content`, `extra_js`.

## Component Reuse

- **Sidebar nav links** (`.nav-link`): shared desktop/mobile, active state with right border indicator, hover transitions, SVG icon color sync.
- **Toast notifications**: identical markup + CSS animations (`toast-in`, `toast-out`, `shrink` progress bar) in both user and admin bases. Tag-based colors: success (emerald), error (rose), warning (amber), info (neutral).
- **Tables**: `.table-scroll` wrapper for horizontal overflow on mobile; `divide-y divide-neutral-900` rows; hover `bg-neutral-900/40`.
- **Form inputs**: consistent `bg-neutral-950 border border-neutral-800 text-white focus:border-white outline-none` styling.
- **Buttons**: primary (white bg, black text), secondary (neutral-900 border), danger (rose-500), ghost (neutral-400 text).
- **Status badges**: dot + label, green for active, neutral for inactive, uppercase tracking-wide text-xs.

## Forms

- **CSRF**: `{% csrf_token %}` in every POST form.
- **File uploads**: `enctype="multipart/form-data"` on avatar/profile forms.
- **Client-side validation**: `onchange` handlers (e.g., `validateProfileImage()`), `accept` attribute on file inputs.
- **Server-side errors**: `{% for error in form.field.errors %}` rendered inline below field in red-500 text-xs uppercase.
- **Tabbed forms** (edit_profile): JS `switchTab()` toggles sections; tab buttons share `.action-button` class with active state (border-white, shadow-xl).
- **Select filters**: `<select onchange="this.form.submit()">` for instant filter submission (category, status, sort).

## Pagination

- **Django Paginator** via `page_obj` / `products` in context.
- **Info line**: "Showing {{ start_index }} to {{ end_index }} of {{ paginator.count }} products".
- **Nav**: Prev/Next with disabled state; page numbers with ellipsis logic (`i > number|add:'-3' and i < number|add:'3'`).
- **Query preservation**: all filter params (`search`, `category`, `status`) appended to page links via template concatenation.

## Messages

- **Django messages framework** rendered in both bases.
- **Toast container**: fixed top-center, z-index 200/60, flex-col gap-3, max-w-md.
- **Auto-dismiss**: 4s timeout + progress bar animation; manual close button.
- **Animation**: `toast-animate-in` on mount, `toast-animate-out` on remove (300ms).
- **Tag mapping**: success/error/warning/info → distinct bg/border/text colors.

## UI Conventions

- **Color palette**: black background (`bg-black`), neutral-900/950 cards, neutral-800 borders, white primary, emerald/rose/amber for status.
- **Typography**: Inter font, uppercase tracking-widest for labels (text-[10px]), italic serif-style for display headings.
- **Spacing**: consistent px-4/6/8, py-2.5/3/4, gap-2/3/4.
- **Radius**: rounded-lg (forms), rounded-xl (cards), rounded-2xl (sections), rounded-full (pills/avatars).
- **Shadows**: subtle (`shadow-xl` on active tabs), toast `shadow-2xl`.
- **Transitions**: 150-300ms on hover/focus, cubic-bezier for sidebar slide.
- **Responsive**: mobile-first, lg: breakpoints for sidebar/table layouts, horizontal scroll on tables.

## Folder Organization

```
templates/
├── base.html                           # Public pages base
├── sample.html                         # Unused reference
├── home/                               # Homepage
├── users/
│   ├── user_dashboard_base.html        # User dashboard base
│   ├── dashboard.html                  # User home
│   ├── login.html / signup.html        # Auth
│   ├── verify_signup_otp.html
│   ├── forgot_password.html
│   ├── reset_password.html
│   ├── verify_reset_otp.html
│   ├── cart_management/
│   │   └── cart_view.html
│   ├── checkout/
│   ├── orders/
│   ├── products/
│   ├── profile/
│   │   ├── profile_view.html
│   │   ├── edit_profile.html
│   │   ├── email_view.html
│   │   └── verify_email_otp.html
│   ├── wishlist/
│   └── wallet/
├── adminpanel/
│   ├── dashboard.html                  # Admin base (sidebar + header)
│   ├── dashboard.html                  # Admin home
│   ├── products/
│   │   ├── products/
│   │   │   ├── product_list.html       # Table + filters + pagination
│   │   │   ├── product_add.html
│   │   │   └── product_edit.html
│   │   ├── categories/                 # CRUD templates
│   │   └── brand/                      # CRUD templates
│   ├── orders/
│   │   ├── order_list.html             # Search, status filter, sort, pagination
│   │   ├── order_detail.html
│   │   └── update_order_status.html
│   ├── coupons/
│   ├── offers/
│   ├── customers/
│   └── sales_report/
└── payments/
    └── payment_page.html / payment_failed.html
```