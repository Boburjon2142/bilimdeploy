from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class LibraryBook(models.Model):
    STATUS_UNREAD = "unread"
    STATUS_READING = "reading"
    STATUS_FINISHED = "finished"

    STATUS_CHOICES = [
        (STATUS_UNREAD, "O‘qilmagan"),
        (STATUS_READING, "O‘qilmoqda"),
        (STATUS_FINISHED, "O‘qilgan"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="library_books")
    title = models.CharField("Kitob nomi", max_length=255)
    author = models.CharField("Muallif", max_length=255)
    status = models.CharField("Holat", max_length=10, choices=STATUS_CHOICES, default=STATUS_UNREAD)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        unique_together = [("user", "title", "author")]
        indexes = [
            models.Index(fields=["user", "status"], name="lib_user_status"),
            models.Index(fields=["user", "title"], name="lib_user_title"),
            models.Index(fields=["user", "author"], name="lib_user_author"),
        ]
        verbose_name = "Kutubxona kitobi"
        verbose_name_plural = "Kutubxona kitoblari"

    def __str__(self):
        return f"{self.title} — {self.author}"

    def save(self, *args, **kwargs):
        self.title = (self.title or "").strip()
        self.author = (self.author or "").strip()
        super().save(*args, **kwargs)


class LibraryLimit(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="library_limit")
    limit = models.PositiveIntegerField(default=10)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kutubxona limiti"
        verbose_name_plural = "Kutubxona limitlari"

    def __str__(self):
        return f"{self.user} — {self.limit}"
