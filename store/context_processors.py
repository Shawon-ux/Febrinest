from django.db.models import Sum

from .models import Category, SiteSettings


def shop(request):
    cart_count = 0
    if request.user.is_authenticated:
        cart_count = request.user.cart_items.aggregate(n=Sum("quantity"))["n"] or 0
    return {
        "nav_categories": Category.objects.all(),
        "site": SiteSettings.get(),
        "cart_count": cart_count,
    }
