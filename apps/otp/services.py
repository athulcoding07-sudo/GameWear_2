import random
from datetime import timedelta
from django.utils import timezone
from .models import OTP
from .utils import send_otp_email

OTP_EXPIRY_MINUTES = 2
RESEND_COOLDOWN_SECONDS = 60
MAX_RESENDS = 3


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp(user, purpose, email=None):
    # invalidate old OTPs of same purpose
    OTP.objects.filter(
        user=user,
        purpose=purpose,
        is_used=False
    ).update(is_used=True)

    otp = OTP.objects.create(
        user=user,
        purpose=purpose,
        code=generate_otp(),
        expires_at=timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )

    to_email = email if email else user.email

    send_otp_email(
        to_email=to_email,
        user_name=user.full_name,
        otp=otp.code,
        purpose=otp.purpose,
        expiry_minutes=OTP_EXPIRY_MINUTES
    )

    return otp


def verify_otp(user, purpose, code):

    otp = OTP.objects.filter(
        user=user,
        purpose=purpose,
        is_used=False
    ).order_by("-created_at").first()

    if not otp:
        return False, "OTP not found"

    if otp.is_expired():
        return False, "OTP expired"

    if otp.code != code:
        return False, "Invalid OTP"

    otp.is_used = True
    otp.save(update_fields=["is_used"])

    return True, "OTP verified"


def resend_otp(user, purpose, email=None):
    try:
        otp = OTP.objects.filter(
            user=user,
            purpose=purpose,
            is_used=False
        ).latest("last_sent_at")
    except OTP.DoesNotExist:
        return False, "OTP not found"

    if timezone.now() < otp.last_sent_at + timedelta(seconds=RESEND_COOLDOWN_SECONDS):
        return False, "Please wait before resending"

    if otp.resend_count >= MAX_RESENDS:
        return False, "Resend limit reached"

    otp.is_used = True
    otp.save(update_fields=["is_used"])

    new_otp = OTP.objects.create(
        user=user,
        purpose=purpose,
        code=generate_otp(),
        expires_at=timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
        resend_count=otp.resend_count + 1,
    )

    to_email = email if email else user.email

    send_otp_email(
        to_email=to_email,
        user_name=user.full_name,
        otp=new_otp.code,
        purpose=new_otp.purpose,
        expiry_minutes=OTP_EXPIRY_MINUTES
    )

    return True, "OTP resent successfully"
