from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Author(models.Model):
    name = models.CharField("Muallif", max_length=255, db_index=True)
    bio = models.TextField("Tarjimai hol", blank=True)
    is_featured = models.BooleanField("Asosiy sahifada ko‘rsatish", default=False)
    photo = models.ImageField("Rasm", upload_to="authors/", blank=True, null=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Muallif"
        verbose_name_plural = "Mualliflar"

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField("Nomi", max_length=255)
    slug = models.SlugField("Slug", unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
        verbose_name="Ota kategoriya",
    )

    class Meta:
        verbose_name_plural = "Kategoriyalar"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class FeaturedCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="featured_items", verbose_name="Kategoriya")
    title = models.CharField("Sarlavha", max_length=255, blank=True)
    limit = models.PositiveIntegerField("Nechta ko‘rsatilsin", default=10)
    order = models.PositiveIntegerField("Tartib", default=0)
    is_active = models.BooleanField("Faol", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Tanlangan kategoriya"
        verbose_name_plural = "Tanlangan kategoriyalar"

    def __str__(self):
        return self.title or f"{self.category.name}"


class Book(models.Model):
    FORMAT_CHOICES = [
        ("hard", "Qattiq muqova"),
        ("soft", "Yumshoq muqova"),
    ]

    title = models.CharField("Sarlavha", max_length=255)
    slug = models.SlugField("Slug", unique=True)
    category = models.ForeignKey(Category, verbose_name="Kategoriya", on_delete=models.CASCADE, related_name="books")
    author = models.ForeignKey(Author, verbose_name="Muallif", on_delete=models.CASCADE, related_name="books")
    purchase_price = models.DecimalField("Sotib olish narxi", max_digits=8, decimal_places=0)
    sale_price = models.DecimalField("Sotish narxi", max_digits=8, decimal_places=0)
    stock_quantity = models.PositiveIntegerField("Ombordagi soni", default=0)
    description = models.TextField("Tavsif", blank=True)
    cover_image = models.ImageField("Muqova", upload_to="covers/", blank=True, null=True)
    book_format = models.CharField("Format", max_length=10, choices=FORMAT_CHOICES, blank=True)
    pages = models.PositiveIntegerField("Betlar soni", blank=True, null=True)
    is_recommended = models.BooleanField("Tavsiya etilgan", default=False, db_index=True)
    views = models.PositiveIntegerField("Ko‘rishlar soni", default=0, db_index=True)
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kitob"
        verbose_name_plural = "Kitoblar"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("book_detail", args=[self.id, self.slug])


class Banner(models.Model):
    title = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to="banners/")
    link = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title or f"Banner #{self.id}"


class AboutPage(models.Model):
    title = models.CharField("Sarlavha", max_length=255, default="Biz haqimizda")
    body = models.TextField("Matn", blank=True)
    link = models.URLField("Havola", blank=True)
    image = models.ImageField("Rasm", upload_to="about/", blank=True, null=True)
    is_active = models.BooleanField("Faol", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Biz haqimizda kontent"
        verbose_name_plural = "Biz haqimizda kontenti"
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return self.title
