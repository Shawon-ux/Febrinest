from django import forms

from accounts.models import normalize_phone, phone_validator

from .models import SIZES, Category, Order, Product, SiteSettings


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=120)
    phone = forms.CharField(max_length=20)
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), label="Full delivery address")
    area = forms.ChoiceField(choices=Order.AREAS, widget=forms.RadioSelect, initial=Order.AREA_INSIDE)
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHODS, widget=forms.RadioSelect, initial=Order.PAY_COD
    )
    transaction_id = forms.CharField(
        max_length=60, required=False, label="Your bKash/Nagad/Rocket number & TrxID"
    )

    def clean_phone(self):
        p = normalize_phone(self.cleaned_data["phone"])
        phone_validator(p)
        return p

    def clean(self):
        data = super().clean()
        pm = data.get("payment_method")
        if pm and pm != Order.PAY_COD and not data.get("transaction_id", "").strip():
            self.add_error("transaction_id", "Enter the Transaction ID (TrxID) of your payment.")
        return data


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "position"]
        labels = {"position": "Display order (0 = first)"}


STATE_CHOICES = [("none", "Not offered"), ("available", "Available"), ("blocked", "Blocked (stock out)")]


class ProductForm(forms.ModelForm):
    """Product fields + one availability dropdown per size."""

    class Meta:
        model = Product
        fields = ["category", "name", "description", "price", "old_price", "image", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = {}
        if self.instance.pk:
            current = {s.size: ("available" if s.available else "blocked") for s in self.instance.sizes.all()}
        for s in SIZES:
            self.fields[f"size_{s}"] = forms.ChoiceField(
                choices=STATE_CHOICES, required=False, initial=current.get(s, "none"), label=s
            )

    def size_fields(self):
        return [self[f"size_{s}"] for s in SIZES]

    def clean(self):
        data = super().clean()
        if not any(data.get(f"size_{s}") in ("available", "blocked") for s in SIZES):
            raise forms.ValidationError("Choose at least one size for this product.")
        return data

    def save(self, commit=True):
        product = super().save(commit)
        if commit:
            for s in SIZES:
                state = self.cleaned_data.get(f"size_{s}") or "none"
                if state == "none":
                    product.sizes.filter(size=s).delete()
                else:
                    product.sizes.update_or_create(size=s, defaults={"available": state == "available"})
        return product


class SettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ["delivery_inside", "delivery_outside", "bkash_number", "nagad_number",
                  "rocket_number", "contact_phone"]
