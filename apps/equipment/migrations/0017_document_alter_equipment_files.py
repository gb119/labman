# Generated by Django 4.2.3 on 2023-07-18 11:08

# Django imports
from django.db import migrations, models

# external imports
import django_simple_file_handler.models
import sortedm2m.fields


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0016_userlistentry_admin_gold_userlistentry_hold"),
    ]

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True, verbose_name="last updated")),
                ("generated_name", models.CharField(blank=True, max_length=255, null=True)),
                ("extra_text", models.TextField(blank=True, verbose_name="extra text (optional)")),
                (
                    "saved_file",
                    models.FileField(
                        max_length=255,
                        upload_to=django_simple_file_handler.models.create_file_path,
                        verbose_name="uploaded file",
                    ),
                ),
                ("title", models.CharField(max_length=245, unique=True)),
                ("version", models.IntegerField(default=0)),
                (
                    "catagory",
                    models.CharField(
                        choices=[
                            ("ra", "Risk Assessment"),
                            ("sop", "Standard Operator Procedure"),
                            ("manual", "Manual/Instructions"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=20,
                    ),
                ),
            ],
            options={
                "verbose_name": "document (categorized)",
                "verbose_name_plural": "documents (categorized)",
            },
        ),
        migrations.AlterField(
            model_name="equipment",
            name="files",
            field=sortedm2m.fields.SortedManyToManyField(
                blank=True, help_text=None, related_name="equipment", to="equipment.document"
            ),
        ),
    ]
