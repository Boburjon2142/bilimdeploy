import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Count, Q
import json

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .forms import (
    LibraryBookForm,
    PasswordResetConfirmForm,
    PasswordResetRequestForm,
    PhoneAuthenticationForm,
    PhoneUserCreationForm,
    TelegramOtpForm,
    normalize_phone,
)
from .models import LibraryBook, LibraryLimit, TelegramProfile
from apps.orders.services.telegram import (
    send_bot_message,
    send_order_canceled,
    send_order_delivered,
    send_otp,
)

User = get_user_model()

OTP_PURPOSE_REGISTER = "register"
OTP_PURPOSE_RESET = "password_reset"


def _otp_key(phone: str, purpose: str) -> str:
    return f"otp:{purpose}:{phone}"

def _pending_register_key(phone: str) -> str:
    return f"pending_register:{phone}"

def _pending_reset_key(phone: str) -> str:
    return f"pending_reset:{phone}"

def _get_linked_chat_id(phone: str) -> str:
    user = User.objects.filter(username=phone).only("id").first()
    if not user:
        cached = cache.get(_tg_link_key(phone))
        return cached or ""
    profile = TelegramProfile.objects.filter(user=user, is_verified=True).only("chat_id").first()
    return profile.chat_id if profile else ""

def _tg_link_key(phone: str) -> str:
    return f"tg_link:{phone}"

def _cache_chat_link(phone: str, chat_id: str) -> None:
    if not phone or not chat_id:
        return
    cache.set(_tg_link_key(phone), str(chat_id), timeout=settings.TELEGRAM_LINK_TTL_SECONDS)

def _cache_pending_register(phone: str) -> None:
    if not phone:
        return
    cache.set(_pending_register_key(phone), True, timeout=settings.TELEGRAM_LINK_TTL_SECONDS)

def _cache_pending_reset(phone: str) -> None:
    if not phone:
        return
    cache.set(_pending_reset_key(phone), True, timeout=settings.TELEGRAM_LINK_TTL_SECONDS)


def _send_otp_code(phone: str, chat_id: str, purpose: str) -> None:
    code = f"{secrets.randbelow(1_000_000):06d}"
    cache.set(
        _otp_key(phone, purpose),
        {"code": code, "attempts": 0, "chat_id": str(chat_id)},
        timeout=settings.OTP_TTL_SECONDS,
    )
    send_otp(str(chat_id), code, purpose, settings.OTP_TTL_SECONDS)


def _verify_otp(phone: str, purpose: str, code: str) -> tuple:
    payload = cache.get(_otp_key(phone, purpose))
    if not payload:
        return False, "Kodning muddati tugagan."
    attempts = int(payload.get("attempts", 0))
    if attempts >= settings.OTP_MAX_ATTEMPTS:
        cache.delete(_otp_key(phone, purpose))
        return False, "Urinishlar limitidan oshdi."
    if payload.get("code") != code:
        attempts += 1
        cache.set(
            _otp_key(phone, purpose),
            {**payload, "attempts": attempts},
            timeout=settings.OTP_TTL_SECONDS,
        )
        return False, "Kod noto'g'ri."
    cache.delete(_otp_key(phone, purpose))
    return True, ""


def _build_profile_context(request, form=None, library_q=None):
    phone = (request.user.username or "").strip()
    orders = []
    if phone:
        from apps.orders.models import Order

        orders = list(
            Order.objects.filter(phone=phone)
            .order_by("-created_at")
            .only("id", "created_at", "status", "total_price", "delivery_fee", "address")
        )

    base_qs = LibraryBook.objects.filter(user=request.user)
    counts = base_qs.aggregate(
        total=Count("id"),
        finished=Count("id", filter=Q(status=LibraryBook.STATUS_FINISHED)),
        reading=Count("id", filter=Q(status=LibraryBook.STATUS_READING)),
        unread=Count("id", filter=Q(status=LibraryBook.STATUS_UNREAD)),
    )

    if library_q is None:
        library_q = (request.GET.get("library_q") or "").strip()
    library_items = base_qs
    if library_q:
        library_items = library_items.filter(Q(title__icontains=library_q) | Q(author__icontains=library_q))

    return {
        "orders": orders,
        "library_items": library_items.order_by("-created_at"),
        "library_counts": counts,
        "library_form": form or LibraryBookForm(),
        "library_q": library_q,
    }


def _library_payload(user, library_q=None):
    base_qs = LibraryBook.objects.filter(user=user)
    counts = base_qs.aggregate(
        total=Count("id"),
        finished=Count("id", filter=Q(status=LibraryBook.STATUS_FINISHED)),
        reading=Count("id", filter=Q(status=LibraryBook.STATUS_READING)),
        unread=Count("id", filter=Q(status=LibraryBook.STATUS_UNREAD)),
    )

    items_qs = base_qs
    if library_q:
        items_qs = items_qs.filter(Q(title__icontains=library_q) | Q(author__icontains=library_q))
    items = list(items_qs.order_by("-created_at").values("id", "title", "author", "status"))
    return {"counts": counts, "items": items}


