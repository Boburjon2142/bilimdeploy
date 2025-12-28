from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("orders/<int:order_id>/cancel/", views.order_cancel, name="order_cancel"),
    path("orders/<int:order_id>/accept/", views.order_accept, name="order_accept"),
]
