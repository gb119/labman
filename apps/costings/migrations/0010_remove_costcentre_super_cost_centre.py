# Generated manually - Remove legacy super_cost_centre field from CostCentre model

# Django imports
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("costings", "0009_populate_costcentre_mptt_tree"),
    ]

    operations = [
        # Remove the old self-referential super_cost_centre field
        # The parent field (TreeForeignKey) has replaced it
        migrations.RemoveField(
            model_name="costcentre",
            name="super_cost_centre",
        ),
    ]
