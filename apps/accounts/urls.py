from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("register/verify/", views.register_verify, name="register_verify"),
    path("api/register/", views.register_json, name="register_json"),
    path("api/register/verify/", views.register_verify_json, name="register_verify_json"),
    path("login/", views.login_view, name="login"),
    path("password/reset/", views.password_reset_request, name="password_reset_request"),
    path("password/reset/confirm/", views.password_reset_confirm, name="password_reset_confirm"),
    path("api/password/reset/", views.password_reset_request_json, name="password_reset_request_json"),
    path("api/password/reset/confirm/", views.password_reset_confirm_json, name="password_reset_confirm_json"),
    path("telegram/webhook/<str:token>/", views.telegram_webhook, name="telegram_webhook"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("library/add/", views.library_add, name="library_add"),
    path("library/list/", views.library_list, name="library_list"),
    path("library/<int:item_id>/delete/", views.library_delete, name="library_delete"),
    path("library/<int:item_id>/status/", views.library_status, name="library_status"),
    path("orders/<int:order_id>/cancel/", views.order_cancel, name="order_cancel"),
    path("orders/<int:order_id>/accept/", views.order_accept, name="order_accept"),
]
