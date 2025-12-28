import json
import logging
import os
from html import escape as html_escape
from typing import List
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.utils import timezone

logger = logging.getLogger("django")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_chat_ids() -> List[str]:
    raw = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if not raw:
        return []
    # Allow multiple destinations: "-100123,...,12345"
    return [part.strip() for part in raw.split(",") if part.strip()]


def _send_telegram_message(text: str) -> None:
    """
    Sends plain-text message to Telegram via Bot API.
    No-op unless TELEGRAM_SEND_ORDERS=true and both token + chat id(s) are set.
    """
    if not _env_bool("TELEGRAM_SEND_ORDERS", default=False):
        return

    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_ids = _get_chat_ids()
    if not token or not chat_ids:
        logger.error(
            "Telegram is enabled but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing (token=%s, chat_ids=%s).",
            "set" if token else "missing",
            "set" if chat_ids else "missing",
        )
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Telegram hard limit is 4096 chars for a message; keep safe.
    text = (text or "").strip()
    if len(text) > 3900:
        text = text[:3900] + "\n...\n(uzun xabar qisqartirildi)"

    for chat_id in chat_ids:
        body = urlencode(
            {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            }
        ).encode("utf-8")
        req = Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urlopen(req, timeout=7) as resp:
                payload = resp.read().decode("utf-8", errors="replace")
            data = json.loads(payload) if payload else {}
            if not data.get("ok", False):
                logger.warning("Telegram sendMessage failed: %s", payload)
        except Exception:
            logger.exception("Telegram sendMessage error (chat_id=%s)", chat_id)


def send_message(text: str) -> None:
    """Public wrapper for sending a plain Telegram message (uses same env toggles)."""
    _send_telegram_message(text)


def _format_money_uzs(value) -> str:
    try:
        v = int(value)
    except Exception:
        return html_escape(str(value))
    return f"{v:,}".replace(",", " ") + " so'm"


def send_order_created(order_id: int) -> None:
    """
    Build and send order details to Telegram.
    Intended to be called inside transaction.on_commit().
    """
    from apps.orders.models import Order

    order = Order.objects.filter(id=order_id).prefetch_related("items__book").first()
    if not order:
        return

    def e(value) -> str:
        return html_escape("" if value is None else str(value), quote=True)

    def label(name: str, value: str) -> str:
        return f"<b>{e(name)}:</b> {value}"

    def _truncate(s: str, max_len: int) -> str:
        if len(s) <= max_len:
            return s
        return s[:max_len] + "…"

    lines: List[str] = []
    lines.append("<b>Yangi buyurtma</b>")
    lines.append(label("ID", f"#{order.id}"))
    if order.created_at:
        ts = timezone.localtime(order.created_at)
        lines.append(label("Vaqt", e(f"{ts:%Y-%m-%d %H:%M}")))
    lines.append("")

    lines.append(label("F.I.Sh", e(order.full_name)))
    lines.append(label("Telefon", e(order.phone)))
    if order.extra_phone:
        lines.append(label("Qo‘shimcha", e(order.extra_phone)))
    lines.append(label("Manzil", e(order.address)))
    if order.address_text:
        lines.append(label("Manzil (matn)", e(order.address_text)))
    if order.location:
        lines.append(label("Lokatsiya", e(order.location)))
    if order.maps_link:
        url = e(order.maps_link)
        lines.append(f"<b>Xarita:</b> <a href=\"{url}\">Google Maps</a>")
    lines.append("")

    lines.append("<b>Mahsulotlar:</b>")
    for item in order.items.all():
        title = getattr(item.book, "title", str(item.book))
        lines.append(f"- {e(title)} x{item.quantity} = {e(f'{item.line_total():.2f}')}")
    lines.append("")

    lines.append(label("To‘lov", e(order.get_payment_type_display())))
    lines.append(label("Jami", e(f"{order.total_price:.2f}")))
    lines.append(
        label(
            "Yetkazish",
            f"{_format_money_uzs(order.delivery_fee)} ({e(order.delivery_distance_km)} km)",
        )
    )
    lines.append(label("Zona", e(order.delivery_zone_status)))
    if order.note:
        lines.append("")
        lines.append("<b>Izoh:</b>")
        lines.append(_truncate(e(order.note), 900))

    _send_telegram_message("\n".join(lines))


def send_order_delivered(order_id: int) -> None:
    """
    Notify Telegram that an order has been delivered/accepted.
    """
    from apps.orders.models import Order

    order = Order.objects.filter(id=order_id).first()
    if not order:
        return

    def e(value) -> str:
        return html_escape("" if value is None else str(value), quote=True)

    lines: List[str] = []
    lines.append("<b>Buyurtma yetkazildi</b>")
    lines.append(f"<b>ID:</b> #{order.id}")
    lines.append(f"<b>F.I.Sh:</b> {e(order.full_name)}")
    lines.append(f"<b>Telefon:</b> {e(order.phone)}")
    lines.append(f"<b>Manzil:</b> {e(order.address)}")
    _send_telegram_message("\n".join(lines))


def send_order_canceled(order_id: int) -> None:
    """
    Notify Telegram that an order has been canceled.
    """
    from apps.orders.models import Order

    order = Order.objects.filter(id=order_id).first()
    if not order:
        return

    def e(value) -> str:
        return html_escape("" if value is None else str(value), quote=True)

    lines: List[str] = []
    lines.append("<b>Buyurtma bekor qilindi</b>")
    lines.append(f"<b>ID:</b> #{order.id}")
    lines.append(f"<b>F.I.Sh:</b> {e(order.full_name)}")
    lines.append(f"<b>Telefon:</b> {e(order.phone)}")
    lines.append(f"<b>Manzil:</b> {e(order.address)}")
    _send_telegram_message("\n".join(lines))
