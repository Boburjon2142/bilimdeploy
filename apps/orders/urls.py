from django.urls import path
from . import views

urlpatterns = [
    path("savat/", views.cart_detail, name="cart_detail"),
    path("savat/qoshish/<int:book_id>/", views.add_to_cart, name="add_to_cart"),
    path("savat/ochirish/<int:book_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("savat/yangilash/<int:book_id>/", views.update_cart, name="update_cart"),
    path("buyurtma/", views.checkout, name="checkout"),
    path("buyurtma/tasdiq/", views.order_confirmation, name="order_confirmation"),
    path("api/orders/", views.api_create_order, name="api_create_order"),
    path("api/delivery-quote/", views.delivery_quote, name="delivery_quote"),
    path("api/cart/", views.api_cart, name="api_cart"),
    path("api/cart/add/", views.api_cart_add, name="api_cart_add"),
    path("api/cart/update/", views.api_cart_update, name="api_cart_update"),
    path("api/cart/remove/", views.api_cart_remove, name="api_cart_remove"),
    path("api/cart/clear/", views.api_cart_clear, name="api_cart_clear"),
]
