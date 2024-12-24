# Generated by Django 4.2.2 on 2023-06-18 22:08

# Django imports
from django.db import migrations

# external imports
import sortedm2m.fields


class Migration(migrations.Migration):

    dependencies = [
        ("photologue", "0012_alter_photo_effect"),
        ("equipment", "0004_alter_equipment_photos"),
    ]

    operations = [
        migrations.AlterField(
            model_name="equipment",
            name="photos",
            field=sortedm2m.fields.SortedManyToManyField(
                blank=True, help_text=None, related_name="equipment", to="photologue.photo"
            ),
        ),
    ]
