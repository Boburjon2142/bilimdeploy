from decimal import Decimal

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.db import transaction

from apps.catalog.models import Book
from .cart import Cart
from .forms import CheckoutForm
from .models import DeliveryNotice, DeliverySettings, Order, OrderItem
from .services.delivery import recalculate_delivery


def cart_detail(request):
    cart = Cart(request)
    return render(request, "cart.html", {"cart_items": list(cart.items()), "cart_total": cart.total_price()})


@require_POST
def add_to_cart(request, book_id):
    cart = Cart(request)
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1
    cart.add(book_id, quantity)
    return redirect("home")



@require_POST
def remove_from_cart(request, book_id):
    cart = Cart(request)
    cart.remove(book_id)
    return redirect("cart_detail")


@require_POST
def update_cart(request, book_id):
    cart = Cart(request)
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1
    cart.update(book_id, quantity)
    return redirect("cart_detail")


def checkout(request):
    cart = Cart(request)
    cart_items = list(cart.items())
    if not cart_items:
        return redirect("cart_detail")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.total_price = cart.total_price()
                order = recalculate_delivery(order, save=False)
                order.save()
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        book=item["book"],
                        quantity=item["quantity"],
                        price=item["price"],
                    )
                cart.clear()
                request.session["last_order_id"] = order.id
            return redirect(reverse("order_confirmation"))
    else:
        form = CheckoutForm()

    delivery_notices = DeliveryNotice.objects.filter(is_active=True).order_by("-updated_at")[:5]
    cfg = DeliverySettings.get_active()

    def _valid_coord(val: float, kind: str) -> bool:
        if val is None:
            return False
        try:
            v = float(val)
        except (TypeError, ValueError):
            return False
        if kind == "lat":
            return -90 <= v <= 90
        return -180 <= v <= 180

    origin_lat = float(settings.SHOP_LAT)
    origin_lng = float(settings.SHOP_LNG)
    if _valid_coord(cfg.shop_lat, "lat") and _valid_coord(cfg.shop_lng, "lng"):
        origin_lat = float(cfg.shop_lat)
        origin_lng = float(cfg.shop_lng)

    return render(
        request,
        "checkout.html",
        {
            "form": form,
            "cart_items": cart_items,
            "cart_total": cart.total_price(),
            "delivery_notices": delivery_notices,
            "origin_lat": origin_lat,
            "origin_lng": origin_lng,
        },
    )


def order_confirmation(request):
    order_id = request.session.get("last_order_id")
    order = Order.objects.filter(id=order_id).first()
    return render(request, "order_confirmation.html", {"order": order})


@require_POST
def delivery_quote(request):
    """
    Lightweight endpoint to preview delivery distance/fee when user selects a point on the map.
    Does not persist anything; uses the same pricing logic as checkout.
    """
    try:
        lat = float(request.POST.get("lat"))
        lng = float(request.POST.get("lng"))
        subtotal = Decimal(request.POST.get("subtotal", "0"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Noto‘g‘ri koordinata yoki summa"}, status=400)

    tmp_order = Order(latitude=lat, longitude=lng, total_price=subtotal)
    tmp_order = recalculate_delivery(tmp_order, save=False)

    data = {
        "distance_km": float(tmp_order.delivery_distance_km or 0),
        "fee": tmp_order.delivery_fee,
        "zone_status": tmp_order.delivery_zone_status,
        "zone_message": (tmp_order.delivery_pricing_snapshot or {}).get("zone_message"),
    }
    return JsonResponse(data)
