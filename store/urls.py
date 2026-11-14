from django.urls import path

from . import views

app_name = "store"
urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("shop/<slug:slug>/", views.shop, name="category"),
    path("product/<int:pk>/", views.product_detail, name="product"),
    path("product/<int:pk>/review/", views.review_add, name="review_add"),
    path("review/<int:pk>/delete/", views.review_delete, name="review_delete"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/<int:pk>/", views.order_done, name="order_done"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/<int:pk>/go/", views.notification_go, name="notification_go"),
    path("my-orders/", views.my_orders, name="my_orders"),
]
