from decimal import Decimal
from django.db import transaction

from apps.wallet.models import WalletTransaction
from apps.wallet.validators.wallet_validator import WalletValidator


class WalletService:

    @staticmethod
    @transaction.atomic
    def credit_wallet(
        wallet,
        amount,
        description,
        reference_id
    ):
        amount = Decimal(str(amount))

        WalletValidator.validate_amount(amount)

        wallet.balance += amount

        wallet.save(update_fields=['balance'])

        WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type=WalletTransaction.CREDIT,
            description=description,
            reference_id=reference_id
        )

        return wallet


    @staticmethod
    @transaction.atomic
    def debit_wallet(
        wallet,
        amount,
        description,
        reference_id
    ):
        amount = Decimal(str(amount))

        WalletValidator.validate_amount(amount)

        WalletValidator.validate_balance(
            wallet,
            amount
        )

        wallet.balance -= amount

        wallet.save(update_fields=['balance'])

        WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type=WalletTransaction.DEBIT,
            description=description,
            reference_id=reference_id
        )

        return wallet