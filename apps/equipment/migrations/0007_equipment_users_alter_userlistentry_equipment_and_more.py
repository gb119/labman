# Generated by Django 4.2.18 on 2025-02-04 17:11

# Django imports
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("equipment", "0006_alter_equipment_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipment",
            name="users",
            field=models.ManyToManyField(
                related_name="user_of",
                through="equipment.UserListEntry",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="userlistentry",
            name="equipment",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="userlist",
                to="equipment.equipment",
            ),
        ),
        migrations.AlterField(
            model_name="userlistentry",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="equipmentlist",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
