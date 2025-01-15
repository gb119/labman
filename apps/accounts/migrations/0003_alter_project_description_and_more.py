# Generated by Django 4.2.17 on 2025-01-10 13:41

# Django imports
from django.db import migrations

# external imports
import labman_utils.models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_role_css"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="description",
            field=labman_utils.models.ObfuscatedHTMLField(),
        ),
        migrations.AlterField(
            model_name="researchgroup",
            name="description",
            field=labman_utils.models.ObfuscatedHTMLField(),
        ),
        migrations.AlterField(
            model_name="role",
            name="description",
            field=labman_utils.models.ObfuscatedHTMLField(),
        ),
    ]