def _get_library_limit(user) -> int:
    limit_row = LibraryLimit.objects.filter(user=user).only("limit").first()
    if limit_row and limit_row.limit:
        return int(limit_row.limit)
    return 10


def register(request):
    if request.user.is_authenticated:
        return redirect("profile")
    if request.method == "POST":
        form = PhoneUserCreationForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data.get("phone")
            if settings.TELEGRAM_SEND_OTP:
                chat_id = _get_linked_chat_id(phone)
                request.session["pending_register"] = {
                    "full_name": form.cleaned_data.get("full_name", "").strip(),
                    "phone": phone,
                    "password": form.cleaned_data.get("password1"),
                    "chat_id": str(chat_id) if chat_id else "",
                }
                request.session["pending_register_needs_link"] = not bool(chat_id)
                if chat_id:
                    _send_otp_code(phone, chat_id, OTP_PURPOSE_REGISTER)
                else:
                    _cache_pending_register(phone)
                return redirect("register_verify")
            else:
                user = form.save()
                auth_login(request, user)
                return redirect("profile")
    else:
        form = PhoneUserCreationForm()
    return render(request, "register.html", {"form": form, "telegram_bot_username": settings.TELEGRAM_BOT_USERNAME})


def register_verify(request):
    pending = request.session.get("pending_register")
    if not pending:
        return redirect("register")
    form = TelegramOtpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ok, error = _verify_otp(pending["phone"], OTP_PURPOSE_REGISTER, form.cleaned_data["code"])
        if not ok:
            form.add_error("code", error)
        elif User.objects.filter(username=pending["phone"]).exists():
            form.add_error(None, "Bu telefon raqam bilan akkaunt mavjud.")
        else:
            chat_id = pending.get("chat_id")
            if chat_id and TelegramProfile.objects.filter(chat_id=str(chat_id)).exists():
                form.add_error(None, "Bu chat id boshqa akkauntga bog'langan.")
                return render(request, "register_verify.html", {"form": form, "phone": pending["phone"]})
            user = User.objects.create_user(
                username=pending["phone"],
                password=pending["password"],
                first_name=pending.get("full_name", ""),
            )
            if chat_id:
                TelegramProfile.objects.update_or_create(
                    user=user,
                    defaults={"chat_id": str(chat_id), "is_verified": True},
                )
            request.session.pop("pending_register", None)
            auth_login(request, user)
            return redirect("profile")
    needs_link = bool(request.session.get("pending_register_needs_link"))
    return render(
        request,
        "register_verify.html",
        {
            "form": form,
            "phone": pending["phone"],
            "needs_link": needs_link,
            "telegram_bot_username": settings.TELEGRAM_BOT_USERNAME,
        },
    )


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


def password_reset_request(request):
    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone"]
        user = User.objects.filter(username=phone).first()
        if not user:
            form.add_error("phone", "Bu telefon raqam bilan akkaunt topilmadi.")
        elif not settings.TELEGRAM_SEND_OTP:
            form.add_error(None, "Telegram orqali tiklash yoqilmagan.")
        else:
            chat_id = _get_linked_chat_id(phone)
            request.session["pending_password_reset"] = {
                "user_id": user.id,
                "phone": phone,
                "chat_id": str(chat_id) if chat_id else "",
            }
            request.session["pending_reset_needs_link"] = not bool(chat_id)
            if chat_id:
                _send_otp_code(phone, chat_id, OTP_PURPOSE_RESET)
            else:
                _cache_pending_reset(phone)
            return redirect("password_reset_confirm")
    return render(request, "password_reset_request.html", {"form": form})


def password_reset_confirm(request):
    pending = request.session.get("pending_password_reset")
    if not pending:
        return redirect("password_reset_request")
    form = PasswordResetConfirmForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ok, error = _verify_otp(pending["phone"], OTP_PURPOSE_RESET, form.cleaned_data["code"])
        if not ok:
            form.add_error("code", error)
        else:
            user = User.objects.filter(id=pending["user_id"]).first()
            if not user:
                form.add_error(None, "Foydalanuvchi topilmadi.")
            else:
                user.set_password(form.cleaned_data["password1"])
                user.save(update_fields=["password"])
                chat_id = pending.get("chat_id")
                if chat_id:
                    TelegramProfile.objects.update_or_create(
                        user=user,
                        defaults={"chat_id": str(chat_id), "is_verified": True},
                    )
                request.session.pop("pending_password_reset", None)
                return redirect("login")
    needs_link = bool(request.session.get("pending_reset_needs_link"))
    return render(
        request,
        "password_reset_confirm.html",
        {
            "form": form,
            "phone": pending["phone"],
            "needs_link": needs_link,
            "telegram_bot_username": settings.TELEGRAM_BOT_USERNAME,
        },
    )


