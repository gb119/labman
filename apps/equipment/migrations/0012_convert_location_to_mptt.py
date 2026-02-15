# Generated manually for MPTT migration

from django.db import migrations, models
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0011_alter_chargingrate_unique_together_and_more"),
    ]

    operations = [
        # Add MPTT fields
        migrations.AddField(
            model_name="location",
            name="lft",
            field=models.PositiveIntegerField(default=0, editable=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="location",
            name="rght",
            field=models.PositiveIntegerField(default=0, editable=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="location",
            name="tree_id",
            field=models.PositiveIntegerField(db_index=True, default=0, editable=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="location",
            name="level",
            field=models.PositiveIntegerField(default=0, editable=False),
            preserve_default=False,
        ),
        # Add parent field (TreeForeignKey)
        migrations.AddField(
            model_name="location",
            name="parent",
            field=mptt.fields.TreeForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="equipment.location",
            ),
        ),
        # Add index on MPTT fields
        migrations.AlterIndexTogether(
            name="location",
            index_together={("tree_id", "lft")},
        ),
        # Change ordering to tree-based
        migrations.AlterModelOptions(
            name="location",
            options={"ordering": ["tree_id", "lft"]},
        ),
    ]
