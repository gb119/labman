# Generated by Django 4.2.17 on 2025-01-22 17:13

# Django imports
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0004_alter_documentsignoff_version_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="shift",
            name="weighting",
            field=models.FloatField(default=1.0),
        ),
    ]
