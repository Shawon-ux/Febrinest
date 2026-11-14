from django.contrib.auth.models import AbstractUser
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

    REQUIRED_FIELDS = ["email", "phone", "full_name"]

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        self.email = (self.email or "").lower()
        if not self.username:
            self.username = self.phone
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name or self.username} ({self.phone})"
