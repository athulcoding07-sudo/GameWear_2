from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from cloudinary.models import CloudinaryField
from  .managers import UserManager
from .validators import validate_name
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.conf import settings



class User(AbstractBaseUser, PermissionsMixin):
    # authentication
    email = models.EmailField(unique=True)

    


    # basic info
    full_name = models.CharField(
        max_length=255,
        validators=[validate_name],
    )

    phone_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
    )

    # profile image
    profile_image = CloudinaryField(
        "image",
        folder="profile_pics",
        
        null=True,
        blank=True,
    )

    # gender & dob
    gender = models.CharField(
        max_length=10,
        choices=[
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ],
        null=True,
        blank=True,
    )

    dob = models.DateField(null=True, blank=True)

    # roles
    role = models.CharField(
        max_length=20,
        choices=[
            ("user", "User"),
            ("admin", "Admin"),
        ],
        default="user",
    )

    # referral system
    referral_code = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
    )

    referred_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals",
    )

    # permissions
    is_active = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    # timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # auth config
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    def __str__(self):
        return str(self.email)
    
    def get_full_name(self):
        return self.full_name
    def save(self, *args, **kwargs):
         if self.email:
             self.email = self.email.lower().strip()
         super().save(*args, **kwargs)

    
    # users/models.py
class PendingEmail(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    new_email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)




class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses"
    )
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.city}"









