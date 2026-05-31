from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.wallet.selectors.wallet_selector import (
    WalletSelector
)


@login_required
def wallet_dashboard(request):
    """
    Wallet dashboard page
    """

    wallet = WalletSelector.get_wallet(
        request.user
    )

    transactions = (
        wallet.transactions.all()
        .order_by("-created_at")[:20]
    )

    context = {
        "wallet": wallet,
        "transactions": transactions
    }

    return render(
        request,
        "users/wallet/wallet.html",
        context
    )