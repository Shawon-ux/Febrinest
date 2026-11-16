from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.db.models.deletion import ProtectedError
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.forms import AdminCreateForm
from accounts.models import PhoneChangeRequest, User

from .filters import filter_products
from .forms import CategoryForm, ProductForm, SettingsForm
from .notify import customers, notify
from .sms import send_sms
from .models import Category, Order, Product, ProductSize, Review, SiteSettings

staff = staff_member_required(login_url="accounts:login")


@staff
def home(request):
    return render(request, "dashboard/home.html", {
        "n_products": Product.objects.count(),
        "n_sections": Category.objects.count(),
        "n_reviews": Review.objects.count(),
        "n_admins": User.objects.filter(is_staff=True).count(),
    })


# ------------------------------------------------------------ products
@staff
def products(request):
    qs, ctx = filter_products(request, Product.objects.all())
    ctx.update(products=qs, base_url=request.path)
    return render(request, "dashboard/products.html", ctx)


@staff
def product_form(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None
    if not Category.objects.exists():
        messages.info(request, "Create a section (e.g. Pants, Shirts) first.")
        return redirect("dashboard:category_new")
    initial = {}
    if not product and request.GET.get("category", "").isdigit():
        initial["category"] = int(request.GET["category"])
    old_price = product.price if product else None
    form = ProductForm(request.POST or None, request.FILES or None, instance=product, initial=initial)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        if saved.is_active:
            if product is None:
                notify(customers(), f"New arrival: {saved.name}",
                       f"Now in {saved.category.name} · ৳{saved.price}", saved.get_absolute_url())
            elif old_price is not None and saved.price < old_price:
                notify(customers(), f"Price drop: {saved.name}",
                       f"Now ৳{saved.price} (was ৳{old_price})", saved.get_absolute_url())
        messages.success(request, f"“{saved.name}” saved.")
        return redirect("dashboard:products")
    return render(request, "dashboard/product_form.html", {"form": form, "product": product})


@staff
@require_POST
def product_delete(request, pk):
    p = get_object_or_404(Product, pk=pk)
    p.delete()
    messages.success(request, f"“{p.name}” deleted.")
    nxt = request.POST.get("next", "")
    if nxt.startswith("/") and not nxt.startswith("//"):
        return redirect(nxt)
    return redirect("dashboard:products")


@staff
@require_POST
def size_toggle(request, pk):
    """One-click lock/unlock of a size from the product list."""
    s = get_object_or_404(ProductSize, pk=pk)
    s.available = not s.available
    s.save()
    state = "available" if s.available else "blocked (stock out)"
    messages.success(request, f"{s.product.name}: size {s.size} is now {state}.")
    return redirect(request.POST.get("next") or "dashboard:products")


# ------------------------------------------------------------ categories
@staff
def categories(request):
    return render(request, "dashboard/categories.html", {
        "categories": Category.objects.annotate(n=Count("products")),
    })


@staff
def category_form(request, pk=None):
    cat = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryForm(request.POST or None, instance=cat)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Section saved.")
        return redirect("dashboard:categories")
    return render(request, "dashboard/category_form.html", {"form": form, "cat": cat})


@staff
@require_POST
def category_delete(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    try:
        cat.delete()
        messages.success(request, "Section deleted.")
    except ProtectedError:
        messages.error(request, "This section still has products. Move or delete them first.")
    return redirect("dashboard:categories")


# ------------------------------------------------------------ orders
@staff
def orders(request):
    qs = Order.objects.select_related("user").prefetch_related("items")
    status = request.GET.get("status", "")
    pay = request.GET.get("payment", "")
    if status:
        qs = qs.filter(status=status)
    if pay:
        qs = qs.filter(payment_status=pay)
    return render(request, "dashboard/orders.html", {
        "orders": qs, "status": status, "pay": pay,
        "statuses": Order.STATUSES, "pay_statuses": Order.PAYMENT_STATUSES,
    })


@staff
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
    if request.method == "POST":
        status, pay = request.POST.get("status"), request.POST.get("payment_status")
        if status in dict(Order.STATUSES):
            order.status = status
        if pay in dict(Order.PAYMENT_STATUSES):
            order.payment_status = pay
        old_status, old_pay = Order.objects.values_list("status", "payment_status").get(pk=order.pk)
        order.save()
        link = reverse("store:my_orders")
        if order.payment_status != old_pay and order.payment_status == Order.PAY_PAID:
            notify(order.user, f"Payment received for order #{order.pk}", "Thank you! We have confirmed your payment.", link)
        if order.status != old_status:
            notify(order.user, f"Order #{order.pk} is {order.get_status_display().lower()}", "", link)
        messages.success(request, f"Order #{order.pk} updated.")
        nxt = request.POST.get("next", "")
        if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
            return redirect(nxt)
        return redirect("dashboard:order_detail", pk=pk)
    return render(request, "dashboard/order_detail.html", {
        "order": order, "statuses": Order.STATUSES, "pay_statuses": Order.PAYMENT_STATUSES,
    })


@staff
@require_POST
def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order.delete()
    messages.success(request, f"Order #{pk} deleted.")
    return redirect("dashboard:orders")


# ------------------------------------------------------------ settings
@staff
def settings_view(request):
    form = SettingsForm(request.POST or None, instance=SiteSettings.get())
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Settings saved. New delivery charges apply to the next orders.")
        return redirect("dashboard:settings")
    return render(request, "dashboard/settings.html", {"form": form})


@staff
def reviews(request):
    return render(request, "dashboard/reviews.html", {
        "reviews": Review.objects.select_related("user", "product"),
    })


# ------------------------------------------------------------ admins
@staff
def admins(request):
    form = AdminCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        u = form.save()
        messages.success(request, f"{u.full_name} is now an admin. They can log in with {u.phone} or {u.email}.")
        return redirect("dashboard:admins")
    return render(request, "dashboard/admins.html", {
        "form": form,
        "admins": User.objects.filter(is_staff=True).order_by("-is_main_admin", "date_joined"),
    })


@staff
@require_POST
def admin_delete(request, pk):
    target = get_object_or_404(User, pk=pk, is_staff=True)
    if target.is_main_admin:
        messages.error(request, "The main admin cannot be removed.")
    elif target.pk == request.user.pk:
        messages.error(request, "You can't remove your own account while logged in.")
    else:
        name = target.full_name
        target.delete()
        messages.success(request, f"Admin {name} removed.")
    return redirect("dashboard:admins")


@staff
@require_POST
def order_payment_failed(request, pk):
    """Admin could not find the payment: tell the customer by SMS + in-site notification."""
    order = get_object_or_404(Order, pk=pk)
    order.payment_status = Order.PAY_FAILED
    order.save(update_fields=["payment_status"])
    msg = (f"Febrinest: Hi {order.full_name}, we did not receive your payment for order #{order.pk} "
           f"(Tk {order.total}). You may have given a wrong Transaction ID. We will call you soon for verification.")
    sent, info = send_sms(order.phone, msg)
    notify(order.user, f"Payment not received for order #{order.pk}",
           "You may have entered a wrong Transaction ID. We will call you soon for verification.",
           reverse("store:my_orders"))
    if sent:
        messages.success(request, f"SMS sent to {order.phone}: payment not received.")
    else:
        messages.warning(request, f"Customer notified on the website, but the SMS was NOT sent ({info}). "
                                  "Use the ✉ SMS menu or call them.")
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect("dashboard:order_detail", pk=pk)


@staff
def announce(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()[:140]
        body = request.POST.get("body", "").strip()[:400]
        link = request.POST.get("url", "").strip()
        if not link.startswith("/"):
            link = ""
        if not title:
            messages.error(request, "Please enter a title.")
        else:
            targets = list(customers())
            notify(targets, title, body, link)
            messages.success(request, f"Sent to {len(targets)} customer{'s' if len(targets) != 1 else ''}.")
            return redirect("dashboard:announce")
    return render(request, "dashboard/announce.html", {"n_customers": customers().count()})


# ------------------------------------------------------------ phone change requests
@staff
def phone_requests(request):
    return render(request, "dashboard/phone_requests.html", {
        "pending": PhoneChangeRequest.objects.filter(status=PhoneChangeRequest.PENDING).select_related("user"),
        "recent": PhoneChangeRequest.objects.exclude(status=PhoneChangeRequest.PENDING).select_related("user")[:20],
    })


@staff
@require_POST
def phone_request_decide(request, pk, decision):
    req = get_object_or_404(PhoneChangeRequest, pk=pk, status=PhoneChangeRequest.PENDING)
    if decision == "approve":
        if User.objects.filter(phone=req.new_phone).exclude(pk=req.user_id).exists():
            messages.error(request, "That number is now used by another account. Reject the request.")
            return redirect("dashboard:phone_requests")
        u = req.user
        if u.username == u.phone:
            u.username = req.new_phone
        u.phone = req.new_phone
        u.save()
        req.status = PhoneChangeRequest.APPROVED
        notify(u, "Phone number updated", f"Your phone number is now {req.new_phone}.", reverse("accounts:profile"))
        messages.success(request, f"{u.full_name}'s phone changed to {req.new_phone}.")
    elif decision == "reject":
        req.status = PhoneChangeRequest.REJECTED
        notify(req.user, "Phone change request rejected", "Contact us if you need help.", reverse("accounts:profile"))
        messages.info(request, "Request rejected.")
    else:
        return redirect("dashboard:phone_requests")
    req.save(update_fields=["status"])
    return redirect("dashboard:phone_requests")
