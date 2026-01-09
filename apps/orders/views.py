from decimal import Decimal
import json

from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.dateparse import parse_time
from django.db import transaction

from apps.catalog.models import Book
from .cart import Cart
from .forms import CheckoutForm
from .models import DeliveryNotice, DeliverySettings, Order, OrderItem
from .services.delivery import recalculate_delivery


@login_required
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
    return redirect(request.META.get("HTTP_REFERER", "home"))



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


@login_required
def checkout(request):
    cart = Cart(request)
    cart_items = list(cart.items())
    if not cart_items:
        return redirect("cart_detail")

    def _in_order_window(cfg, now_time):
        if not cfg.order_start_time or not cfg.order_end_time:
            return True
        start = cfg.order_start_time
        end = cfg.order_end_time
        if start <= end:
            return start <= now_time <= end
        return now_time >= start or now_time <= end

    cfg = DeliverySettings.get_active()
    can_order = _in_order_window(cfg, timezone.localtime().time())

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if not can_order:
            form.add_error(None, "Barcha kuryerlar band")
        elif form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.total_price = cart.total_price()
                order.subtotal_before_discount = order.total_price
                order.discount_percent = order.discount_percent or 0
                order.discount_amount = order.discount_amount or 0
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
        user = request.user
        form = CheckoutForm(
            initial={
                "full_name": user.first_name or "",
                "phone": user.username or "",
            }
        )

    delivery_notices = DeliveryNotice.objects.filter(is_active=True).order_by("-updated_at")[:5]

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
            "can_order": can_order,
        },
    )


def order_confirmation(request):
    order_id = request.session.get("last_order_id")
    order = Order.objects.filter(id=order_id).first()
    return render(request, "order_confirmation.html", {"order": order})


def _cart_json_payload(request, cart):
    items = []
    for item in cart.items():
        book = item["book"]
        cover = book.cover_image.url if book.cover_image else ""
        if cover:
            cover = request.build_absolute_uri(cover)
        items.append(
            {
                "book_id": book.id,
                "title": book.title,
                "cover": cover,
                "price": str(item["price"]),
                "quantity": item["quantity"],
                "line_total": str(item["line_total"]),
            }
        )
    return {
        "items": items,
        "total_price": str(cart.total_price()),
        "count": len(cart),
    }


