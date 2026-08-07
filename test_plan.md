# GameWear Test Plan

## Overview

Project: GameWear

Framework:
- Django
- PostgreSQL
- Tailwind CSS
- JavaScript

Objective

Validate every user flow before deployment.

Priority

P0 - Critical
P1 - High
P2 - Medium
P3 - Low

---

# Module 1 Authentication

Priority: P0

## Signup

- Email verification
- OTP resend
- OTP expiry
- Invalid OTP
- Signup validation
- Password validation
- Referral code
- Wallet creation
- Session cleanup

Edge Cases

- Refresh OTP page
- Access signup without verification
- Double submit
- Expired OTP

Security

- Session bypass
- Duplicate email
- SQL Injection
- XSS

---

## Login

Test

- Valid login
- Invalid password
- Invalid email
- Blocked user
- Admin login
- Logout
- Already logged in redirect

Security

- User enumeration
- Session fixation

---

## Forgot Password

Test

- Unknown email
- Valid email
- Expired reset link
- Reused reset link
- Password validation

---

# Module 2 Products

Priority: P0

## Home

- Banner
- Categories
- Featured products

## Shop

Test

- Search
- Category filter
- Multiple filters
- Price filter
- Sorting
- Pagination

Edge Cases

- Deleted product
- Inactive product
- Zero stock
- Hidden variants

---

## Product Detail

Test

- Variant selection
- Price update
- Gallery update
- Wishlist
- Add to Cart
- Quantity
- Zoom
- Related products

Edge Cases

- Invalid slug
- Out of stock
- Deleted product

---

# Module 3 Cart

Priority: P0

Test

- Add
- Remove
- Update quantity
- Maximum quantity
- Stock validation
- AJAX response

Coupons

- Apply
- Remove
- Expired
- Minimum purchase
- Percentage
- Fixed amount

Validate

- Cart badge
- Offer price
- Session

---

# Module 4 Wishlist

Priority: P1

Test

- Add
- Remove
- Move to Cart
- Move All
- Clear Wishlist

Edge Cases

- Out of stock
- Quantity already 5

---

# Module 5 Checkout

Priority: P0

Checkout

- Empty cart
- No address
- Address selection

Payment

- COD
- Wallet
- Razorpay

Verify

- Order creation
- Stock deduction
- Cart clearing
- Payment verification

Failure Cases

- Payment cancelled
- Payment failed
- Invalid signature
- Duplicate callback

---

# Module 6 Orders

Priority: P1

Test

- Orders list
- Search
- Order details
- Invoice download
- Cancel
- Return

Edge Cases

- Other user's order
- Already cancelled
- Already returned

---

# Module 7 User Profile

Priority: P1

Test

- Edit profile
- Upload image
- Remove image
- Change email
- OTP verification
- Change password

---

# Module 8 Address

Priority: P1

Test

- Add address
- Edit
- Delete
- Default address
- Validation

---

# Module 9 Wallet

Priority: P1

Test

- Balance
- Transactions
- Referral reward
- Wallet payment
- Refund

---

# Module 10 Coupons

Priority: P1

Test

- Active coupon
- Expired coupon
- Usage limit
- Minimum purchase
- Maximum discount

---

# Module 11 Admin Panel

Priority: P0

Authentication

- Admin login
- Logout

Users

- Block
- Unblock

Products

- CRUD
- Variant CRUD
- Image upload

Categories

- CRUD

Brands

- CRUD

Offers

- Product offer
- Category offer

Orders

- Update status
- Approve cancel
- Approve return

Reports

- Sales report
- Filters
- Export PDF
- Export Excel

---

# Security Checklist

Authentication

- CSRF
- SQL Injection
- XSS
- Session fixation
- Authentication bypass

Authorization

- User cannot access another user's data
- Admin routes protected

Input Validation

- HTML injection
- Invalid file upload
- Long input
- Empty input

---

# Performance

Test

- Pagination
- Search
- Large cart
- Large order history
- Slow network

---

# Regression

Before every release

- Signup
- Login
- Cart
- Checkout
- Razorpay
- Wallet
- Orders
- Wishlist

---

# Known Bugs

Maintain a separate file

KNOWN_BUGS.md

Never report known bugs as new bugs.

---

# Expected Output

Claude should report

- Severity

- Module

- URL

- Steps to reproduce

- Expected result

- Actual result

- Root cause

- Suggested fix

- Priority
