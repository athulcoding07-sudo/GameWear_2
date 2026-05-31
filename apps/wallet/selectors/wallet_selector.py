from django.shortcuts import get_object_or_404
from apps.wallet.models import Wallet


class WalletSelector:

    @staticmethod
    def get_wallet(user):

        wallet, created = (
            Wallet.objects.select_related(
                'user'
            ).get_or_create(
                user=user
            )
        )

        return wallet