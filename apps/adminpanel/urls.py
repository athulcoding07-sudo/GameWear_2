from django.urls import path
from .views import admin_dashboard,customers_view,customers_list,logout_view,block_user,unblock_user,add_user_api,add_user_page,delete_user,edit_user


app_name = "adminpanel" 

urlpatterns = [
    path("dashboard/",admin_dashboard,name='dashboard'),
    path("customer-view/<int:customer_id>/",customers_view,name='customers_view'),
    path("customer-list/",customers_list,name='customers_list'),
    path("logout/", logout_view, name="logout_view"),
    path("customers/block/<int:user_id>/", block_user, name="block_user"),
    path("customers/unblock/<int:user_id>/", unblock_user, name="unblock_user"),
    path('add-customer-page/', add_user_page, name='add_user_page'),
    path('add-customer/', add_user_api, name='add_user_api'),
    path('delete/<int:user_id>/', delete_user, name='delete_user'),
    path('edit-customer/<int:user_id>/', edit_user, name='edit_user'),

    



    
]
