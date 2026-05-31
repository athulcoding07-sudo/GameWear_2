from decimal import Decimal
from django.core.exceptions import ValidationError





class WalletValidator:

    @staticmethod
    def validate_amount(amount):
        if amount <= 0:
            raise ValidationError(
                "Amount must be greater than 0"
            )

    @staticmethod
    def validate_balance(wallet, amount):
        if wallet.balance < amount:
            raise ValidationError(
                f"Insufficient balance. "
                f"Available: ₹{wallet.balance}"
            )