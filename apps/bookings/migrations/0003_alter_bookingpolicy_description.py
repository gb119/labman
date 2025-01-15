# Generated by Django 4.2.17 on 2025-01-10 13:41

# Django imports
from django.db import migrations

# external imports
import labman_utils.models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bookingpolicy",
            name="description",
            field=labman_utils.models.ObfuscatedHTMLField(),
        ),
    ]