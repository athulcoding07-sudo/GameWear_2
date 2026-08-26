from django.urls import path
from . import views

app_name = "products"

urlpatterns = [

    # =========================
    # CATEGORY URLs
    # =========================
    path("categories/", views.category_list, name="category_list"),
    path("categories/save/", views.category_save, name="category_save"),
    path("categories/<int:pk>/toggle/", views.category_toggle, name="category_toggle"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),

    # =========================
    # PRODUCT URLs
    # =========================
    path("products/add/", views.product_add, name="product_add"),
    path("products/", views.product_list, name="product_list"),
    path("products/<int:product_id>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("products/<int:pk>/toggle/", views.product_toggle, name="product_toggle"),

    # =========================
    # VARIANT URLs
    # =========================
    path("variants/<int:variant_id>/delete/", views.delete_variant, name="delete_variant"),

    # =========================
    # USER PRODUCT LISTING
    # =========================
    path("user_products/", views.user_product_list, name="users_product_listing"),
    path("product_detail/<slug:slug>/", views.user_product_detail, name="users_product_detail"),
    path("review/<slug:slug>/", views.add_or_edit_review, name="add_or_edit_review"),

    # =========================
    # USER BRAND LISTING
    # =========================
    path('brands/', views.brand_list, name='brand_list'),
    path('brand/save/', views.brand_save, name='brand_save'),
    path('brand/toggle/<int:id>/', views.brand_toggle, name='brand_toggle'),
    path('brand/delete/<int:id>/', views.brand_delete, name='brand_delete'),

    # =========================
    # CART MANAGEMENT 
    # =========================

    path("cart-view/", views.cart_view, name="cart_view"),
   
    path("cart-add/<int:product_id>/", views.add_to_cart_view, name="add_to_cart"),
    path("cart/update/<int:item_id>/<str:action>/",views.update_cart_view, name="update_cart"),
    path("cart/remove/<int:item_id>/",views.remove_cart_view, name="remove_cart"),

    # =========================
    # WHSILIST
    # =========================

    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/toggle/<int:product_id>/", views.toggle_wishlist_view, name="toggle_wishlist"),
    path("wishlist/remove/<int:item_id>/", views.remove_wishlist_view, name="remove_wishlist"),
    path("wishlist/move-to-cart/<int:item_id>/", views.move_to_cart_view, name="move_to_cart"),


    # =========================
    # ORDER MANAGEMENT
    # =========================

    path("checkout/", views.checkout_view, name="checkout"),
    path("place-order/", views.place_order, name="place_order"),
    path("success/<int:order_id>/", views.order_success, name="order_success"),
    path("orders/<int:order_id>/",views.order_detail,name="order_detail"),
    path("orders/history/",views.order_history,name="order_history"),
    path("order/cancel-item/<int:item_id>/", views.cancel_order_item, name="cancel_order_item"),
    path("order/return-item/<int:item_id>/", views.return_order_item, name="return_order_item"),
    path("order/return/<int:order_id>/", views.return_order, name="return_order"),
    path("orders/search/", views.search_orders, name="search_orders"),
    path("order/invoice/<int:order_id>/", views.download_invoice, name="download_invoice"),


    # =========================
    # ADMIN ORDER MANAGEMENTT
    # =========================

    path("orders/admin-order-list/", views.admin_order_list, name="admin_order_list"),
    path("orders/admin-order-detail/<int:order_id>/", views.admin_order_detail, name="admin_order_detail"),
    path("orders/admin-update-order/<int:order_id>/status/", views.admin_update_order_status, name="admin_update_order_status"),

    # Per-item return / refund actions
    path("orders/admin-item/<int:item_id>/approve-return/", views.admin_approve_return_item, name="admin_approve_return_item"),
    path("orders/admin-item/<int:item_id>/reject-return/",  views.admin_reject_return_item,  name="admin_reject_return_item"),
    path("orders/admin-item/<int:item_id>/refund/",         views.admin_refund_item,          name="admin_refund_item"),

]
