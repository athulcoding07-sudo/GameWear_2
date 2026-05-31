from decimal import Decimal
import razorpay

from django.conf import settings
from django.db import transaction

from apps.wallet.models import WalletTopUp
from apps.wallet.services.wallet_service import WalletService


# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    )
)


class WalletPaymentService:

    @staticmethod
    @transaction.atomic
    def create_topup(user, amount):
        """
        Create Razorpay order and save pending topup record
        """

        amount = Decimal(str(amount))

        if amount <= 0:
            raise ValueError(
                "Amount must be greater than 0"
            )

        amount_in_paise = int(amount * 100)

        order_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "payment_capture": 1
        }

        order = razorpay_client.order.create(
            data=order_data
        )

        WalletTopUp.objects.create(
            user=user,
            amount=amount,
            razorpay_order_id=order["id"],
            status=WalletTopUp.PENDING
        )

        return order


    @staticmethod
    @transaction.atomic
    def verify_and_credit(
        topup,
        payment_id,
        razorpay_signature
    ):
        """
        Verify Razorpay payment and credit wallet
        """

        # Avoid duplicate processing
        if topup.status == WalletTopUp.SUCCESS:
            return False

        params_dict = {
            "razorpay_order_id": topup.razorpay_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": razorpay_signature
        }

        # Verify Razorpay signature
        razorpay_client.utility.verify_payment_signature(
            params_dict
        )

        # Update topup status
        topup.razorpay_payment_id = payment_id
        topup.status = WalletTopUp.SUCCESS

        topup.save(
            update_fields=[
                "razorpay_payment_id",
                "status"
            ]
        )

        # Credit wallet
        WalletService.credit_wallet(
            wallet=topup.user.wallet,
            amount=topup.amount,
            description=(
                f"Wallet topup via Razorpay "
                f"({topup.razorpay_order_id})"
            ),
            reference_id=payment_id
        )

        return True