# Generated manually for CostCentre MPTT migration

from django.db import migrations, models
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        ("costings", "0007_costrate_costcentre_rate"),
    ]

    operations = [
        # First, remove the old custom level field
        migrations.RemoveField(
            model_name="costcentre",
            name="level",
        ),
        # Add MPTT fields
        migrations.AddField(
            model_name="costcentre",
            name="lft",
            field=models.PositiveIntegerField(default=0, editable=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="costcentre",
            name="rght",
            field=models.PositiveIntegerField(default=0, editable=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="costcentre",
            name="tree_id",
            field=models.PositiveIntegerField(db_index=True, default=0, editable=False),
            preserve_default=False,
        ),
        # Add new MPTT-managed level field (non-nullable PositiveIntegerField)
        migrations.AddField(
            model_name="costcentre",
            name="level",
            field=models.PositiveIntegerField(default=0, editable=False),
            preserve_default=False,
        ),
        # Add parent field (TreeForeignKey)
        migrations.AddField(
            model_name="costcentre",
            name="parent",
            field=mptt.fields.TreeForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="costings.costcentre",
            ),
        ),
        # Add index on MPTT fields
        migrations.AlterIndexTogether(
            name="costcentre",
            index_together={("tree_id", "lft")},
        ),
        # Change ordering to tree-based
        migrations.AlterModelOptions(
            name="costcentre",
            options={"ordering": ["tree_id", "lft"]},
        ),
    ]
