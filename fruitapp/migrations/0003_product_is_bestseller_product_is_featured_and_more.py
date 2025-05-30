# Generated by Django 4.2.14 on 2025-05-22 23:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fruitapp", "0002_product_star"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_bestseller",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="product",
            name="is_featured",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="product",
            name="is_organic",
            field=models.BooleanField(default=False),
        ),
    ]
