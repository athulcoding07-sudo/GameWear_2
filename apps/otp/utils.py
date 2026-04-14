from django.core.mail import send_mail


def send_otp_email(
    to_email,
    user_name,
    otp,
    purpose,
    expiry_minutes= 2
):
    subject_map = {
        "signup": "Verify your GameWear account",
        "login": "GameWear Login OTP",
        "forgot_password": "Reset your GameWear password",
        "email_change": "Confirm your new email",
    }

    subject = subject_map.get(purpose, "Your GameWear OTP")

    message = (
        f"Hello {user_name},\n\n"
        f"Your OTP for {purpose.replace('_', ' ')} is: {otp}\n"
        f"This OTP is valid for {expiry_minutes} minutes.\n\n"
        "If you did not request this, please ignore this email.\n\n"
        "— Team GameWear"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email="no-reply@gamewear.com",
        recipient_list=[to_email],
    )
