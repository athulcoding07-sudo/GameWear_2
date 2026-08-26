from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.users.validators import validate_name as validate_user_name
from apps.core.validators import validate_name as validate_core_name


class NameValidatorTests(TestCase):
    def test_user_name_validation(self):
        # Single word without space
        validate_user_name("Athul")
        # Multi word with space
        validate_user_name("Athul George")
        # Name with apostrophe/hyphen
        validate_user_name("O'Connor-Smith")

        # Invalid cases
        with self.assertRaises(ValidationError):
            validate_user_name("12345")

    def test_core_name_validation(self):
        # Product/Category/Offer single word name
        validate_core_name("Jersey")
        # Multi word name
        validate_core_name("Home Jersey 2026")

        # Invalid cases
        with self.assertRaises(ValidationError):
            validate_core_name("123")


class SocialAdapterTests(TestCase):
    def test_populate_user_name(self):
        from apps.users.adapters import CustomSocialAccountAdapter
        from allauth.socialaccount.models import SocialLogin
        from apps.users.models import User

        adapter = CustomSocialAccountAdapter()
        user = User(email="testgoogle@example.com")
        sociallogin = SocialLogin(user=user)

        data = {"name": "Google User", "first_name": "Google", "last_name": "User"}
        populated_user = adapter.populate_user(None, sociallogin, data)

        self.assertEqual(populated_user.full_name, "Google User")


