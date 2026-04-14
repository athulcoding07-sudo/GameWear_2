from django import forms
from apps.users.models import User
import re


class UserForm(forms.ModelForm):
    first_name = forms.CharField()
    last_name = forms.CharField()

    class Meta:
        model = User
        fields = ["email", "is_active", "profile_image"]

    # 🔹 Email validation
    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()

        qs = User.objects.filter(email=email)

        # Exclude current instance (for edit)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Email already exists.")

        return email

    # 🔹 Full form validation
    def clean(self):
        cleaned_data = super().clean()

        first = cleaned_data.get("first_name", "").strip()
        last = cleaned_data.get("last_name", "").strip()

        name_pattern = r"^[A-Za-z\s'-]+$"  # supports real names

        # First name validation
        if not first:
            self.add_error("first_name", "First name is required.")
        elif not re.match(name_pattern, first):
            self.add_error("first_name", "Only letters are allowed.")

        # Last name validation
        if not last:
            self.add_error("last_name", "Last name is required.")
        elif not re.match(name_pattern, last):
            self.add_error("last_name", "Only letters are allowed.")

        return cleaned_data

    # 🔹 Save full_name
    def save(self, commit=True):
        instance = super().save(commit=False)

        first = self.cleaned_data.get("first_name", "").strip()
        last = self.cleaned_data.get("last_name", "").strip()

        instance.full_name = f"{first} {last}"

        if commit:
            instance.save()

        return instance
    