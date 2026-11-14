import io
import random

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from store.models import Category, Product, SiteSettings

ADMIN = dict(phone="01700000000", email="admin@febricon.com", full_name="Febricon Admin")
ADMIN_PASSWORD = "Febricon@2026"

TOP = ["S", "M", "L", "XL", "XXL"]
PANT = ["28", "30", "32", "34", "36"]
DATA = {
    "Shirt": (TOP, [("Classic Oxford Shirt", 1450, 1800, "#2f4b7c"), ("Slim Fit Check Shirt", 1250, None, "#7c4b2f"),
                    ("Formal White Shirt", 1350, 1600, "#d9d9d9")]),
    "Pant": (PANT, [("Slim Chino Pant", 1650, 1900, "#8c7b5a"), ("Black Formal Trouser", 1750, None, "#222222"),
                    ("Stretch Denim Jeans", 1950, 2300, "#34527a")]),
    "T-Shirt": (TOP, [("Basic Cotton Tee", 550, 700, "#c0392b"), ("Graphic Street Tee", 750, None, "#1e1e1e"),
                      ("Oversized Drop-Shoulder Tee", 850, 999, "#6b8e6b")]),
    "Polo Shirt": (TOP, [("Pique Polo – Navy", 950, 1200, "#1f2d5a"), ("Contrast Collar Polo", 1050, None, "#a83240")]),
    "Panjabi": (TOP, [("Festive Cotton Panjabi", 2200, 2600, "#e8dcc2"), ("Embroidered Eid Panjabi", 3200, 3800, "#14532d"),
                      ("Everyday Linen Panjabi", 1850, None, "#5b6b8c")]),
    "Hoodie": (TOP, [("Fleece Pullover Hoodie", 1650, 1950, "#444b55")]),
    "Jacket": (TOP, [("Windbreaker Jacket", 2400, 2900, "#2e5339")]),
}


def make_image(label, color):
    img = Image.new("RGB", (600, 800), color)
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 560, 760], outline="white", width=3)
    d.text((70, 700), label, fill="white")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = "Create the admin account, sections and dummy products."

    def handle(self, *a, **o):
        User = get_user_model()
        u, created = User.objects.get_or_create(phone=ADMIN["phone"], defaults=dict(
            username=ADMIN["phone"], email=ADMIN["email"], full_name=ADMIN["full_name"]))
        u.is_staff = u.is_superuser = True
        u.set_password(ADMIN_PASSWORD)
        u.save()

        s = SiteSettings.get()
        s.bkash_number = s.bkash_number or "01700000000"
        s.nagad_number = s.nagad_number or "01700000000"
        s.contact_phone = s.contact_phone or "01700000000"
        s.save()

        random.seed(7)
        for pos, (cat_name, (sizes, items)) in enumerate(DATA.items()):
            cat, _ = Category.objects.get_or_create(name=cat_name, defaults={"position": pos})
            for name, price, old, color in items:
                if Product.objects.filter(name=name).exists():
                    continue
                p = Product.objects.create(
                    category=cat, name=name, price=price, old_price=old,
                    description=f"{name} from Febricon. Soft, durable fabric with a clean modern fit. Demo product.")
                p.image.save(f"{name.lower().replace(' ', '-')}.jpg", make_image(name, color), save=True)
                blocked = random.choice(sizes[:-1])  # one size stocked out so the lock is visible
                for sz in sizes:
                    p.sizes.create(size=sz, available=(sz != blocked))
        self.stdout.write(self.style.SUCCESS("Seeded."))
