from django import forms
from django.contrib.auth import get_user_model
from .models import PendingEmail,Address
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from datetime import date


User = get_user_model()





class UserSignupForm(forms.ModelForm):

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Password"})
    )

    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm Password"})
    )

    referral_code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Referral Code"})
    )

    class Meta:
        model = User
        fields = ["full_name", "email", "phone_number"]

        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Full name"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com"}),
            "phone_number": forms.TextInput(attrs={"placeholder": "9876543210"}),
        }

    # ---------- INIT ----------

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        common_classes = (
            "w-full px-4 py-3 bg-neutral-800 border border-neutral-700 "
            "rounded-lg focus:ring-2 focus:ring-white text-white"
        )

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", common_classes)

    # ---------- FIELD VALIDATIONS ----------

    def clean_email(self):
        email = self.cleaned_data.get("email").lower()

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")

        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")

        if phone and not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")

        if phone and User.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError("This phone number is already registered.")

        return phone

    # ---------- PASSWORD VALIDATION ----------

    def clean_password1(self):
        password = self.cleaned_data.get("password1")

        try:
            validate_password(password)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)

        return password

    def clean(self):
        cleaned_data = super().clean()

        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")

        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")

        return cleaned_data

    # ---------- SAVE ----------

    def save(self, commit=True):
        user = super().save(commit=False)

        user.set_password(self.cleaned_data["password1"])

        code = self.cleaned_data.get("referral_code")

        if code:
            try:
                user.referred_by = User.objects.get(referral_code=code)
            except User.DoesNotExist:
                self.add_error("referral_code", "Invalid referral code")

        if commit:
            user.save()

        return user





class UserEditProfileForm(forms.ModelForm):

    phone_validator = RegexValidator(
        regex=r"^[6-9]\d{9}$",
        message="Enter a valid 10-digit Indian phone number starting with 6-9."
    )

    class Meta:
        model = User
        fields = ["full_name", "phone_number", "dob", "gender", "profile_image"]

        widgets = {
            "dob": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full bg-black border border-neutral-800 rounded-xl px-4 py-4 text-sm text-white focus:border-white focus:outline-none transition",
                }
            )
        }

    # ---------- PHONE VALIDATION ----------

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")

        if not phone:
            return phone

        # regex validation
        self.phone_validator(phone)

        # prevent repeating numbers (0000000000, 1111111111 etc)
        if len(set(phone)) == 1:
            raise forms.ValidationError(
                "Phone number cannot contain the same digit repeated."
            )

        # unique validation
        if User.objects.filter(phone_number=phone).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This phone number is already in use.")

        return phone

    # ---------- DOB VALIDATION ----------

    def clean_dob(self):
        dob = self.cleaned_data.get("dob")

        if dob and dob > date.today():
            raise forms.ValidationError("Date of birth cannot be in the future.")

        return dob








class EmailChangeForm(forms.ModelForm):
    class Meta:
        model = PendingEmail
        fields = ["new_email"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)  # ✅ remove user safely
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        new_email = self.cleaned_data.get("new_email")

        if not self.user:
            raise forms.ValidationError("User context is missing.")

        # 1️⃣ Same as current email
        if new_email == self.user.email:
            raise forms.ValidationError(
                "This is already your current email."
            )

        # 2️⃣ Email already used by another user
        if User.objects.filter(email=new_email).exists():
            raise forms.ValidationError(
                "This email is already registered."
            )

        # 3️⃣ Email pending for another user
        if PendingEmail.objects.filter(
            new_email=new_email
        ).exclude(user=self.user).exists():
            raise forms.ValidationError(
                "This email is already pending verification."
            )

        return new_email




class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "full_name",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "is_default",
        ]