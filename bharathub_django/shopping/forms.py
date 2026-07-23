from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "price", "unit", "stock", "description", "image"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Dell Laptop Repair"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "price": forms.NumberInput(attrs={"class": "form-input", "placeholder": "5000"}),
            "unit": forms.Select(attrs={"class": "form-select"}),
            "stock": forms.NumberInput(attrs={"class": "form-input", "placeholder": "100"}),
            "description": forms.Textarea(attrs={"class": "form-textarea", "rows": 2}),
            "image": forms.ClearableFileInput(attrs={"class": "form-input"}),
        }
