from django import forms
from .models import Category, Product, ProductImage


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "description", "is_active"]
        widgets = {
            "slug": forms.TextInput(attrs={"placeholder": "Auto-generated if left blank"})
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        qs = Category.objects.filter(name__iexact=name)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Category with this name already exists")

        return name
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "description",
            "brand",
            "is_active",
            "is_featured",
            "is_listed",
        ]
class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "is_primary"]
