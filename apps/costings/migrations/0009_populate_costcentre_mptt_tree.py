# Generated manually - Data migration to populate CostCentre MPTT tree structure

from django.db import migrations


def populate_mptt_from_existing_hierarchy(apps, schema_editor):
    """Populate MPTT fields from existing super_cost_centre/code structure."""
    CostCentre = apps.get_model("costings", "CostCentre")
    
    # First, copy super_cost_centre field to parent field
    for cc in CostCentre.objects.all():
        cc.parent = cc.super_cost_centre
        cc.save(update_fields=["parent"])
    
    # Now rebuild the MPTT tree structure
    # Get all root cost centres (no parent)
    roots = CostCentre.objects.filter(parent__isnull=True).order_by("name")
    
    tree_id = 1
    
    def build_tree(cost_centre, tree_id, lft):
        """Recursively build MPTT tree structure."""
        cost_centre.tree_id = tree_id
        cost_centre.lft = lft
        
        # Get children ordered by name
        children = CostCentre.objects.filter(parent=cost_centre).order_by("name")
        
        # Calculate level based on parent
        if cost_centre.parent:
            parent = CostCentre.objects.get(pk=cost_centre.parent.pk)
            cost_centre.level = parent.level + 1
        else:
            cost_centre.level = 0
        
        rght = lft + 1
        
        # Process all children
        for child in children:
            rght = build_tree(child, tree_id, rght)
        
        cost_centre.rght = rght
        cost_centre.save(update_fields=["tree_id", "lft", "rght", "level"])
        
        return rght + 1
    
    # Build tree for each root
    for root in roots:
        # Start each tree with lft=1, return value is unused
        build_tree(root, tree_id, 1)
        tree_id += 1


def reverse_mptt_to_hierarchy(apps, schema_editor):
    """Reverse: copy parent back to super_cost_centre field."""
    CostCentre = apps.get_model("costings", "CostCentre")
    
    for cc in CostCentre.objects.all():
        cc.super_cost_centre = cc.parent
        cc.save(update_fields=["super_cost_centre"])


class Migration(migrations.Migration):

    dependencies = [
        ("costings", "0008_convert_costcentre_to_mptt"),
    ]

    operations = [
        migrations.RunPython(populate_mptt_from_existing_hierarchy, reverse_mptt_to_hierarchy),
    ]
