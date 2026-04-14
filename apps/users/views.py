from django.shortcuts import render,redirect
from django.contrib import messages
from django.db import IntegrityError
from .forms import UserSignupForm,UserEditProfileForm,EmailChangeForm,AddressForm
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.shortcuts import get_object_or_404
from apps.otp.services import send_otp,verify_otp,resend_otp
from django.contrib.auth import update_session_auth_hash
from .models import PendingEmail,Address
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from apps.products.models import Category
from apps.otp.models import OTP



# Create your views here.



User = get_user_model()


def signup_view(request):
    """
    Handles user registration with Email OTP verification.

    - GET  → Display signup form
    - POST → Validate form, create inactive user, send OTP, redirect to OTP verify
    """

    if request.method == "POST":
        form = UserSignupForm(request.POST)

        try:
            if form.is_valid():
                # Create user but do NOT activate yet
                user = form.save(commit=False)
                user.is_active = False
                user.save()
                # Send OTP email
                send_otp(user, "signup")
                # Store user id in session for OTP verification
                request.session["signup_user_id"] = user.id
                messages.success(request, "OTP sent to your email. Please verify.")
                return redirect("users:verify_signup_otp")
            else:
                messages.error(request, "Please correct the errors below.")
        except IntegrityError:
            messages.error(
                request,
                "A user with this email or phone already exists."
            )
        except Exception:
            messages.error(
                request,
                "Something went wrong. Please try again later."
            )
    else:
        form = UserSignupForm()

    return render(request, "users/signup.html", {"form": form})





def verify_signup_otp(request):

    user_id = request.session.get("signup_user_id")
    if not user_id:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect("users:signup")

    user = get_object_or_404(User, id=user_id)

    # get latest OTP
    otp = OTP.objects.filter(
        user=user,
        purpose="signup",
        is_used=False
    ).last()

    remaining_seconds = 0

    if otp:
        remaining_seconds = int((otp.expires_at - timezone.now()).total_seconds())

        if remaining_seconds < 0:
            remaining_seconds = 0

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        success, message = verify_otp(user, "signup", entered_otp)

        if success:
            user.is_active = True
            user.save(update_fields=["is_active"])

            request.session.pop("signup_user_id", None)

            messages.success(request, "Account verified successfully. Please log in.")
            return redirect("users:login")

        messages.error(request, message)

    return render(
        request,
        "users/verify_signup_otp.html",
        {"remaining_seconds": remaining_seconds}
    )





def resend_signup_otp(request):
    """
    Resend signup OTP
    - get the id and checke it
    - then we provide there resent the otp
    """

    user_id = request.session.get("signup_user_id")
    if not user_id:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect("users:signup")

    user = get_object_or_404(User, id=user_id)

    success, message = resend_otp(user, "signup")
    messages.info(request, message)

    return redirect("users:verify_signup_otp")


def login_view(request):
    """
    Handles user login:
    - Authenticate user
    - Check blocked status
    - Redirect admin or user accordingly
    """
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)
        if user is None:
            messages.error(request, "Invalid credentials or account blocked")
            return redirect("users:login")
        if user.is_blocked:
            messages.error(request, "Your account has been blocked!")
            return redirect("users:login")
        login(request, user)
        messages.success(request, "Login successful")
        if user.is_staff or user.role == "admin":
            return redirect("adminpanel:dashboard")
        return redirect("users:dashboard")
    return render(request, "users/login.html")


@never_cache
@require_POST
def logout_view(request):
    logout(request)
    return redirect("home:landing")



def forgot_password_view(request):
    """
    - show the email input form
    - get email,sent otp,redirect to  otp verify page
    """
    if request.method == "POST":


        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            send_otp(user,"reset_password")
            request.session['reset_user_id'] = user.id
            messages.success(request,"OTP sent to your email.")
            return redirect("users:verify_reset_otp")
        except User.DoesNotExist:
            messages.error(request,"No account found with this email.")

        except Exception:
            messages.error(request,"Something went wrong. Please try again later.")

    return render(request,"users/forgot_password.html")

def verify_reset_otp(request):
    """
    verify otp for password reset
    """
    user_id = request.session['reset_user_id']
    if not user_id:
        messages.error(request,"Session expired. Please try again.")
        return redirect("users:forgot_password")
    user = get_object_or_404(User, id = user_id)
    if request.method == "POST":
        entered_otp = request.POST.get('otp')
        success,message = verify_otp(user,'reset_password',entered_otp)
        if success:
            messages.success(request, "OTP verified. Set a new password.")
            return redirect("users:reset_password")
        messages.error(request, message)

    return render(request,'users/verify_reset_otp.html')


def resend_reset_otp(request):
    """
    - resend the otp
    - check the user_id
    - comform user exist then send the otp
    """
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, "Session expired. Please try again.")
        return redirect("users:forgot_password")
    user = get_object_or_404(User,id = user_id)
    success, message = resend_otp(user, "reset_password")
    messages.info(request, message)

    return redirect("users:verify_reset_otp")



def reset_password_view(request):
    """
    - reset password

    """
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, "Session expired. Please try again.")
        return redirect("users:forgot_password")
    user = get_object_or_404(User,id = user_id)



    if request.method == "POST":

        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        print(f'{password1},{password2}')

        if not password1 or not password2:
            messages.error(request, "All fields are required.")
        elif password1 != password2:
            messages.error(request, "Passwords do not match.")
        else:
            user.password = make_password(password1)
            user.save(update_fields=["password"])
            # cleanup session
            request.session.pop("reset_user_id", None)
            messages.success(request, "Password reset successful. Please log in.")
            return redirect("users:login")
    return render(request,'users/reset_password.html',{"validlink": True})


