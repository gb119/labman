# Generated by Django 4.2.2 on 2023-06-24 16:36

# Django imports
from django.db import migrations

# external imports
import sortedm2m.fields


class Migration(migrations.Migration):

    dependencies = [
        ("flatpages", "0001_initial"),
        ("photologue", "0012_alter_photo_effect"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="pages",
            field=sortedm2m.fields.SortedManyToManyField(help_text=None, to="flatpages.flatpage"),
        ),
        migrations.AddField(
            model_name="account",
            name="photos",
            field=sortedm2m.fields.SortedManyToManyField(help_text=None, to="photologue.photo"),
        ),
    ]
