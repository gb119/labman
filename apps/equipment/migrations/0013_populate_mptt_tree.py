# Generated manually - Data migration to populate MPTT tree structure

# Django imports
from django.db import migrations


def populate_mptt_from_existing_hierarchy(apps, schema_editor):
    """Populate MPTT fields from existing location/code structure."""
    Location = apps.get_model("equipment", "Location")

    # First, copy location field to parent field
    for loc in Location.objects.all():
        loc.parent = loc.location
        loc.save(update_fields=["parent"])

    # Now rebuild the MPTT tree structure
    # We need to use raw SQL to call MPTT's rebuild method since we can't
    # access MPTT methods in a migration
    # Instead, we'll manually build the tree structure

    # Get all root locations (no parent)
    roots = Location.objects.filter(parent__isnull=True).order_by("name")

    tree_id = 1

    def build_tree(location, tree_id, lft):
        """Recursively build MPTT tree structure."""
        location.tree_id = tree_id
        location.lft = lft

        # Get children ordered by name
        children = Location.objects.filter(parent=location).order_by("name")

        # Calculate level based on parent
        if location.parent:
            parent = Location.objects.get(pk=location.parent.pk)
            location.level = parent.level + 1
        else:
            location.level = 0

        rght = lft + 1

        # Process all children
        for child in children:
            rght = build_tree(child, tree_id, rght)

        location.rght = rght
        location.save(update_fields=["tree_id", "lft", "rght", "level"])

        return rght + 1

    # Build tree for each root
    for root in roots:
        # Start each tree with lft=1, return value is unused
        build_tree(root, tree_id, 1)
        tree_id += 1


def reverse_mptt_to_hierarchy(apps, schema_editor):
    """Reverse: copy parent back to location field."""
    Location = apps.get_model("equipment", "Location")

    for loc in Location.objects.all():
        loc.location = loc.parent
        loc.save(update_fields=["location"])


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0012_convert_location_to_mptt"),
    ]

    operations = [
        migrations.RunPython(populate_mptt_from_existing_hierarchy, reverse_mptt_to_hierarchy),
    ]
