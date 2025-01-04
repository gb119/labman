# Generated by Django 4.2.17 on 2025-01-04 22:50

# Django imports
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("equipment", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("bookings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="bookingentry",
            name="equipment",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="bookings",
                to="equipment.equipment",
            ),
        ),
        migrations.AddField(
            model_name="bookingentry",
            name="project",
            field=models.ForeignKey(
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="accounts.project",
            ),
        ),
        migrations.AddField(
            model_name="bookingentry",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="bookings",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]