from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

# Every size the shop can offer. Admin picks which apply to each product.
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL", "28", "30", "32", "34", "36", "38", "40", "42", "Free"]


class SiteSettings(models.Model):
    """Single row, edited by the admin from the dashboard."""

    delivery_inside = models.DecimalField(
        "Delivery charge – inside Dhaka (৳)", max_digits=8, decimal_places=0, default=60
    )
    delivery_outside = models.DecimalField(
        "Delivery charge – outside Dhaka (৳)", max_digits=8, decimal_places=0, default=120
    )
    bkash_number = models.CharField("bKash number", max_length=20, blank=True)
    nagad_number = models.CharField("Nagad number", max_length=20, blank=True)
    rocket_number = models.CharField("Rocket number", max_length=20, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name_plural = "Site settings"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return "Febrinest settings"


class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "section"
            slug, n = base, 2
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:category", args=[self.slug])

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    price = models.DecimalField("Price (৳)", max_digits=9, decimal_places=0, validators=[MinValueValidator(1)])
    old_price = models.DecimalField(
        "Old price (৳) – optional, shown struck through", max_digits=9, decimal_places=0, null=True, blank=True
    )
    image = models.ImageField(upload_to="products/", blank=True)
    is_active = models.BooleanField("Visible in shop", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def get_absolute_url(self):
        return reverse("store:product", args=[self.pk])

    @property
    def available_sizes(self):
        return [s for s in self.sizes.all() if s.available]

    @property
    def in_stock(self):
        return any(s.available for s in self.sizes.all())

    @property
    def rating_stats(self):
        revs = list(self.reviews.all())
        if not revs:
            return None
        return {"avg": round(sum(r.rating for r in revs) / len(revs), 1), "n": len(revs)}

    @property
    def on_sale(self):
        return bool(self.old_price and self.old_price > self.price)

    def __str__(self):
        return self.name


class ProductSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sizes")
    size = models.CharField(max_length=10)
    # False = admin has locked this size (stock out). Customers see it but cannot add it.
    available = models.BooleanField(default=True)

    class Meta:
        unique_together = ("product", "size")
        ordering = ["id"]

    def __str__(self):
        return f"{self.product} – {self.size}"


class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=10)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product", "size")
        ordering = ["added_at"]

    @property
    def size_ok(self):
        return self.product.is_active and self.product.sizes.filter(size=self.size, available=True).exists()

    @property
    def line_total(self):
        return self.product.price * self.quantity


class Order(models.Model):
    AREA_INSIDE, AREA_OUTSIDE = "inside", "outside"
    AREAS = [(AREA_INSIDE, "Inside Dhaka"), (AREA_OUTSIDE, "Outside Dhaka")]

    PAY_COD, PAY_BKASH, PAY_NAGAD, PAY_ROCKET = "cod", "bkash", "nagad", "rocket"
    PAYMENT_METHODS = [
        (PAY_COD, "Cash on Delivery (offline)"),
        (PAY_BKASH, "bKash (online)"),
        (PAY_NAGAD, "Nagad (online)"),
        (PAY_ROCKET, "Rocket (online)"),
    ]

    PAY_UNPAID, PAY_VERIFY, PAY_PAID = "unpaid", "verifying", "paid"
    PAYMENT_STATUSES = [(PAY_UNPAID, "Unpaid"), (PAY_VERIFY, "Awaiting verification"), (PAY_PAID, "Paid")]

    STATUSES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=14)
    address = models.TextField()
    area = models.CharField(max_length=10, choices=AREAS)
    subtotal = models.DecimalField(max_digits=10, decimal_places=0)
    delivery_charge = models.DecimalField(max_digits=8, decimal_places=0)
    total = models.DecimalField(max_digits=10, decimal_places=0)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUSES, default=PAY_UNPAID)
    transaction_id = models.CharField("Payer number / TrxID", max_length=60, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_online(self):
        return self.payment_method != self.PAY_COD

    @property
    def sms_templates(self):
        """(label, message, sms: link) – opens the admin's phone/SMS app with the text filled in."""
        from urllib.parse import quote
        n, i, t = self.full_name, self.pk, self.total
        method = self.get_payment_method_display().split(" (")[0]
        msgs = [
            ("Order confirmed", f"Febrinest: Hi {n}, your order #{i} (Tk {t}) is confirmed. We will deliver it soon. Thank you!"),
            ("Payment not received", f"Febrinest: Hi {n}, we have not received the payment for order #{i} (Tk {t}). Please send it via {method} and reply with your TrxID."),
            ("Order shipped", f"Febrinest: Hi {n}, your order #{i} has been shipped and will reach you shortly."),
            ("Order cancelled", f"Febrinest: Hi {n}, your order #{i} has been cancelled. Call us if this is a mistake."),
        ]
        return [(label, msg, f"sms:{self.phone}?body={quote(msg)}") for label, msg in msgs]

    def __str__(self):
        return f"Order #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=140)  # snapshot, so later price/name edits don't rewrite history
    size = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=9, decimal_places=0)
    quantity = models.PositiveIntegerField()

    @property
    def line_total(self):
        return self.price * self.quantity


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("product", "user")  # one review per customer per product; resubmitting edits it

    def __str__(self):
        return f"{self.user} on {self.product} ({self.rating}★)"
