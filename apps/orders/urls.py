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
]
