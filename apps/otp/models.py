from django.db import models
from django.conf import settings
from django.utils import timezone

class OTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    purpose = models.CharField(max_length=50)
    code = models.CharField(max_length=6)

    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    resend_count = models.PositiveIntegerField(default=0)
    last_sent_at = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.user.email} - {self.purpose}"


# Create your models here.
