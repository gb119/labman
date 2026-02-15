# Generated manually - Remove deprecated code field from Location model

from django.db import migrations
import mptt.fields
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0014_remove_location_location_field"),
    ]

    operations = [
        # Remove the unique constraint on code field
        migrations.RemoveConstraint(
            model_name="location",
            name="Unique Location Code",
        ),
        # Remove the code field - it's been replaced by MPTT hierarchy
        migrations.RemoveField(
            model_name="location",
            name="code",
        ),
        # Update the parent field to change related_name from "children" to "direct_children"
        # This avoids conflicts with the children property that returns all descendants
        migrations.AlterField(
            model_name="location",
            name="parent",
            field=mptt.fields.TreeForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="direct_children",
                to="equipment.location",
            ),
        ),
    ]
