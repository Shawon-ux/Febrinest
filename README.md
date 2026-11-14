# Febrinest – Clothing Store (Python / Django)

An online clothing shop with a customer storefront and an admin panel.
Built with Django 5.2, SQLite locally (PostgreSQL in production), WhiteNoise for static files.

---

## 1. Features

### Customers
- **Register** with name, Gmail, phone number, password. **Login** with phone *or* Gmail + password.
- Home page with hero, sections (Shirt, Pant, T-Shirt, Polo, Panjabi, Hoodie, Jacket…), latest arrivals.
- Navbar links (All + sections) and Cart appear **only after login**.
- Filters: search, section, size, price range, sort, in-stock only.
- Product page shows every size; sizes the admin blocked show **"Not available"** and can't be added to the cart.
- Cart: change quantity, delete items, continue shopping, then review & pay.
- Payment: **Cash on Delivery** (offline) or **bKash / Nagad / Rocket** (online – customer sends money, enters TrxID).
- Delivery charge: **৳60 inside Dhaka, ৳120 outside** (admin can change). A notice before ordering explains that delivery must be paid and the 1-hour cancel rule.
- **Cancel an order within 1 hour** of placing it (live countdown; locks automatically afterwards, enforced on the server too).
- Reviews (1–5 stars + comment), one per product per customer.
- 🔔 Notifications: new products, price drops, discounts/announcements, order & payment updates.

### Admin (`/dashboard/`)
- **Sections:** add / rename / delete (they appear in the navbar automatically).
- **Products:** create, edit price (with optional "old price" shown struck through), image, description, hide/show, delete.
  - Each section page has **"+ Add new <Section>"** (section pre-selected).
  - Per size: *Available / Blocked (stock out) / Not offered*; one-click lock/unlock from the product list.
- **Orders** (top navbar): customer, phone, items, total, payment method, **TrxID**, status.
  - ✓ *Payment received* / ✗ *Payment not received* (auto-SMS + notification to the customer).
  - 📞 Call and ✉ SMS templates (confirmed, payment not received, shipped, cancelled); delete fake orders.
- **Reviews:** delete any customer review.
- **Announcements:** send discounts/offers to all customers' notification bell.
- **Admins:** add new admins (name, Gmail, phone, password) or remove them. The **main admin can never be removed**.
- **Delivery & payment:** delivery fees, bKash/Nagad/Rocket numbers, contact phone.
- Admin accounts can't shop (no cart/checkout).
- `/django-admin/` is the built-in Django admin (main admin only).

---

## 2. Run locally (Windows)

```powershell
cd E:\Febricon
venv\Scripts\activate
pip install -r requirements.txt        # only needed on a fresh machine
python manage.py migrate
python manage.py seed_demo             # creates main admin, sections and 16 demo products
python manage.py runserver
```

Open **http://127.0.0.1:8000/**

### Default main admin (created by `seed_demo`)
| | |
|---|---|
| Login | phone `01700000000` **or** email `admin@febricon.com` |
| Password | `Febricon@2026` |

**Change this password before going live** (`/django-admin/` → Users, or `python manage.py changepassword <username>`).
To create your own main admin instead: `python manage.py createsuperuser` (the first superuser becomes the protected main admin).

Re-running `seed_demo` is safe (no duplicate products) but **resets that admin's password** to the value above.

### Tests
```powershell
python manage.py test
```

---

## 3. Project layout

```
febricon/            settings, urls, wsgi (internal project package)
accounts/            custom User (phone + email login), registration, login backend
store/
  models.py          Category, Product, ProductSize, CartItem, Order, Review, Notification, SiteSettings
  views.py           storefront: home, shop, product, cart, checkout, orders, reviews, notifications
  dashboard.py       admin panel views (products, orders, admins, announcements …)
  notify.py          create notifications
  sms.py             automatic SMS sender
  filters.py         shared product filtering
  management/commands/seed_demo.py
templates/           base, store/, dashboard/, accounts/
static/              css/febrinest styles, img/ (stock photos)
requirements.txt  Procfile  build.sh
```

---

## 4. Automatic SMS (optional but recommended)

SMS is sent when the admin clicks **✗ Payment not received**:
*"Febrinest: Hi {name}, we did not receive your payment for order #{id} (Tk {total}). You may have given a wrong Transaction ID. We will call you soon for verification."*

Django can't send SMS by itself – you need an SMS provider account. Set one environment variable
with your provider's HTTP send URL:

```
SMS_URL="https://PROVIDER/api?api_key=KEY&senderid=Febrinest&number={to}&message={message}"
```
Placeholders: `{to}` = `8801XXXXXXXXX`, `{to_local}` = `01XXXXXXXXX`, `{message}` = URL-encoded text.

Without `SMS_URL`, nothing is sent: the customer still gets the in-site 🔔 notification and the admin sees a
warning (use the ✉ SMS menu or call). The ✉ SMS menu buttons open your **phone's** messaging app with the text ready.

---

## 5. Online payments

bKash / Nagad / Rocket are **manual**: the customer sends money to the number you set under
*Delivery & payment*, then enters their number/TrxID at checkout. The order shows
**Awaiting verification** with the TrxID – check it in your wallet app, then click
**✓ Payment received** (or **✗ Payment not received**).
Automatic gateways (bKash merchant API, SSLCommerz) need a merchant account and keys – not included.

---

## 6. Deploy (Render / Railway / Heroku)

1. Push the project to GitHub (`venv/`, `db.sqlite3`, `media/` are git-ignored).
2. Create a web service + a **PostgreSQL** database.
3. Environment variables:

| Variable | Value |
|---|---|
| `DEBUG` | `0` |
| `SECRET_KEY` | long random string |
| `ALLOWED_HOSTS` | `yourdomain.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://yourdomain.com` |
| `DATABASE_URL` | your Postgres URL |
| `MEDIA_ROOT` | path of a persistent disk (for uploaded product images) |
| `SMS_URL` | optional, see section 4 |

4. Build command: `./build.sh`  Start command: `gunicorn febricon.wsgi`
5. Run once on the server: `python manage.py createsuperuser` (becomes the main admin).
   Don't run `seed_demo` in production unless you want the demo products and default admin password.

> Free hosts wipe the disk on redeploy → uploaded product images disappear unless you attach a
> persistent disk or move images to Cloudinary/S3. The demo/stock photos in `static/img` are Unsplash
> images; replace them with your own product photos.

---

## 7. Notes & rules
- Cancel window: 1 hour (`Order.CANCEL_WINDOW` in `store/models.py`). Shipped/delivered orders can't be cancelled.
- Order prices are snapshotted: later price edits don't change past orders.
- If the admin blocks a size after a customer added it to the cart, checkout is blocked until that item is removed.
- Delivery fees and payment numbers live in the database (edit them in the admin panel, not in code).
