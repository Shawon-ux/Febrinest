from django.urls import path

from . import views

app_name = "store"
urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("shop/<slug:slug>/", views.shop, name="category"),
    path("product/<int:pk>/", views.product_detail, name="product"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/<int:pk>/", views.order_done, name="order_done"),
    path("my-orders/", views.my_orders, name="my_orders"),
]
