from django.db.models import Sum

from .models import Category, Order, SiteSettings


def shop(request):
    cart_count = 0
    if request.user.is_authenticated:
        cart_count = request.user.cart_items.aggregate(n=Sum("quantity"))["n"] or 0
    pending = 0
    if request.user.is_authenticated and request.user.is_staff:
        pending = Order.objects.filter(status="pending").count()
    unread, recent = 0, []
    if request.user.is_authenticated:
        unread = request.user.notifications.filter(is_read=False).count()
        recent = list(request.user.notifications.all()[:6])
    return {
        "unread_count": unread,
        "recent_notifications": recent,
        "pending_orders": pending,
        "nav_categories": Category.objects.all(),
        "site": SiteSettings.get(),
        "cart_count": cart_count,
    }
