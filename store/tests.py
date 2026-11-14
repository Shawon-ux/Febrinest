from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import CartItem, Category, Order, Product, SiteSettings

User = get_user_model()


class ShopFlow(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="a", full_name="Boss", email="boss@gmail.com", phone="01711111111",
            password="secret123", is_staff=True)
        self.cat = Category.objects.create(name="Pants")

    def test_register_and_login_by_phone_or_email(self):
        r = self.client.post(reverse("accounts:register"), {
            "full_name": "Rahim", "email": "Rahim@gmail.com", "phone": "+8801812345678",
            "password": "pass1234", "confirm_password": "pass1234"})
        self.assertEqual(r.status_code, 302)
        self.client.logout()
        for ident in ("01812345678", "rahim@gmail.com"):
            r = self.client.post(reverse("accounts:login"), {"identifier": ident, "password": "pass1234"})
            self.assertEqual(r.status_code, 302, ident)
            self.client.logout()
        r = self.client.post(reverse("accounts:login"), {"identifier": "01812345678", "password": "bad"})
        self.assertEqual(r.status_code, 200)

    def test_register_requires_phone(self):
        r = self.client.post(reverse("accounts:register"), {
            "full_name": "X", "email": "x@gmail.com", "phone": "",
            "password": "pass1234", "confirm_password": "pass1234"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(email="x@gmail.com").exists())

    def test_customer_cannot_open_dashboard(self):
        u = User.objects.create_user(username="c", full_name="C", email="c@gmail.com", phone="01922222222", password="x123456")
        self.client.force_login(u)
        self.assertEqual(self.client.get(reverse("dashboard:products")).status_code, 302)

    def test_admin_product_size_lock_cart_checkout(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("dashboard:product_new"), {
            "category": self.cat.pk, "name": "Chino", "description": "d", "price": "300",
            "is_active": "on", "size_L": "blocked", "size_XL": "available"})
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["form"].errors)
        p = Product.objects.get()
        # price edit next day
        self.client.post(reverse("dashboard:product_edit", args=[p.pk]), {
            "category": self.cat.pk, "name": "Chino", "price": "350", "is_active": "on",
            "size_L": "blocked", "size_XL": "available"})
        p.refresh_from_db()
        self.assertEqual(p.price, 350)
        self.client.logout()

        cust = User.objects.create_user(username="c", full_name="Cust", email="c@gmail.com", phone="01922222222", password="x123456")
        self.client.force_login(cust)
        page = self.client.get(p.get_absolute_url()).content.decode()
        self.assertIn("Not available", page)
        # blocked size rejected
        self.client.post(reverse("store:cart_add", args=[p.pk]), {"size": "L", "quantity": 1})
        self.assertEqual(CartItem.objects.count(), 0)
        self.client.post(reverse("store:cart_add", args=[p.pk]), {"size": "XL", "quantity": 2})
        self.assertEqual(CartItem.objects.get().quantity, 2)

        # admin blocks XL after it's in cart -> checkout refused
        p.sizes.filter(size="XL").update(available=False)
        self.assertEqual(self.client.get(reverse("store:checkout")).status_code, 302)
        p.sizes.filter(size="XL").update(available=True)

        data = {"full_name": "Cust", "phone": "01922222222", "address": "Road 1", "area": "outside",
                "payment_method": "bkash", "transaction_id": ""}
        self.assertEqual(self.client.post(reverse("store:checkout"), data).status_code, 200)  # needs TrxID
        data["transaction_id"] = "01922222222 / ABC123"
        self.assertEqual(self.client.post(reverse("store:checkout"), data).status_code, 302)
        o = Order.objects.get()
        self.assertEqual((o.subtotal, o.delivery_charge, o.total), (700, 120, 820))
        self.assertEqual(o.payment_status, Order.PAY_VERIFY)
        self.assertEqual(CartItem.objects.count(), 0)

        # admin raises delivery fee; COD inside Dhaka
        s = SiteSettings.get(); s.delivery_inside = 80; s.save()
        self.client.post(reverse("store:cart_add", args=[p.pk]), {"size": "XL", "quantity": 1})
        data.update(area="inside", payment_method="cod")
        self.client.post(reverse("store:checkout"), data)
        o2 = Order.objects.first()
        self.assertEqual((o2.delivery_charge, o2.total), (80, 430))

    def test_filters(self):
        p = Product.objects.create(category=self.cat, name="Jeans", price=900)
        p.sizes.create(size="32", available=True)
        q = Product.objects.create(category=self.cat, name="Cargo", price=500)
        q.sizes.create(size="32", available=False)
        r = self.client.get(reverse("store:shop"), {"size": "32", "max": "1000"})
        self.assertEqual([x.name for x in r.context["products"]], ["Jeans"])


class ReviewFlow(TestCase):
    def test_review_and_admin_delete(self):
        cat = Category.objects.create(name="Jacket")
        p = Product.objects.create(category=cat, name="J", price=100)
        p.sizes.create(size="M")
        cust = User.objects.create_user(username="c", full_name="Cust", email="c@g.com", phone="01922222222", password="x123456")
        admin = User.objects.create_user(username="a", full_name="A", email="a@g.com", phone="01711111111", password="x123456", is_staff=True)
        self.client.force_login(cust)
        self.client.post(reverse("store:review_add", args=[p.pk]), {"rating": 4, "comment": "Nice"})
        self.client.post(reverse("store:review_add", args=[p.pk]), {"rating": 5, "comment": "Great"})  # edits, no duplicate
        self.assertEqual(p.reviews.count(), 1)
        r = p.reviews.get()
        self.assertEqual(self.client.post(reverse("store:review_delete", args=[r.pk])).status_code, 302)
        self.assertEqual(p.reviews.count(), 1)  # customer cannot delete
        self.assertIn("Great", self.client.get(p.get_absolute_url()).content.decode())
        self.client.force_login(admin)
        page = self.client.get(reverse("store:category", args=[cat.slug])).content.decode()
        self.assertIn("Add new Jacket", page)
        self.assertIn(f"category={cat.pk}", page)
        self.client.post(reverse("store:review_delete", args=[r.pk]))
        self.assertEqual(p.reviews.count(), 0)
        self.assertEqual(self.client.get(reverse("dashboard:product_new") + f"?category={cat.pk}").context["form"]["category"].value(), cat.pk)
        self.assertEqual(self.client.get(reverse("dashboard:reviews")).status_code, 200)


