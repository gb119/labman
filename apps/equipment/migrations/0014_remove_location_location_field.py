# Generated manually - Remove legacy location field from Location model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0013_populate_mptt_tree"),
    ]

    operations = [
        # Remove the old self-referential location field
        # The parent field (TreeForeignKey) has replaced it
        migrations.RemoveField(
            model_name="location",
            name="location",
        ),
    ]
