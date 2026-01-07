from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_librarylimit"),
    ]

    operations = [
        migrations.CreateModel(
            name="TelegramProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chat_id", models.CharField(max_length=64, unique=True)),
                ("is_verified", models.BooleanField(default=True)),
                ("verified_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="telegram_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Telegram profili",
                "verbose_name_plural": "Telegram profillari",
            },
        ),
    ]
