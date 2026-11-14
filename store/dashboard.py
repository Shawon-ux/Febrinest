from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .filters import filter_products
from .forms import CategoryForm, ProductForm, SettingsForm
from .models import Category, Order, Product, ProductSize, SiteSettings

staff = staff_member_required(login_url="accounts:login")


@staff
def home(request):
    return render(request, "dashboard/home.html", {
        "n_products": Product.objects.count(),
        "n_orders": Order.objects.count(),
        "n_pending": Order.objects.filter(status="pending").count(),
        "n_verify": Order.objects.filter(payment_status=Order.PAY_VERIFY).count(),
        "revenue": Order.objects.exclude(status="cancelled").aggregate(t=Sum("total"))["t"] or 0,
        "recent": Order.objects.select_related("user")[:8],
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
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"“{saved.name}” saved.")
        return redirect("dashboard:products")
    return render(request, "dashboard/product_form.html", {"form": form, "product": product})


@staff
@require_POST
def product_delete(request, pk):
    p = get_object_or_404(Product, pk=pk)
    p.delete()
    messages.success(request, f"“{p.name}” deleted.")
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
    qs = Order.objects.select_related("user")
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
        order.save()
        messages.success(request, f"Order #{order.pk} updated.")
        return redirect("dashboard:order_detail", pk=pk)
    return render(request, "dashboard/order_detail.html", {
        "order": order, "statuses": Order.STATUSES, "pay_statuses": Order.PAYMENT_STATUSES,
    })


# ------------------------------------------------------------ settings
@staff
def settings_view(request):
    form = SettingsForm(request.POST or None, instance=SiteSettings.get())
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Settings saved. New delivery charges apply to the next orders.")
        return redirect("dashboard:settings")
    return render(request, "dashboard/settings.html", {"form": form})
