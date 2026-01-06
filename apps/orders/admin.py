from django.contrib import admin, messages
from django.utils.html import format_html

from django import forms

from .models import DeliveryNotice, DeliveryZone, Order, OrderItem, DeliverySettings
from .services.delivery import (
    build_courier_url,
    generate_google_maps_link,
    parse_coordinates_from_link,
    recalculate_delivery,
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("book", "quantity", "price")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "phone",
        "delivery_fee",
        "delivery_distance_km",
        "delivery_zone_status",
        "maps_link_display",
        "status",
        "created_at",
    )
    list_filter = ("status", "payment_type", "created_at", "delivery_zone_status")
    inlines = [OrderItemInline]
    search_fields = ("full_name", "phone", "location", "address_text")
    readonly_fields = (
        "total_price",
        "delivery_distance_km",
        "delivery_fee",
        "delivery_zone_status",
        "maps_link",
        "courier_maps_url",
        "delivery_pricing_snapshot",
    )
    actions = ["recalculate_delivery_action"]

    @admin.display(description="Xarita")
    def maps_link_display(self, obj):
        if obj.latitude and obj.longitude:
            url = obj.maps_link or generate_google_maps_link(float(obj.latitude), float(obj.longitude))
            return format_html('<a href="{}" target="_blank" rel="noopener">Open in Maps</a>', url)
        return "—"

    @admin.action(description="Yetkazib berishni qayta hisoblash")
    def recalculate_delivery_action(self, request, queryset):
        for order in queryset:
            recalculate_delivery(order)
        self.message_user(request, f"{queryset.count()} ta buyurtma uchun qayta hisoblandi.")


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "mode", "is_active", "message")
    list_filter = ("mode", "is_active")
    search_fields = ("name", "message")


@admin.register(DeliveryNotice)
class DeliveryNoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("title", "body")


class DeliverySettingsForm(forms.ModelForm):
    class Meta:
        model = DeliverySettings
        fields = "__all__"

    class Media:
        css = {
            "all": ("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",),
        }
        js = (
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
            "orders/admin_shop_origin.js",
        )


@admin.register(DeliverySettings)
class DeliverySettingsAdmin(admin.ModelAdmin):
    form = DeliverySettingsForm
    list_display = (
        "base_fee_uzs",
        "per_km_fee_uzs",
        "min_fee_uzs",
        "max_fee_uzs",
        "free_over_uzs",
        "order_start_time",
        "order_end_time",
        "updated_at",
    )

    def save_model(self, request, obj, form, change):
        """
        Allow ops to paste a map link; we parse it into coordinates so distance
        calculations work even if they don't set lat/lng manually.
        """
        coords = parse_coordinates_from_link(obj.shop_location_link or "")
        if coords:
            obj.shop_lat, obj.shop_lng = coords
            messages.info(request, "Do‘kon koordinatalari kiritilgan havoladan olindi.")
        elif obj.shop_location_link:
            messages.warning(request, "Koordinatalar havoladan aniqlanmadi, iltimos linkni tekshiring.")
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        # Enforce singleton: allow add only if none exists.
        if DeliverySettings.objects.exists():
            return False
        return super().has_add_permission(request)