class AdminOrders(TestCase):
    def test_admin_orders_sms_delete_and_no_shopping(self):
        cat = Category.objects.create(name="Shirt")
        p = Product.objects.create(category=cat, name="S", price=100); p.sizes.create(size="M")
        cust = User.objects.create_user(username="c", full_name="Cust", email="c@g.com", phone="01922222222", password="x123456")
        admin = User.objects.create_user(username="a", full_name="A", email="a@g.com", phone="01711111111", password="x123456", is_staff=True)
        o = Order.objects.create(user=cust, full_name="Cust", phone="01922222222", address="x", area="inside",
                                 subtotal=100, delivery_charge=60, total=160, payment_method="bkash")
        self.client.force_login(admin)
        html = self.client.get(reverse("dashboard:orders")).content.decode()
        self.assertIn("tel:01922222222", html); self.assertIn("sms:01922222222?body=", html)
        self.assertIn("Payment not received", html)
        home = self.client.get("/").content.decode()
        self.assertIn(">Orders", home); self.assertNotIn('class="cart"', home)
        self.assertEqual(self.client.post(reverse("store:cart_add", args=[p.pk]), {"size": "M"}).status_code, 302)
        self.assertEqual(CartItem.objects.count(), 0)
        self.assertEqual(self.client.get(reverse("store:checkout")).status_code, 302)
        page = self.client.get(p.get_absolute_url()).content.decode()
        self.assertNotIn("Add to cart", page); self.assertIn("Edit product", page)
        self.client.force_login(cust)
        self.assertEqual(self.client.post(reverse("dashboard:order_delete", args=[o.pk])).status_code, 302)
        self.assertTrue(Order.objects.filter(pk=o.pk).exists())  # customers can't delete
        self.client.force_login(admin)
        self.client.post(reverse("dashboard:order_delete", args=[o.pk]))
        self.assertFalse(Order.objects.filter(pk=o.pk).exists())


class AdminManagement(TestCase):
    def setUp(self):
        self.main = User.objects.create_user(username="m", full_name="Main", email="main@g.com", phone="01700000000",
                                             password="x123456", is_staff=True, is_superuser=True)

    def test_main_admin_protected_and_new_admin_login(self):
        self.assertTrue(User.objects.get(pk=self.main.pk).is_main_admin)
        self.client.force_login(self.main)
        r = self.client.post(reverse("dashboard:admins"), {"full_name": "Sub", "email": "sub@gmail.com",
            "phone": "01855555555", "password": "pass1234", "confirm_password": "pass1234"})
        self.assertEqual(r.status_code, 302)
        sub = User.objects.get(email="sub@gmail.com"); self.assertTrue(sub.is_staff); self.assertFalse(sub.is_main_admin)
        self.client.logout()
        for ident in ("01855555555", "sub@gmail.com"):
            r = self.client.post(reverse("accounts:login"), {"identifier": ident, "password": "pass1234"})
            self.assertEqual(r.url, reverse("dashboard:home"), ident); self.client.logout()
        # sub-admin cannot remove main admin
        self.client.force_login(sub)
        self.client.post(reverse("dashboard:admin_delete", args=[self.main.pk]))
        self.assertTrue(User.objects.filter(pk=self.main.pk).exists())
        # main admin cannot be removed even by itself; can remove others
        self.client.force_login(self.main)
        self.client.post(reverse("dashboard:admin_delete", args=[self.main.pk]))
        self.assertTrue(User.objects.filter(pk=self.main.pk).exists())
        with self.assertRaises(Exception):
            self.main.delete()
        self.client.post(reverse("dashboard:admin_delete", args=[sub.pk]))
        self.assertFalse(User.objects.filter(pk=sub.pk).exists())

    def test_customer_cannot_manage_admins(self):
        c = User.objects.create_user(username="c", full_name="C", email="c@g.com", phone="01922222222", password="x123456")
        self.client.force_login(c)
        self.assertEqual(self.client.get(reverse("dashboard:admins")).status_code, 302)


class TrxVisible(TestCase):
    def test_trx_shown_and_mark_paid(self):
        cust = User.objects.create_user(username="c", full_name="C", email="c@g.com", phone="01922222222", password="x123456")
        admin = User.objects.create_user(username="a", full_name="A", email="a@g.com", phone="01711111111", password="x123456", is_staff=True)
        o = Order.objects.create(user=cust, full_name="C", phone="01922222222", address="x", area="inside", subtotal=100,
                                 delivery_charge=60, total=160, payment_method="bkash", payment_status="verifying", transaction_id="TRX9Z88")
        self.client.force_login(admin)
        self.assertIn("TRX9Z88", self.client.get(reverse("dashboard:orders")).content.decode())
        self.assertIn("TRX9Z88", self.client.get(reverse("dashboard:order_detail", args=[o.pk])).content.decode())
        r = self.client.post(reverse("dashboard:order_detail", args=[o.pk]), {"payment_status": "paid", "next": "/dashboard/orders/"})
        self.assertEqual(r.url, "/dashboard/orders/"); o.refresh_from_db(); self.assertEqual(o.payment_status, "paid")
