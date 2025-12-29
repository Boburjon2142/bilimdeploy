from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import LibraryBookForm, PhoneAuthenticationForm, PhoneUserCreationForm
from .models import LibraryBook, LibraryLimit
from apps.orders.services.telegram import send_order_canceled, send_order_delivered


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
