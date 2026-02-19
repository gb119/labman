# -*- coding: utf-8 -*-
"""Resources for the account app."""
# Python imports
import re

# Django imports
from django.contrib.auth.models import Group

# external imports
from import_export import fields, resources, widgets

# app imports
from .models import CostCentre, CostRate


class CostCentreResource(resources.ModelResource):
    """Import-export resource for CostCentre code objects.

    Uses name as the primary import/export identifier. The code field is
    maintained for backwards compatibility during migration.
    """

    parent = fields.Field(
        column_name="parent",
        attribute="parent",
        widget=widgets.ForeignKeyWidget(CostCentre, "name"),
    )

    class Meta:
        model = CostCentre
        import_id_fields = ["name"]
        # Exclude MPTT fields - they are auto-managed by django-mptt
        # Note: 'rght' is the correct field name (abbreviation of 'right')
        exclude = ["lft", "rght", "tree_id", "level"]


class CostRateResource(resources.ModelResource):
    """Import-Export admin for CostRates."""

    class Meta:
        model = CostRate
        import_id_fields = ["id"]
