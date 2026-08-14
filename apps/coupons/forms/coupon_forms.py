from django import forms
from django.utils import timezone

from apps.coupons.models import Coupon


class CouponForm(forms.ModelForm):

    class Meta:
        model = Coupon

        fields = [
            "code",
            "discount_percentage",
            "minimum_amount",
            # "maximum_discount",
            "valid_from",
            "valid_to",
            
            "is_active",
        ]

        widgets = {
            "valid_from": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                }
            ),

            "valid_to": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                }
            ),
        }

    def clean_code(self):
        code = self.cleaned_data.get("code")

        if not code:
            raise forms.ValidationError(
                "Coupon code is required.",
            )

        code = code.strip().upper()

        if " " in code:
            raise forms.ValidationError(
                "Coupon code cannot contain spaces.",
            )

        return code

    def clean_discount_percentage(self):
        discount_percentage = self.cleaned_data.get(
            "discount_percentage"
        )

        if discount_percentage <= 0:
            raise forms.ValidationError(
                "Discount percentage must be greater than zero.",
            )

        if discount_percentage > 100:
            raise forms.ValidationError(
                "Discount percentage cannot exceed 100.",
            )

        return discount_percentage

    def clean_minimum_amount(self):
        minimum_amount = self.cleaned_data.get(
            "minimum_amount"
        )

        if minimum_amount < 0:
            raise forms.ValidationError(
                "Minimum amount cannot be negative.",
            )

        return minimum_amount

    # def clean_maximum_discount(self):
    #     maximum_discount = self.cleaned_data.get(
    #         "maximum_discount"
    #     )

    #     if maximum_discount <= 0:
    #         raise forms.ValidationError(
    #             "Maximum discount must be greater than zero.",
    #         )

    #     return maximum_discount

    

    def clean(self):
        cleaned_data = super().clean()

        valid_from = cleaned_data.get("valid_from")
        valid_to = cleaned_data.get("valid_to")

        if valid_from and valid_to:

            # Make naive datetimes timezone-aware for comparison
            if timezone.is_naive(valid_from):
                valid_from = timezone.make_aware(valid_from)
                cleaned_data["valid_from"] = valid_from

            if timezone.is_naive(valid_to):
                valid_to = timezone.make_aware(valid_to)
                cleaned_data["valid_to"] = valid_to

            if valid_from >= valid_to:
                raise forms.ValidationError(
                    "End date must be greater than start date.",
                )

            if valid_to <= timezone.now():
                raise forms.ValidationError(
                    "Coupon expiry date must be in the future.",
                )

        return cleaned_data