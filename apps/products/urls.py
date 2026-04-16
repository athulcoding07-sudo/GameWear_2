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
]