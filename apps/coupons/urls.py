from django.urls import path

from apps.coupons.views import dashboard_coupon_views as views




app_name = "coupons"

urlpatterns = [
    path("dashboard/coupons/", views.coupon_list_view, name="dashboard_coupon_list"),
    path("dashboard/coupons/create/", views.coupon_create_view, name="dashboard_coupon_create"),
    path("dashboard/coupons/<int:coupon_id>/update/", views.coupon_update_view, name="dashboard_coupon_update"),
    path("dashboard/coupons/<int:coupon_id>/delete/", views.coupon_delete_view, name="dashboard_coupon_delete"),
    path("dashboard/coupons/<int:coupon_id>/toggle/",views.coupon_toggle_status_view,name="dashboard_coupon_toggle"),
]