def logout_view(request):
    auth_logout(request)
    return redirect("home")


@login_required
def profile(request):
    context = _build_profile_context(request)
    return render(request, "profile.html", context)


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


@login_required
@require_POST
def library_add(request):
    form = LibraryBookForm(request.POST)
    if form.is_valid():
        title = form.cleaned_data["title"]
        author = form.cleaned_data["author"]
        status = form.cleaned_data["status"]

        existing = LibraryBook.objects.filter(user=request.user, title=title, author=author).first()
        if existing:
            if existing.status != status:
                existing.status = status
                existing.save(update_fields=["status"])
        else:
            limit = _get_library_limit(request.user)
            if LibraryBook.objects.filter(user=request.user).count() >= limit:
                form.add_error(None, f"Kutubxonaga ko‘pi bilan {limit} ta kitob qo‘shish mumkin. Limitni oshirish uchun +998 91 963 07 70 raqamiga murojaat qiling.")
            else:
                LibraryBook.objects.create(user=request.user, title=title, author=author, status=status)

        if form.errors:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"errors": form.errors}, status=400)
            context = _build_profile_context(request, form=form)
            return render(request, "profile.html", context)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            library_q = (request.POST.get("library_q") or "").strip()
            return JsonResponse(_library_payload(request.user, library_q))
        return redirect("profile")
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"errors": form.errors}, status=400)
    context = _build_profile_context(request, form=form)
    return render(request, "profile.html", context)


@login_required
@require_POST
def library_delete(request, item_id):
    LibraryBook.objects.filter(id=item_id, user=request.user).delete()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        library_q = (request.POST.get("library_q") or "").strip()
        return JsonResponse(_library_payload(request.user, library_q))
    return redirect("profile")


@login_required
@require_POST
def library_status(request, item_id):
    status = (request.POST.get("status") or "").strip()
    allowed = {LibraryBook.STATUS_UNREAD, LibraryBook.STATUS_READING, LibraryBook.STATUS_FINISHED}
    if status in allowed:
        LibraryBook.objects.filter(id=item_id, user=request.user).update(status=status)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        library_q = (request.POST.get("library_q") or "").strip()
        return JsonResponse(_library_payload(request.user, library_q))
    return redirect("profile")


@login_required
def library_list(request):
    library_q = (request.GET.get("library_q") or "").strip()
    return JsonResponse(_library_payload(request.user, library_q))


@csrf_exempt
@require_POST
def telegram_webhook(request, token: str):
    if not settings.TELEGRAM_WEBHOOK_TOKEN or token != settings.TELEGRAM_WEBHOOK_TOKEN:
        return JsonResponse({"ok": False}, status=404)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False}, status=400)

    message = payload.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    if not chat_id or not text:
        return JsonResponse({"ok": True})

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        phone_raw = parts[1] if len(parts) > 1 else ""
        phone = normalize_phone(phone_raw)
        if len(phone) < 7:
            send_bot_message(str(chat_id), "Telefon raqamni yuboring: /start +998901234567")
            return JsonResponse({"ok": True})

        existing = TelegramProfile.objects.filter(chat_id=str(chat_id)).first()
        if existing and existing.user.username != phone:
            send_bot_message(str(chat_id), "Bu chat id boshqa akkauntga bog'langan.")
            return JsonResponse({"ok": True})

        user = User.objects.filter(username=phone).first()
        if user:
            TelegramProfile.objects.update_or_create(
                user=user,
                defaults={"chat_id": str(chat_id), "is_verified": True},
            )
            send_bot_message(str(chat_id), "Telegram hisobingiz bog'landi. Endi saytda kod keladi.")
        else:
            _cache_chat_link(phone, str(chat_id))
            send_bot_message(str(chat_id), "Bog'lash saqlandi. Endi saytda ro'yxatdan o'ting.")

        if settings.TELEGRAM_SEND_OTP:
            if cache.get(_pending_register_key(phone)):
                _send_otp_code(phone, str(chat_id), OTP_PURPOSE_REGISTER)
            if user and cache.get(_pending_reset_key(phone)):
                _send_otp_code(phone, str(chat_id), OTP_PURPOSE_RESET)
    else:
        send_bot_message(str(chat_id), "Bot faqat /start <telefon> formatini qabul qiladi.")

    return JsonResponse({"ok": True})
