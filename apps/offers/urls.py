from django.urls import path
from . import views


app_name = "offers"

urlpatterns = [

    # Product Offers
    path("products/", views.product_offer_list, name="product_offer_list"),
    path("products/create/", views.product_offer_create, name="product_offer_create"),
    path("products/<int:pk>/update/", views.product_offer_update, name="product_offer_update"),
    path("products/<int:pk>/delete/", views.product_offer_delete, name="product_offer_delete"),
    path("products/<int:pk>/toggle/", views.product_offer_toggle, name="product_offer_toggle"),
    path("products-by-category/<int:category_id>/", views.products_by_category, name="products_by_category"),

    # Category Offers
    path("category-offers/", views.category_offer_list, name="category_offer_list"),
    path("category-offers/create/", views.category_offer_add, name="category_offer_add"),
    path("category-offers/<int:pk>/edit/", views.category_offer_edit, name="category_offer_edit"),
    path("category-offers/<int:pk>/toggle/", views.category_offer_toggle, name="category_offer_toggle"),
    path("category-offers/<int:pk>/delete/", views.category_offer_delete, name="category_offer_delete"),

   
]