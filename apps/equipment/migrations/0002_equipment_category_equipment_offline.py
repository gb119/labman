# Generated by Django 4.2.17 on 2025-01-07 14:49

# Django imports
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipment",
            name="category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("cryostat", "Cryostat"),
                    ("deposition", "Thin fil;m growth"),
                    ("magnetometer", "Magnetic Characterisation"),
                    ("furnace", "Furnace"),
                    ("transport", "Electrical Transport"),
                    ("characterisation", "Material Characterisation"),
                    ("other", "Other"),
                ],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="equipment",
            name="offline",
            field=models.BooleanField(default=False),
        ),
    ]
