from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .models import normalize_phone


class PhoneOrEmailBackend(ModelBackend):
    """Log in with phone number OR email + password."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        ident = (username or kwargs.get(User.USERNAME_FIELD) or "").strip()
        if not ident or not password:
            return None
        if "@" in ident:
            user = User.objects.filter(email__iexact=ident).first()
        else:
            user = User.objects.filter(phone=normalize_phone(ident)).first()
            if user is None:  # e.g. the auto-created superuser username
                user = User.objects.filter(username=ident).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
