from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("library/add/", views.library_add, name="library_add"),
    path("library/list/", views.library_list, name="library_list"),
    path("library/<int:item_id>/delete/", views.library_delete, name="library_delete"),
    path("library/<int:item_id>/status/", views.library_status, name="library_status"),
    path("orders/<int:order_id>/cancel/", views.order_cancel, name="order_cancel"),
    path("orders/<int:order_id>/accept/", views.order_accept, name="order_accept"),
]
