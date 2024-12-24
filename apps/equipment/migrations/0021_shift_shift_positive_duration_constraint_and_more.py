# Generated by Django 4.2.5 on 2023-09-12 22:16

# Python imports
import datetime

# Django imports
from django.db import migrations, models

# external imports
import sortedm2m.fields
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0020_equipment_pages"),
    ]

    operations = [
        migrations.CreateModel(
            name="Shift",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(blank=True, max_length=80, null=True)),
                ("description", tinymce.models.HTMLField()),
                ("start_time", models.TimeField(default=datetime.time(9, 0))),
                ("end_time", models.TimeField(default=datetime.time(18, 0))),
            ],
            options={
                "verbose_name": "Booking Shift",
                "verbose_name_plural": "Booking shofts",
                "ordering": ["start_time"],
            },
        ),
        migrations.AddConstraint(
            model_name="shift",
            constraint=models.CheckConstraint(
                check=models.Q(("start_time__lt", models.F("end_time"))), name="Positive Duration Constraint"
            ),
        ),
        migrations.AddField(
            model_name="equipment",
            name="shifts",
            field=sortedm2m.fields.SortedManyToManyField(
                blank=True, help_text=None, related_name="equipment", to="equipment.shift"
            ),
        ),
    ]
