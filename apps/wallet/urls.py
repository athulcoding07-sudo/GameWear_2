from django.urls import path

from apps.wallet.views.payment_views import (
    add_money_page,
    create_razorpay_order,
    payment_success,
)

from apps.wallet.views.wallet_views import (
    wallet_dashboard,
)

app_name = "wallet"

urlpatterns = [

    path("", wallet_dashboard, name="dashboard"),     # Wallet dashboard

    path("add-money/", add_money_page, name="add_money"),    # Add money page

    path("create-order/", create_razorpay_order, name="create_order"),    # Create Razorpay order

    path("payment-success/", payment_success, name="payment_success"),       # Payment success callback


]