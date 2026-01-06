from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, F
from django.http import JsonResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET
from django.conf import settings
from django.utils.translation import get_language
from .models import Category, Book, Author, Banner, FeaturedCategory


from .cache_keys import (
    home_top_categories_key,
    home_featured_authors_key,
    home_banners_key,
    home_featured_cfgs_key,
    home_featured_books_key,
    home_best_selling_key,
    home_new_books_key,
    home_recommended_key,
    best_selling_list_key,
    recommended_list_key,
    categories_top_key,
)

HOME_TTL = 60 * 5  # 5 minutes; homepage rotates moderately often
LIST_TTL = 60 * 10  # 10 minutes; bestseller/recommended lists are stable
CATEGORY_TTL = 60 * 15  # 15 minutes; taxonomy changes rarely


_LATIN_TO_CYR = {
    "o'": "ў",
    "g'": "ғ",
    "sh": "ш",
    "ch": "ч",
    "ya": "я",
    "yo": "ё",
    "yu": "ю",
    "a": "а",
    "b": "б",
    "d": "д",
    "e": "е",
    "f": "ф",
    "g": "г",
    "h": "ҳ",
    "i": "и",
    "j": "ж",
    "k": "к",
    "l": "л",
    "m": "м",
    "n": "н",
    "o": "о",
    "p": "п",
    "q": "қ",
    "r": "р",
    "s": "с",
    "t": "т",
    "u": "у",
    "v": "в",
    "x": "х",
    "y": "й",
    "z": "з",
}
_CYR_TO_LAT = {
    "ў": "o'",
    "ғ": "g'",
    "ш": "sh",
    "ч": "ch",
    "я": "ya",
    "ё": "yo",
    "ю": "yu",
    "а": "a",
    "б": "b",
    "д": "d",
    "е": "e",
    "ф": "f",
    "г": "g",
    "ҳ": "h",
    "и": "i",
    "ж": "j",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "қ": "q",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "в": "v",
    "х": "x",
    "й": "y",
    "з": "z",
    "ь": "",
    "ъ": "",
}


def _to_cyrillic(text: str) -> str:
    value = text.lower()
    result = []
    i = 0
    while i < len(value):
        pair = value[i : i + 2]
        if pair in _LATIN_TO_CYR:
            result.append(_LATIN_TO_CYR[pair])
            i += 2
            continue
        ch = value[i]
        result.append(_LATIN_TO_CYR.get(ch, ch))
        i += 1
    return "".join(result)


def _to_latin(text: str) -> str:
    value = text.lower()
    result = []
    for ch in value:
        result.append(_CYR_TO_LAT.get(ch, ch))
    return "".join(result)


def _build_search_variants(query: str) -> list:
    variants = {query}
    variants.add(_to_cyrillic(query))
    variants.add(_to_latin(query))
    return [v for v in variants if v]


def _abs_media_url(request, field):
    if not field:
        return None
    try:
        url = field.url
    except Exception:
        return None
    return request.build_absolute_uri(url)


def _serialize_category(category):
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "parent_id": category.parent_id,
    }


def _serialize_author(request, author):
    return {
        "id": author.id,
        "name": author.name,
        "bio": author.bio,
        "is_featured": author.is_featured,
        "photo": _abs_media_url(request, author.photo),
    }


def _serialize_banner(request, banner):
    return {
        "id": banner.id,
        "title": banner.title,
        "image": _abs_media_url(request, banner.image),
        "link": banner.link,
        "order": banner.order,
        "is_active": banner.is_active,
    }


def _serialize_book(request, book):
    return {
        "id": book.id,
        "title": book.title,
        "slug": book.slug,
        "description": book.description,
        "purchase_price": str(book.purchase_price),
        "sale_price": str(book.sale_price),
        "stock_quantity": book.stock_quantity,
        "book_format": book.book_format,
        "pages": book.pages,
        "is_recommended": book.is_recommended,
        "views": book.views,
        "created_at": book.created_at.isoformat(),
        "cover_image": _abs_media_url(request, book.cover_image),
        "author": {
            "id": book.author_id,
            "name": book.author.name,
        },
        "category": {
            "id": book.category_id,
            "name": book.category.name,
            "slug": book.category.slug,
        },
    }


