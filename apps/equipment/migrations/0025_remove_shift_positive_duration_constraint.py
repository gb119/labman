# Generated by Django 4.2.17 on 2025-01-02 15:05

# Django imports
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0024_alter_shift_options_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="shift",
            name="Positive Duration Constraint",
        ),
    ]