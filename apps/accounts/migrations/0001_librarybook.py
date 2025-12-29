from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LibraryBook",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255, verbose_name="Kitob nomi")),
                ("author", models.CharField(max_length=255, verbose_name="Muallif")),
                (
                    "status",
                    models.CharField(
                        choices=[("unread", "O‘qilmagan"), ("reading", "O‘qilmoqda"), ("finished", "O‘qilgan")],
                        default="unread",
                        max_length=10,
                        verbose_name="Holat",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="library_books",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Kutubxona kitobi",
                "verbose_name_plural": "Kutubxona kitoblari",
                "ordering": ["-created_at", "-id"],
                "unique_together": {("user", "title", "author")},
                "indexes": [
                    models.Index(fields=["user", "status"], name="lib_user_status"),
                    models.Index(fields=["user", "title"], name="lib_user_title"),
                    models.Index(fields=["user", "author"], name="lib_user_author"),
                ],
            },
        ),
    ]
