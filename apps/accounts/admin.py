from django.contrib import admin

from .models import LibraryBook, LibraryLimit


@admin.register(LibraryBook)
class LibraryBookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "author", "user__username")
    ordering = ("-created_at",)


@admin.register(LibraryLimit)
class LibraryLimitAdmin(admin.ModelAdmin):
    list_display = ("user", "limit", "updated_at")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    ordering = ("-updated_at",)
