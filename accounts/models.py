from django.contrib.auth.models import AbstractUser
from django.core.exceptions import PermissionDenied
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    r"^(?:\+?88)?01[3-9]\d{8}$", "Enter a valid Bangladeshi mobile number, e.g. 01712345678."
)


def normalize_phone(raw: str) -> str:
    """Store every phone as 01XXXXXXXXX so login lookups are consistent."""
    p = "".join(ch for ch in (raw or "") if ch.isdigit())
    if p.startswith("880"):
        p = p[2:]
    return p


class User(AbstractUser):
    # `username` is kept (required by Django) and auto-filled from the phone number.
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=14, unique=True, validators=[phone_validator])

    # The owner account. Nobody (including other admins) can remove or demote it.
    is_main_admin = models.BooleanField(default=False, editable=False)

    REQUIRED_FIELDS = ["email", "phone", "full_name"]

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        self.email = (self.email or "").lower()
        if not self.username:
            self.username = self.phone
        if self.is_superuser and not self.is_main_admin and not User.objects.filter(is_main_admin=True).exists():
            self.is_main_admin = True
        if self.is_main_admin:
            self.is_staff = True
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_main_admin:
            raise PermissionDenied("The main admin cannot be deleted.")
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name or self.username} ({self.phone})"


class PhoneChangeRequest(models.Model):
    PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"
    STATUS = [(PENDING, "Pending"), (APPROVED, "Approved"), (REJECTED, "Rejected")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="phone_requests")
    new_phone = models.CharField(max_length=14, validators=[phone_validator])
    status = models.CharField(max_length=10, choices=STATUS, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
