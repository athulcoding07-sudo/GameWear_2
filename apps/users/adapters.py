from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.users.validators import validate_name

User = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        # Get full name from Google data
        name = (
            data.get("name")
            or f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
        )
        if not name:
            name = user.email.split("@")[0] if user.email else "User"

        # Sanitize / validate name to ensure it passes model validation
        try:
            validate_name(name)
        except ValidationError:
            name = "".join(c for c in name if c.isalnum() or c in " &'()-").strip()
            if not name:
                name = "User"

        user.full_name = name
        return user

    def pre_social_login(self, request, sociallogin):
        # If social account already exists, do nothing
        if sociallogin.is_existing:
            return

        # Get email from social account
        email = sociallogin.account.extra_data.get("email") or getattr(
            sociallogin.user, "email", None
        )
        if not email:
            return

        email = email.lower().strip()

        # If a user with this email already exists, connect Google login to that user
        try:
            user = User.objects.get(email__iexact=email)
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            pass
