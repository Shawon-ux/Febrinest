from django.urls import path

from . import dashboard as v

app_name = "dashboard"
urlpatterns = [
    path("", v.home, name="home"),
    path("products/", v.products, name="products"),
    path("products/new/", v.product_form, name="product_new"),
    path("products/<int:pk>/edit/", v.product_form, name="product_edit"),
    path("products/<int:pk>/delete/", v.product_delete, name="product_delete"),
    path("sizes/<int:pk>/toggle/", v.size_toggle, name="size_toggle"),
    path("sections/", v.categories, name="categories"),
    path("sections/new/", v.category_form, name="category_new"),
    path("sections/<int:pk>/edit/", v.category_form, name="category_edit"),
    path("sections/<int:pk>/delete/", v.category_delete, name="category_delete"),
    path("orders/", v.orders, name="orders"),
    path("orders/<int:pk>/", v.order_detail, name="order_detail"),
    path("orders/<int:pk>/delete/", v.order_delete, name="order_delete"),
    path("admins/", v.admins, name="admins"),
    path("admins/<int:pk>/delete/", v.admin_delete, name="admin_delete"),
    path("orders/<int:pk>/payment-failed/", v.order_payment_failed, name="order_payment_failed"),
    path("announce/", v.announce, name="announce"),
    path("reviews/", v.reviews, name="reviews"),
    path("settings/", v.settings_view, name="settings"),
]