def _get_pagination(request, default_limit=20, max_limit=100):
    try:
        limit = int(request.GET.get("limit", default_limit))
    except (TypeError, ValueError):
        limit = default_limit
    try:
        offset = int(request.GET.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    if limit <= 0:
        limit = default_limit
    if limit > max_limit:
        limit = max_limit
    if offset < 0:
        offset = 0
    return limit, offset


@cache_page(HOME_TTL)
def home(request):
    lang = get_language() or getattr(settings, "LANGUAGE_CODE", "default")
    # Cache only public, non-user-specific content to reduce DB hits.
    categories = cache.get_or_set(
        home_top_categories_key(lang),
        lambda: list(Category.objects.filter(parent__isnull=True)[:4]),
        HOME_TTL,
    )
    authors = cache.get_or_set(
        home_featured_authors_key(lang),
        lambda: list(Author.objects.filter(is_featured=True)[:10]),
        HOME_TTL,
    )
    banners = cache.get_or_set(
        home_banners_key(lang),
        lambda: list(
            Banner.objects.filter(is_active=True)
            .order_by("order", "-created_at")
            .select_related(None)[:5]
        ),
        HOME_TTL,
    )
    featured_cfgs = cache.get_or_set(
        home_featured_cfgs_key(lang),
        lambda: list(
            FeaturedCategory.objects.filter(is_active=True)
            .select_related("category")
        ),
        HOME_TTL,
    )
    featured_sections = []
    for cfg in featured_cfgs:
        limit = cfg.limit or 10
        books_key = home_featured_books_key(cfg.category_id, limit, lang)
        books = cache.get_or_set(
            books_key,
            lambda: list(
                Book.objects.filter(category=cfg.category)
                .select_related("author", "category")
                .order_by("-created_at")[:limit]
            ),
            HOME_TTL,
        )
        featured_sections.append(
            {
                "title": cfg.title or cfg.category.name,
                "category": cfg.category,
                "books": books,
            }
        )
    best_selling = cache.get_or_set(
        home_best_selling_key(lang),
        lambda: list(
            Book.objects.select_related("author", "category")
            .order_by("-views")[:6]
        ),
        LIST_TTL,
    )
    new_books = cache.get_or_set(
        home_new_books_key(lang),
        lambda: list(
            Book.objects.select_related("author", "category")
            .order_by("-created_at")[:6]
        ),
        HOME_TTL,
    )
    recommended = cache.get_or_set(
        home_recommended_key(lang),
        lambda: list(
            Book.objects.filter(is_recommended=True)
            .select_related("author", "category")
            .order_by("-created_at")[:6]
        ),
        LIST_TTL,
    )
    return render(
        request,
        "home.html",
        {
            "categories": categories,
            "authors": authors,
            "banners": banners,
            "featured_sections": featured_sections,
            "best_selling": best_selling,
            "new_books": new_books,
            "recommended": recommended,
        },
    )


@cache_page(CATEGORY_TTL)
def categories_list(request):
    lang = get_language() or getattr(settings, "LANGUAGE_CODE", "default")
    categories = cache.get_or_set(
        categories_top_key(lang),
        lambda: list(Category.objects.filter(parent__isnull=True).order_by("name")),
        CATEGORY_TTL,
    )
    return render(request, "categories_list.html", {"categories": categories})


@cache_page(CATEGORY_TTL)
def authors_list(request):
    authors = Author.objects.all().order_by("name")
    return render(request, "authors_list.html", {"authors": authors})


@cache_page(CATEGORY_TTL)
def about(request):
    from .models import AboutPage

    about_page = (
        AboutPage.objects.filter(is_active=True)
        .order_by("-updated_at", "-id")
        .first()
    )
    return render(request, "about.html", {"about_page": about_page})


@cache_page(HOME_TTL)
def new_books_list(request):
    books = Book.objects.order_by("-created_at")
    return render(request, "book_list.html", {"title": "Yangi qo‘shilganlar", "books": books})


@cache_page(LIST_TTL)
def best_selling_list(request):
    lang = get_language() or getattr(settings, "LANGUAGE_CODE", "default")
    # Safe to cache: same for every user, changes only when sales/views change.
    books = cache.get_or_set(
        best_selling_list_key(lang),
        lambda: list(Book.objects.select_related("author", "category").order_by("-views")),
        LIST_TTL,
    )
    return render(request, "book_list.html", {"title": "Eng ko‘p sotilganlar", "books": books})


@cache_page(LIST_TTL)
def recommended_list(request):
    lang = get_language() or getattr(settings, "LANGUAGE_CODE", "default")
    # Safe to cache: recommendation flag is content-based, not user-based.
    books = cache.get_or_set(
        recommended_list_key(lang),
        lambda: list(
            Book.objects.filter(is_recommended=True)
            .select_related("author", "category")
            .order_by("-created_at")
        ),
        LIST_TTL,
    )
    return render(request, "book_list.html", {"title": "Tavsiya etilganlar", "books": books})


def author_detail(request, author_id):
    author = get_object_or_404(Author, id=author_id)
    books = Book.objects.filter(author=author).select_related("category").order_by("-created_at")
    return render(request, "book_list.html", {"title": author.name, "books": books})


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    descendants = category.children.all()
    category_ids = [category.id] + list(descendants.values_list("id", flat=True))
    books = (
        Book.objects.filter(category__in=category_ids)
        .select_related("author", "category")
    )
    authors = Author.objects.filter(books__category__in=category_ids).distinct()

    author_id = request.GET.get("author")
    if author_id:
        books = books.filter(author_id=author_id)

    sort = request.GET.get("sort")
    sort_map = {
        "price_asc": "sale_price",
        "price_desc": "-sale_price",
        "newest": "-created_at",
        "oldest": "created_at",
        "popular": "-views",
    }
    if sort in sort_map:
        books = books.order_by(sort_map[sort])

    return render(
        request,
        "category_list.html",
        {
            "category": category,
            "books": books,
            "authors": authors,
            "current_author": author_id,
            "current_sort": sort,
            "child_categories": descendants,
        },
    )


def book_detail(request, id, slug):
    book = get_object_or_404(Book.objects.select_related("author", "category"), id=id, slug=slug)
    Book.objects.filter(id=book.id).update(views=F("views") + 1)
    favorites = request.session.get("favorites", [])
    in_favorites = str(book.id) in favorites
    similar_books = (
        Book.objects.filter(category=book.category)
        .exclude(id=book.id)
        .select_related("author", "category")
        .order_by("-views")[:10]
    )
    return render(
        request,
        "book_detail.html",
        {
            "book": book,
            "in_favorites": in_favorites,
            "similar_books": similar_books,
        },
    )


def search(request):
    def normalize(v):
        return None if v in [None, "", "None", "null"] else v

    query = request.GET.get("q", "").strip()
    variants = _build_search_variants(query) if query else []

    # Normalize GET params
    author_id = normalize(request.GET.get("author"))
    category_slug = normalize(request.GET.get("category"))
    sort = normalize(request.GET.get("sort"))
    limit = normalize(request.GET.get("limit"))

    books = Book.objects.none()
    authors = Author.objects.none()
    categories = Category.objects.all()

    sort_options = [
        ("", "Mosligi bo‘yicha"),
        ("popular", "Eng saralar"),
        ("newest", "Yangi"),
        ("alpha_asc", "Alifbo (A-Z)"),
        ("alpha_desc", "Alifbo (Z-A)"),
        ("price_desc", "Narx (qimmat-arzon)"),
        ("price_asc", "Narx (arzon-qimmat)"),
    ]

    limit_options = ["8", "12", "16", "24", "32"]
    top_searched = (
        Book.objects.select_related("author", "category")
        .order_by("-views")[:5]
    )

    if query:
        q_filter = Q()
        for term in variants:
            q_filter |= Q(title__icontains=term)
            q_filter |= Q(author__name__icontains=term)
            q_filter |= Q(category__name__icontains=term)
        books = Book.objects.filter(q_filter).select_related("author", "category")

        # Filter by author
        if author_id:
            books = books.filter(author_id=author_id)

        # Filter by category
        if category_slug:
            books = books.filter(category__slug=category_slug)

        # Sorting
        sort_map = {
            "price_asc": "sale_price",
            "price_desc": "-sale_price",
            "newest": "-created_at",
            "oldest": "created_at",
            "popular": "-views",
            "alpha_asc": "title",
            "alpha_desc": "-title",
        }

        if sort in sort_map:
            books = books.order_by(sort_map[sort])

        # Sidebar authors
        authors = Author.objects.filter(books__in=books).distinct()

        # Limit
        if limit:
            try:
                limit_int = int(limit)
                if limit_int > 0:
                    books = books[:limit_int]
            except ValueError:
                pass

    return render(
        request,
        "search_results.html",
        {
            "query": query,
            "books": books,
            "authors": authors,
            "categories": categories,
            "top_searched": top_searched,
            "current_author": author_id,
            "current_category": category_slug,
            "current_sort": sort,
            "current_limit": limit,
            "sort_options": sort_options,
            "limit_options": limit_options,
        },
    )



def favorites(request):
    fav_ids = request.session.get("favorites", [])
    books = Book.objects.filter(id__in=fav_ids).select_related("author", "category")
    return render(request, "favorites.html", {"books": books})


def add_favorite(request, book_id):
    favs = request.session.get("favorites", [])
    key = str(book_id)
    if key not in favs:
        favs.append(key)
    request.session["favorites"] = favs
    request.session.modified = True
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect("favorites")


def remove_favorite(request, book_id):
    favs = request.session.get("favorites", [])
    key = str(book_id)
    if key in favs:
        favs.remove(key)
        request.session["favorites"] = favs
        request.session.modified = True
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect("favorites")


@cache_page(HOME_TTL)
@require_GET
def api_home(request):
    lang = get_language() or getattr(settings, "LANGUAGE_CODE", "default")
    categories = cache.get_or_set(
        home_top_categories_key(lang),
        lambda: list(Category.objects.filter(parent__isnull=True)[:4]),
        HOME_TTL,
    )
    authors = cache.get_or_set(
        home_featured_authors_key(lang),
        lambda: list(Author.objects.filter(is_featured=True)[:10]),
        HOME_TTL,
    )
    banners = cache.get_or_set(
        home_banners_key(lang),
        lambda: list(
            Banner.objects.filter(is_active=True)
            .order_by("order", "-created_at")
            .select_related(None)[:5]
        ),
        HOME_TTL,
    )
    featured_cfgs = cache.get_or_set(
        home_featured_cfgs_key(lang),
        lambda: list(
            FeaturedCategory.objects.filter(is_active=True)
            .select_related("category")
        ),
        HOME_TTL,
    )
    featured_sections = []
    for cfg in featured_cfgs:
        limit = cfg.limit or 10
        books_key = home_featured_books_key(cfg.category_id, limit, lang)
        books = cache.get_or_set(
            books_key,
            lambda: list(
                Book.objects.filter(category=cfg.category)
                .select_related("author", "category")
                .order_by("-created_at")[:limit]
            ),
            HOME_TTL,
        )
        featured_sections.append(
            {
                "title": cfg.title or cfg.category.name,
                "category": _serialize_category(cfg.category),
                "books": [_serialize_book(request, book) for book in books],
            }
        )
    best_selling = cache.get_or_set(
        home_best_selling_key(lang),
        lambda: list(
            Book.objects.select_related("author", "category")
            .order_by("-views")[:6]
        ),
        LIST_TTL,
    )
    new_books = cache.get_or_set(
        home_new_books_key(lang),
        lambda: list(
            Book.objects.select_related("author", "category")
            .order_by("-created_at")[:6]
        ),
        HOME_TTL,
    )
    recommended = cache.get_or_set(
        home_recommended_key(lang),
        lambda: list(
            Book.objects.filter(is_recommended=True)
            .select_related("author", "category")
            .order_by("-created_at")[:6]
        ),
        LIST_TTL,
    )
    data = {
        "categories": [_serialize_category(category) for category in categories],
        "authors": [_serialize_author(request, author) for author in authors],
        "banners": [_serialize_banner(request, banner) for banner in banners],
        "featured_sections": featured_sections,
        "best_selling": [_serialize_book(request, book) for book in best_selling],
        "new_books": [_serialize_book(request, book) for book in new_books],
        "recommended": [_serialize_book(request, book) for book in recommended],
    }
    return JsonResponse(data)


@cache_page(CATEGORY_TTL)
@require_GET
def api_categories(request):
    categories = list(Category.objects.all().order_by("name"))
    by_id = {
        category.id: {**_serialize_category(category), "children": []}
        for category in categories
    }
    roots = []
    for category in categories:
        payload = by_id[category.id]
        if category.parent_id and category.parent_id in by_id:
            by_id[category.parent_id]["children"].append(payload)
        else:
            roots.append(payload)
    return JsonResponse({"items": roots})


@cache_page(CATEGORY_TTL)
@require_GET
def api_authors(request):
    authors = Author.objects.all().order_by("name")
    return JsonResponse({"items": [_serialize_author(request, author) for author in authors]})


@cache_page(LIST_TTL)
@require_GET
def api_books(request):
    qs = Book.objects.select_related("author", "category").all()
    query = request.GET.get("q", "").strip()
    if query:
        variants = _build_search_variants(query)
        q_filter = Q()
        for term in variants:
            q_filter |= Q(title__icontains=term)
            q_filter |= Q(author__name__icontains=term)
            q_filter |= Q(category__name__icontains=term)
        qs = qs.filter(q_filter)

    category = request.GET.get("category")
    if category:
        if category.isdigit():
            qs = qs.filter(category_id=int(category))
        else:
            qs = qs.filter(category__slug=category)

    author = request.GET.get("author")
    if author and author.isdigit():
        qs = qs.filter(author_id=int(author))

    sort = request.GET.get("sort")
    sort_map = {
        "price_asc": "sale_price",
        "price_desc": "-sale_price",
        "newest": "-created_at",
        "oldest": "created_at",
        "popular": "-views",
        "alpha_asc": "title",
        "alpha_desc": "-title",
    }
    if sort in sort_map:
        qs = qs.order_by(sort_map[sort])

    total = qs.count()
    limit, offset = _get_pagination(request, default_limit=20, max_limit=100)
    items = qs[offset : offset + limit]
    data = {
        "count": total,
        "limit": limit,
        "offset": offset,
        "items": [_serialize_book(request, book) for book in items],
    }
    return JsonResponse(data)


@require_GET
def api_book_detail(request, id):
    book = get_object_or_404(Book.objects.select_related("author", "category"), id=id)
    Book.objects.filter(id=book.id).update(views=F("views") + 1)
    similar_books = (
        Book.objects.filter(category=book.category)
        .exclude(id=book.id)
        .select_related("author", "category")
        .order_by("-views")[:10]
    )
    data = {
        "book": _serialize_book(request, book),
        "similar": [_serialize_book(request, item) for item in similar_books],
    }
    return JsonResponse(data)


@cache_page(CATEGORY_TTL)
@require_GET
def api_about(request):
    from .models import AboutPage

    about_page = (
        AboutPage.objects.filter(is_active=True)
        .order_by("-updated_at", "-id")
        .first()
    )
    data = None
    if about_page:
        data = {
            "title": about_page.title,
            "body": about_page.body,
            "link": about_page.link,
            "image": _abs_media_url(request, about_page.image),
            "updated_at": about_page.updated_at.isoformat(),
        }
    return JsonResponse({"item": data})
