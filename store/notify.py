from django.contrib.auth import get_user_model

from .models import Notification


def notify(users, title, body="", url=""):
    """Create one notification per user (accepts a queryset/list or a single user)."""
    if hasattr(users, "pk"):
        users = [users]
    Notification.objects.bulk_create(
        [Notification(user=u, title=title, body=body[:400], url=url) for u in users]
    )


def customers():
    return get_user_model().objects.filter(is_staff=False, is_active=True)


def admins():
    return get_user_model().objects.filter(is_staff=True, is_active=True)
