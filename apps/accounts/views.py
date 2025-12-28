from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import PhoneAuthenticationForm, PhoneUserCreationForm
from apps.orders.services.telegram import send_order_canceled, send_order_delivered


def register(request):
    if request.user.is_authenticated:
        return redirect("profile")
    if request.method == "POST":
        form = PhoneUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect("profile")
    else:
        form = PhoneUserCreationForm()
    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("profile")
    if request.method == "POST":
        form = PhoneAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            next_url = request.POST.get("next") or request.GET.get("next")
            return redirect(next_url or "profile")
    else:
        form = PhoneAuthenticationForm()
    return render(request, "login.html", {"form": form})


def logout_view(request):
    auth_logout(request)
    return redirect("home")


@login_required
def profile(request):
    phone = (request.user.username or "").strip()
    orders = []
    if phone:
        from apps.orders.models import Order

        orders = list(
            Order.objects.filter(phone=phone)
            .order_by("-created_at")
            .only("id", "created_at", "status", "total_price", "delivery_fee", "address")
        )
    return render(request, "profile.html", {"orders": orders})


@login_required
@require_POST
def order_cancel(request, order_id):
    phone = (request.user.username or "").strip()
    if not phone:
        return redirect("profile")
    from apps.orders.models import Order

    order = Order.objects.filter(id=order_id, phone=phone).first()
    if not order:
        return redirect("profile")
    send_order_canceled(order.id)
    order.delete()
    request.user.is_active = False
    request.user.save(update_fields=["is_active"])
    auth_logout(request)
    return redirect("profile")


@login_required
@require_POST
def order_accept(request, order_id):
    phone = (request.user.username or "").strip()
    if not phone:
        return redirect("profile")
    from apps.orders.models import Order

    order = Order.objects.filter(id=order_id, phone=phone).first()
    if not order:
        return redirect("profile")
    send_order_delivered(order.id)
    order.delete()
    return redirect("profile")
