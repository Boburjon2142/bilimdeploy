from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0011_alter_book_purchase_price_alter_book_sale_price"),
    ]

    operations = [
        migrations.AlterField(
            model_name="book",
            name="purchase_price",
            field=models.DecimalField(
                blank=True,
                null=True,
                decimal_places=0,
                max_digits=8,
                verbose_name="Sotib olish narxi",
            ),
        ),
    ]