def _read_json(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return None


@ensure_csrf_cookie
def api_cart(request):
    cart = Cart(request)
    return JsonResponse(_cart_json_payload(request, cart))


@require_POST
def api_cart_add(request):
    payload = _read_json(request)
    if payload is None:
        return JsonResponse({"error": "invalid_json"}, status=400)
    try:
        book_id = int(payload.get("book_id"))
        quantity = int(payload.get("quantity", 1))
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid_payload"}, status=400)
    if book_id <= 0 or quantity <= 0:
        return JsonResponse({"error": "invalid_payload"}, status=400)
    cart = Cart(request)
    cart.add(book_id, quantity)
    return JsonResponse(_cart_json_payload(request, cart))


@require_POST
def api_cart_update(request):
    payload = _read_json(request)
    if payload is None:
        return JsonResponse({"error": "invalid_json"}, status=400)
    try:
        book_id = int(payload.get("book_id"))
        quantity = int(payload.get("quantity", 1))
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid_payload"}, status=400)
    if book_id <= 0:
        return JsonResponse({"error": "invalid_payload"}, status=400)
    cart = Cart(request)
    cart.update(book_id, quantity)
    return JsonResponse(_cart_json_payload(request, cart))


@require_POST
def api_cart_remove(request):
    payload = _read_json(request)
    if payload is None:
        return JsonResponse({"error": "invalid_json"}, status=400)
    try:
        book_id = int(payload.get("book_id"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid_payload"}, status=400)
    if book_id <= 0:
        return JsonResponse({"error": "invalid_payload"}, status=400)
    cart = Cart(request)
    cart.remove(book_id)
    return JsonResponse(_cart_json_payload(request, cart))


@require_POST
def api_cart_clear(request):
    cart = Cart(request)
    cart.clear()
    return JsonResponse(_cart_json_payload(request, cart))


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


@csrf_exempt
@require_POST
def api_create_order(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        return JsonResponse({"error": "items_required"}, status=400)

    full_name = (payload.get("full_name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    address = (payload.get("address") or "").strip()
    if not full_name or not phone or not address:
        return JsonResponse({"error": "missing_required_fields"}, status=400)

    payment_type = payload.get("payment_type") or "cash"
    valid_payments = {choice[0] for choice in Order.PAYMENT_CHOICES}
    if payment_type not in valid_payments:
        return JsonResponse({"error": "invalid_payment_type"}, status=400)

    order = Order(
        full_name=full_name,
        phone=phone,
        extra_phone=(payload.get("extra_phone") or "").strip(),
        location=(payload.get("location") or "").strip(),
        address_text=(payload.get("address_text") or "").strip(),
        address=address,
        note=(payload.get("note") or "").strip(),
        payment_type=payment_type,
        status="new",
        order_source=(payload.get("order_source") or "app").strip() or "app",
        delivery_time_choice=payload.get("delivery_time_choice") or "now",
    )

    if "latitude" in payload:
        try:
            order.latitude = Decimal(str(payload.get("latitude")))
        except (TypeError, ValueError):
            return JsonResponse({"error": "invalid_latitude"}, status=400)
    if "longitude" in payload:
        try:
            order.longitude = Decimal(str(payload.get("longitude")))
        except (TypeError, ValueError):
            return JsonResponse({"error": "invalid_longitude"}, status=400)

    if order.delivery_time_choice == "schedule":
        delivery_time = parse_time(payload.get("delivery_time") or "")
        if delivery_time:
            order.delivery_time = delivery_time

    item_payloads = []
    book_ids = []
    for item in items:
        if not isinstance(item, dict):
            return JsonResponse({"error": "invalid_item"}, status=400)
        try:
            book_id = int(item.get("book_id"))
            quantity = int(item.get("quantity", 1))
        except (TypeError, ValueError):
            return JsonResponse({"error": "invalid_item"}, status=400)
        if book_id <= 0 or quantity <= 0:
            return JsonResponse({"error": "invalid_item"}, status=400)
        book_ids.append(book_id)
        item_payloads.append({"book_id": book_id, "quantity": quantity})

    books = Book.objects.in_bulk(book_ids)
    missing = [book_id for book_id in book_ids if book_id not in books]
    if missing:
        return JsonResponse({"error": "book_not_found", "missing": missing}, status=404)

    total = Decimal("0")
    for item in item_payloads:
        book = books[item["book_id"]]
        total += book.sale_price * item["quantity"]

    discount_percent = payload.get("discount_percent")
    discount_amount = payload.get("discount_amount")
    discount_percent_value = 0
    discount_amount_value = Decimal("0")
    if discount_percent is not None:
        try:
            discount_percent_value = int(discount_percent)
        except (TypeError, ValueError):
            return JsonResponse({"error": "invalid_discount_percent"}, status=400)
        if discount_percent_value < 0 or discount_percent_value > 100:
            return JsonResponse({"error": "invalid_discount_percent"}, status=400)
        discount_amount_value = (total * Decimal(discount_percent_value)) / Decimal("100")
    elif discount_amount is not None:
        try:
            discount_amount_value = Decimal(str(discount_amount))
        except (TypeError, ValueError):
            return JsonResponse({"error": "invalid_discount_amount"}, status=400)
        if discount_amount_value < 0:
            return JsonResponse({"error": "invalid_discount_amount"}, status=400)

    order.subtotal_before_discount = total
    order.discount_percent = discount_percent_value
    order.discount_amount = discount_amount_value
    order.total_price = max(Decimal("0"), total - discount_amount_value)

    with transaction.atomic():
        order = recalculate_delivery(order, save=False)
        order.save()
        for item in item_payloads:
            book = books[item["book_id"]]
            OrderItem.objects.create(
                order=order,
                book=book,
                quantity=item["quantity"],
                price=book.sale_price,
            )

    data = {
        "id": order.id,
        "status": order.status,
        "total_price": str(order.total_price),
        "subtotal_before_discount": str(order.subtotal_before_discount),
        "discount_percent": order.discount_percent,
        "discount_amount": str(order.discount_amount),
        "delivery_fee": order.delivery_fee,
        "delivery_distance_km": str(order.delivery_distance_km or 0),
    }
    return JsonResponse(data, status=201)
