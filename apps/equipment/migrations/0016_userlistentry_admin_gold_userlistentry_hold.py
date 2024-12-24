# Generated by Django 4.2.3 on 2023-07-18 09:00

# Django imports
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0015_alter_location_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="userlistentry",
            name="admin_gold",
            field=models.BooleanField(default=False, verbose_name="Management hold"),
        ),
        migrations.AddField(
            model_name="userlistentry",
            name="hold",
            field=models.BooleanField(default=False, verbose_name="User clearable hold"),
        ),
    ]
