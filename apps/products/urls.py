from django.urls import path
from .views import category_list,category_save,category_toggle,category_delete,product_add,product_list,product_edit,product_toggle,product_delete,delete_variant,user_product_list,user_product_detail,add_or_edit_review



app_name = "products" 

urlpatterns = [



    # =========================
    # CATEGORY URLs
    # =========================
    path("categories/", category_list, name="category_list"),
    path("categories/save/", category_save, name="category_save"),
    path("categories/<int:pk>/toggle/", category_toggle, name="category_toggle"),
    path("categories/<int:pk>/delete/", category_delete, name="category_delete"),

    # =========================
    # PRODUCT URLs
    # =========================
    path("products/add/", product_add, name="product_add"),
    path("products/", product_list, name="product_list"),
    path("products/<int:product_id>/edit/", product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", product_delete, name="product_delete"),
    path("products/<int:pk>/toggle/", product_toggle, name="product_toggle"),

    # =========================
    # VARIANT URLs
    # =========================
    path("variants/<int:variant_id>/delete/", delete_variant, name="delete_variant"),

    # =========================
    # USER PRODUCT LISTING
    # =========================
    path("user_products/", user_product_list, name="users_product_listing"),
    path("product_detail/<slug:slug>/", user_product_detail, name="users_product_detail"),
    path("review/<slug:slug>/", add_or_edit_review, name="add_or_edit_review"),


  

]
