# Generated by Django 4.2.2 on 2023-06-25 19:36

# Django imports
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0005_alter_account_pages_alter_account_photos_and_more"),
        ("equipment", "0010_equipment_files"),
    ]

    operations = [
        migrations.CreateModel(
            name="BookingEntry",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_time", models.DateTimeField()),
                ("end_time", models.DateTimeField()),
                (
                    "equipment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="bookings", to="equipment.equipment"
                    ),
                ),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="accounts.project")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bookings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
