from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_save


def reward_referral_on_order_placed(sender, instance, created, **kwargs):

    # Run only when a NEW order is created
    if not created:
        return

    from apps.users.models import User
    from apps.wallet.models import Wallet

    user = instance.user

    # User did not apply a referral code
    if not user.referred_by_id:
        return

    with transaction.atomic():

        # Lock and get latest user data
        user = User.objects.select_for_update().get(pk=user.pk)

        # Reward already given before
        if user.referral_reward_granted:
            return

        referrer = user.referred_by

        # Get/create referred user's wallet
        user_wallet, _ = Wallet.objects.get_or_create(user=user)

        # Get/create referrer's wallet
        referrer_wallet, _ = Wallet.objects.get_or_create(
            user=referrer
        )

        # Add ₹10 to referred user
        Wallet.objects.filter(pk=user_wallet.pk).update(
            balance=F("balance") + Decimal("10.00")
        )

        # Add ₹10 to referrer
        Wallet.objects.filter(pk=referrer_wallet.pk).update(
            balance=F("balance") + Decimal("10.00")
        )

        # Mark reward as completed
        user.referral_reward_granted = True
        user.save(update_fields=["referral_reward_granted"])

        
        


def connect_signals():
    from apps.products.models import Order

    post_save.connect(
        reward_referral_on_order_placed,
        sender=Order,
        dispatch_uid="reward_referral_on_order_placed",
    )


connect_signals()