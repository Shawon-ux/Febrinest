from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import normalize_phone, phone_validator

from .filters import filter_products
from .forms import CheckoutForm
from .models import CartItem, Category, Order, OrderItem, Product, Review, SiteSettings


SECTION_IMG = {
    "shirt": "denim-shirt.jpg", "pant": "jeans2.jpg", "t-shirt": "tee-white.jpg",
    "polo-shirt": "tees-green.jpg", "panjabi": "rack.jpg", "hoodie": "sweat.jpg", "jacket": "model-jacket.jpg",
}


def home(request):
    products = Product.objects.filter(is_active=True).select_related("category").prefetch_related("sizes")
    sections = Category.objects.annotate(
        n=Count("products", filter=Q(products__is_active=True))
    ).filter(n__gt=0)
    sections = list(sections)
    for c in sections:
        c.cover = SECTION_IMG.get(c.slug, "store.jpg")
    return render(request, "store/home.html", {
        "sections": sections,
        "latest": products[:8],
    })


def shop(request, slug=None):
    category = get_object_or_404(Category, slug=slug) if slug else None
    qs = Product.objects.filter(is_active=True)
    if category:
        qs = qs.filter(category=category)
    qs, ctx = filter_products(request, qs, fixed_category=category)
    ctx.update(products=qs, category=category, base_url=request.path)
    return render(request, "store/shop.html", ctx)


def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("sizes"), pk=pk, is_active=True
    )
    related = Product.objects.filter(category=product.category, is_active=True).exclude(pk=pk)[:4]
    reviews = product.reviews.select_related("user")
    mine = reviews.filter(user=request.user).first() if request.user.is_authenticated else None
    return render(request, "store/product.html", {
        "product": product, "related": related, "reviews": reviews, "my_review": mine,
    })


@login_required
@require_POST
def review_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    comment = request.POST.get("comment", "").strip()[:1000]
    try:
        rating = max(1, min(5, int(request.POST.get("rating", 5))))
    except ValueError:
        rating = 5
    if not comment:
        messages.error(request, "Please write a comment.")
    else:
        Review.objects.update_or_create(
            product=product, user=request.user, defaults={"rating": rating, "comment": comment})
        messages.success(request, "Thanks for your review!")
    return redirect(f"{product.get_absolute_url()}#reviews")


@staff_member_required(login_url="accounts:login")
@require_POST
def review_delete(request, pk):
    r = get_object_or_404(Review, pk=pk)
    r.delete()
    messages.success(request, "Review deleted.")
    return redirect(request.POST.get("next") or r.product.get_absolute_url())


# ---------------------------------------------------------------- cart
@login_required
def cart(request):
    items = list(request.user.cart_items.select_related("product"))
    for i in items:
        i.ok = i.size_ok
    subtotal = sum(i.line_total for i in items)
    return render(request, "store/cart.html", {
        "items": items,
        "subtotal": subtotal,
        "has_blocked": any(not i.ok for i in items),
    })


@require_POST
def cart_add(request, pk):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in (phone number required) to add items to your cart.")
        return redirect(f"/accounts/login/?next={request.POST.get('next') or '/'}")
    product = get_object_or_404(Product, pk=pk, is_active=True)
    size = request.POST.get("size", "")
    try:
        qty = max(1, min(int(request.POST.get("quantity", 1)), 20))
    except ValueError:
        qty = 1
    if not product.sizes.filter(size=size, available=True).exists():
        messages.error(request, f"Size {size or '—'} is not available for {product.name}. Please choose another size.")
        return redirect(product)
    item, created = CartItem.objects.get_or_create(
        user=request.user, product=product, size=size, defaults={"quantity": qty}
    )
    if not created:
        item.quantity = min(item.quantity + qty, 20)
        item.save()
    messages.success(request, f"{product.name} (size {size}) added to your cart.")
    if request.POST.get("go") == "cart":
        return redirect("store:cart")
    return redirect(request.POST.get("next") or product)


@login_required
@require_POST
def cart_update(request, pk):
    item = get_object_or_404(CartItem, pk=pk, user=request.user)
    try:
        item.quantity = max(1, min(int(request.POST.get("quantity", 1)), 20))
        item.save()
    except ValueError:
        pass
    return redirect("store:cart")


@login_required
@require_POST
def cart_remove(request, pk):
    get_object_or_404(CartItem, pk=pk, user=request.user).delete()
    messages.info(request, "Item removed from your cart.")
    return redirect("store:cart")


# ---------------------------------------------------------------- checkout
@login_required
def checkout(request):
    items = list(request.user.cart_items.select_related("product"))
    if not items:
        messages.info(request, "Your cart is empty.")
        return redirect("store:home")
    blocked = [i for i in items if not i.size_ok]
    if blocked:
        messages.error(request, "Some items are no longer available in that size. Remove them to continue.")
        return redirect("store:cart")

    site = SiteSettings.get()
    subtotal = sum(i.line_total for i in items)
    form = CheckoutForm(request.POST or None, initial={
        "full_name": request.user.full_name, "phone": request.user.phone,
    })
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        delivery = site.delivery_inside if cd["area"] == Order.AREA_INSIDE else site.delivery_outside
        online = cd["payment_method"] != Order.PAY_COD
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user, full_name=cd["full_name"], phone=cd["phone"],
                address=cd["address"], area=cd["area"], subtotal=subtotal,
                delivery_charge=delivery, total=subtotal + delivery,
                payment_method=cd["payment_method"],
                payment_status=Order.PAY_VERIFY if online else Order.PAY_UNPAID,
                transaction_id=cd["transaction_id"] if online else "",
            )
            OrderItem.objects.bulk_create([
                OrderItem(order=order, product=i.product, name=i.product.name, size=i.size,
                          price=i.product.price, quantity=i.quantity) for i in items
            ])
            request.user.cart_items.all().delete()
        return redirect("store:order_done", pk=order.pk)

    return render(request, "store/checkout.html", {
        "form": form, "items": items, "subtotal": subtotal,
        "delivery_inside": site.delivery_inside, "delivery_outside": site.delivery_outside,
    })


@login_required
def order_done(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, "store/order_done.html", {"order": order})


@login_required
def my_orders(request):
    orders = request.user.orders.prefetch_related("items")
    return render(request, "store/my_orders.html", {"orders": orders})
