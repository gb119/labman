# Generated by Django 4.2.17 on 2025-01-06 16:49

# Django imports
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="css",
            field=models.CharField(
                default="bg-gradient bg-success text-white",
                max_length=40,
                verbose_name="CSS class",
            ),
        ),
    ]