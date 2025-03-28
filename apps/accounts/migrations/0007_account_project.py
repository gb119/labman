# Generated by Django 4.2.19 on 2025-02-19 20:22

# Django imports
from django.db import migrations

# external imports
import sortedm2m.fields


class Migration(migrations.Migration):

    dependencies = [
        ("costings", "0005_alter_costcentre_people"),
        ("accounts", "0006_delete_project"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="project",
            field=sortedm2m.fields.SortedManyToManyField(
                blank=True,
                help_text=None,
                related_name="accounts",
                to="costings.costcentre",
            ),
        ),
    ]
