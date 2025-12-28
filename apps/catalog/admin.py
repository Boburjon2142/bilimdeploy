from django.contrib import admin
from django import forms
from .models import Author, Category, Book, Banner, FeaturedCategory, AboutPage


class BookInline(admin.TabularInline):
    model = Book
    extra = 0
    fields = ("title", "category", "sale_price")
    readonly_fields = ("title", "category", "sale_price")


class BookAdminForm(forms.ModelForm):
    author_name = forms.CharField(label="Muallif", required=True)

    class Meta:
        model = Book
        fields = [
            "title",
            "slug",
            "category",
            "author_name",
            "purchase_price",
            "sale_price",
            "stock_quantity",
            "description",
            "cover_image",
            "book_format",
            "pages",
            "is_recommended",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.author_id:
            self.fields["author_name"].initial = self.instance.author.name

    def save(self, commit=True):
        author_name = self.cleaned_data.get("author_name", "").strip()
        author_obj, _ = Author.objects.get_or_create(name=author_name)
        self.instance.author = author_obj
        return super().save(commit=commit)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "is_featured")
    search_fields = ("name",)
    list_editable = ("is_featured",)
    inlines = [BookInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    list_filter = ("parent",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "purchase_price", "sale_price", "is_recommended", "views", "created_at")
    list_filter = ("category", "author", "is_recommended", "book_format")
    search_fields = ("title", "author__name")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category",)
    form = BookAdminForm


@admin.register(FeaturedCategory)
class FeaturedCategoryAdmin(admin.ModelAdmin):
    list_display = ("category", "title", "limit", "order", "is_active")
    list_editable = ("limit", "order", "is_active")
    search_fields = ("category__name", "title")


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active", "created_at")
    list_editable = ("order", "is_active")


@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "updated_at")
    list_editable = ("is_active",)
    search_fields = ("title", "body")
