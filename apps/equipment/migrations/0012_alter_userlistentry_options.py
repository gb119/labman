# Generated by Django 4.2.2 on 2023-06-25 22:33

# Django imports
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0011_equipment_policies"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="userlistentry",
            options={
                "ordering": ["equipment", "-role", "user"],
                "verbose_name": "User List Entry",
                "verbose_name_plural": "User List Entries",
            },
        ),
    ]
