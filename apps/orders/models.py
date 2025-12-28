from django.db import models
from apps.catalog.models import Book


class Order(models.Model):
    PAYMENT_CHOICES = [
        ("cash", "Naqd"),
        ("bank", "Bank o‘tkazmasi"),
    ]
    STATUS_CHOICES = [
        ("new", "Yangi"),
        ("accepted", "Qabul qilindi"),
        ("delivering", "Yetkazilmoqda"),
        ("finished", "Yakunlangan"),
    ]
    ZONE_STATUS_CHOICES = [
        ("OK", "OK"),
        ("BLOCKED", "BLOCKED"),
    ]

    full_name = models.CharField("F.I.Sh", max_length=255)
    phone = models.CharField("Telefon", max_length=50, db_index=True)
    extra_phone = models.CharField("Qo‘shimcha telefon", max_length=50, blank=True)
    location = models.CharField("Lokatsiya", max_length=255, blank=True)
    address_text = models.CharField("Qo‘shimcha manzil matni", max_length=255, blank=True)
    address = models.CharField("Mo‘ljal", max_length=255)
    note = models.TextField("Izoh", blank=True)
    payment_type = models.CharField("To‘lov turi", max_length=20, choices=PAYMENT_CHOICES, default="cash")
    status = models.CharField("Holat", max_length=20, choices=STATUS_CHOICES, default="new", db_index=True)
    order_source = models.CharField("Manba", max_length=20, default="web")
    total_price = models.DecimalField("Umumiy summa", max_digits=10, decimal_places=2, default=0)
    subtotal_before_discount = models.DecimalField(
        "Chegirmasiz summa", max_digits=10, decimal_places=2, default=0
    )
    discount_percent = models.PositiveIntegerField("Chegirma (%)", default=0)
    discount_amount = models.DecimalField("Chegirma summasi", max_digits=10, decimal_places=2, default=0)
    delivery_time_choice = models.CharField(
        "Yetkazish vaqti", max_length=10, choices=[("now", "Hozirroq"), ("schedule", "Vaqtni tanlash")], default="now"
    )
    delivery_time = models.TimeField("Yetkazish vaqti (ixtiyoriy)", null=True, blank=True)
    latitude = models.DecimalField("Kenglik (lat)", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("Uzunlik (lng)", max_digits=9, decimal_places=6, null=True, blank=True)
    maps_link = models.URLField("Xarita havolasi", blank=True, default="")
    delivery_distance_km = models.DecimalField("Masofa (km)", max_digits=7, decimal_places=2, default=0)
    delivery_fee = models.IntegerField("Yetkazib berish narxi (so‘m)", default=0)
    delivery_zone_status = models.CharField(
        "Zona holati", max_length=10, choices=ZONE_STATUS_CHOICES, default="OK"
    )
    courier_maps_url = models.URLField("Kuryer xarita havolasi", blank=True, default="")
    delivery_pricing_snapshot = models.JSONField("Yetkazib berish hisoboti", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Buyurtma #{self.id} - {self.full_name}"


class DeliveryZone(models.Model):
    MODE_CHOICES = [
        ("CIRCLE", "Doira"),
        ("BBOX", "To‘rtburchak"),
    ]

    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="CIRCLE")
    center_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    center_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    radius_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    min_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    min_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    max_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    max_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    message = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Yetkazib berish zonasi"
        verbose_name_plural = "Yetkazib berish zonalari"

    def __str__(self):
        return self.name


class DeliveryNotice(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Yetkazib berish ma'lumoti"
        verbose_name_plural = "Yetkazib berish ma'lumotlari"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class DeliverySettings(models.Model):
    """Singleton-style delivery config editable via admin."""

    base_fee_uzs = models.PositiveIntegerField(default=10000)
    per_km_fee_uzs = models.PositiveIntegerField(default=2000)
    min_fee_uzs = models.PositiveIntegerField(default=10000)
    max_fee_uzs = models.PositiveIntegerField(default=60000)
    free_over_uzs = models.PositiveIntegerField(
        null=True, blank=True, help_text="Bo'sh qoldirilsa, chegirma yo'q"
    )
    shop_location_link = models.URLField("Do‘kon manzili (havola)", blank=True, default="")
    shop_lat = models.DecimalField(
        "Do‘kon lat (ixtiyoriy)", max_digits=9, decimal_places=6, null=True, blank=True
    )
    shop_lng = models.DecimalField(
        "Do‘kon lng (ixtiyoriy)", max_digits=9, decimal_places=6, null=True, blank=True
    )
    order_start_time = models.TimeField("Buyurtma boshlanishi", null=True, blank=True)
    order_end_time = models.TimeField("Buyurtma tugashi", null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Yetkazib berish sozlamasi"
        verbose_name_plural = "Yetkazib berish sozlamalari"

    def __str__(self):
        return "Yetkazib berish sozlamasi"

    @classmethod
    def get_active(cls):
        # Always return a single config row; create defaults if missing.
        obj, _ = cls.objects.get_or_create(id=1)
        return obj


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def line_total(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.book.title} x{self.quantity}"