@login_required
def user_dashboard(request):
    """
    User dashboard — shows active categories with images
    """

    categories = Category.objects.filter(is_active=True).order_by("name")

    context = {
        "categories": categories,
    }

    return render(request, "users/dashboard.html", context)

@login_required
def user_profile_view(request):
    """
    - show the user profile
    """

    return render(request, "users/profile/profile_view.html")

@login_required
def user_profile_edit_view(request):

    if request.method == "POST":
        form = UserEditProfileForm(
            request.POST,
            request.FILES,
            instance=request.user
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("users:user_profile_edit")

        # send validation errors to toast messages
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)

    else:
        form = UserEditProfileForm(instance=request.user)

    return render(
        request,
        "users/profile/edit_profile.html",
        {"form": form}
    )




@login_required
def user_update_password_view(request):
    """
    Allow logged-in user to update their password.
    - Verifies old password
    - Confirms new password match
    - Keeps user logged in after change
    """

    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password1 = request.POST.get("new_password1")
        new_password2 = request.POST.get("new_password2")

        if not old_password or not new_password1 or not new_password2:
            messages.error(request, "All fields are required.")
            return redirect("users:user_profile_edit")
        if not request.user.check_password(old_password):
            messages.error(request, "Current password is incorrect.")
            return redirect("users:user_profile_edit")
        if new_password1 != new_password2:
            messages.error(request, "New passwords do not match.")
            return redirect("users:user_profile_edit")
        request.user.set_password(new_password1)
        request.user.save()

        update_session_auth_hash(request, request.user)

        messages.success(request, "Password updated successfully.")
        return redirect("users:user_profile")

    return render(request, "users/update_password.html")



@login_required
def request_email_change_sent_otp(request):
    if request.method == "POST":
        form = EmailChangeForm(request.POST, user=request.user)

        if form.is_valid():
            new_email = form.cleaned_data["new_email"]
            PendingEmail.objects.update_or_create(
                user=request.user,
                defaults={"new_email": new_email}
            )
            send_otp(
                user=request.user,
                purpose="email_change",
                email=new_email
            )

            request.session["email_change"] = True
            messages.success(request, "OTP sent to new email.")
            return redirect("users:verify_email_change_otp")
    else:
        form = EmailChangeForm(user=request.user)  # ✅ also pass user on GET

    return render(
        request,
        "users/profile/email_view.html",
        {"form": form}
    )

@login_required
def verify_email_change_otp(request):
    if not request.session.get("email_change"):
        return redirect("users:user_profile_edit")

    if request.method == "POST":
        otp = request.POST.get("otp")
        if verify_otp(
            user=request.user,
            purpose="email_change",
            code=otp
        ):
            pending = PendingEmail.objects.get(user=request.user)
            # Update real email ONLY now
            request.user.email = pending.new_email
            request.user.save(update_fields=["email"])

            pending.delete()
            request.session.pop("email_change")

            messages.success(request, "Email updated successfully.")
            return redirect("users:user_profile_edit")

        messages.error(request, "Invalid or expired OTP.")

    return render(request, "users/profile/verify_email_otp.html")

@login_required
def resend_email_change_otp(request):
    """
    - resend email change otp
    - confirm session exists
    - confirm pending email exists
    - resend otp to NEW email
    """

    if not request.session.get("email_change"):
        messages.error(request, "Session expired. Please try again.")
        return redirect("users:user_profile_edit")
    try:
        pending = PendingEmail.objects.get(user=request.user)
    except PendingEmail.DoesNotExist:
        messages.error(request, "No pending email change found.")
        return redirect("users:user_profile_edit")
    # Reuse your existing resend_otp logic
    success, message = resend_otp(
        user=request.user,
        purpose="email_change",
        email=pending.new_email   # IMPORTANT
    )
    messages.info(request, message)
    return redirect("users:verify_email_change_otp")


@login_required
def address_view(request):
    # Fetch all addresses belonging to the logged-in user
    addresses = Address.objects.filter(user=request.user)
    return render(request, "users/profile/address/address_view.html", {
        "addresses": addresses
    })


@login_required
def add_address(request):
    if request.method == "POST":

        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            # If setting default, unset others
            if address.is_default:
                request.user.addresses.update(is_default=False)
            address.save()
            messages.success(request, "Address saved successfully.")
            return redirect("users:address_view")  # change to your page
        else:
            messages.error(request,'form is not valid')
    else:
        form = AddressForm()

    return render(request, "users/profile/address/address_view.html", {"form": form})


@login_required
def edit_address(request, address_id=None):
    # Check for the ID in the URL or the POST data to avoid TypeError
    target_id = address_id or request.POST.get('address_id')
    if not target_id:
        messages.error(request, "Address ID is missing.")
        return redirect("users:address_view")

    # Fetch the specific address belonging to the user
    address = get_object_or_404(Address, id=target_id, user=request.user)

    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            updated_address = form.save(commit=False)

            # If this address is being set as default, unset all others
            if updated_address.is_default:
                Address.objects.filter(user=request.user).exclude(id=target_id).update(is_default=False)

            updated_address.save()
            messages.success(request, "Address updated successfully.")
            return redirect("users:address_view")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AddressForm(instance=address)

    return render(request, "users/profile/address/address_view.html", {"form": form, "edit_address": address})

@login_required
def delete_address(request, address_id=None):
    # The error occurred because address_id was missing in the URL path.
    # We allow address_id to be None and check POST data as a fallback.
    target_id = address_id or request.POST.get('address_id')
    if not target_id:
        messages.error(request, "Address ID is missing.")
        return redirect("users:address_view")
    # Ensure user can only delete their own address
    address = get_object_or_404(Address, id=target_id, user=request.user)

    if request.method == "POST":
        address.delete()
        messages.success(request, "Address deleted successfully.")

    return redirect("users:address_view")


