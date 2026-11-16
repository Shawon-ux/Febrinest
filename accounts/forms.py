from django import forms
from django.contrib.auth import authenticate, password_validation

from .models import User, normalize_phone, phone_validator


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    class Meta:
        model = User
        fields = ["full_name", "email", "phone"]
        labels = {"full_name": "Full name", "email": "Gmail / Email"}

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        phone_validator(phone)
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("confirm_password"):
            self.add_error("confirm_password", "Passwords do not match.")
        elif data.get("password"):
            password_validation.validate_password(data["password"])
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    identifier = forms.CharField(label="Phone number or Email")
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        if data.get("identifier") and data.get("password"):
            self.user = authenticate(
                self.request, username=data["identifier"], password=data["password"]
            )
            if self.user is None:
                raise forms.ValidationError("Wrong phone/email or password.")
        return data


class AdminCreateForm(RegisterForm):
    """Main admin creates another admin: name, email, phone, password."""

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Customers may edit their name only; phone changes go through admin approval."""

    class Meta:
        model = User
        fields = ["full_name"]
        labels = {"full_name": "Full name"}


class AdminProfileForm(forms.ModelForm):
    """Admins can edit their own name and phone directly, no approval needed."""

    class Meta:
        model = User
        fields = ["full_name", "phone"]
        labels = {"full_name": "Full name", "phone": "Phone number"}

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        phone_validator(phone)
        if User.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another account already uses this number.")
        return phone

    def save(self, commit=True):
        old = User.objects.get(pk=self.instance.pk).phone
        user = super().save(commit=False)
        if user.username == old:
            user.username = user.phone
        if commit:
            user.save()
        return user


class PhoneChangeForm(forms.Form):
    new_phone = forms.CharField(label="New phone number")

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_phone(self):
        phone = normalize_phone(self.cleaned_data["new_phone"])
        phone_validator(phone)
        if phone == self.user.phone:
            raise forms.ValidationError("That is already your phone number.")
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("Another account already uses this number.")
        return phone
