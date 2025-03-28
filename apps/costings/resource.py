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
    """Import-export resource for CostCentre code objects."""

    class Meta:
        model = CostCentre
        import_id_fields = ["id"]


class CostRateResource(resources.ModelResource):
    """Import-Export admin for CostRates."""

    class Meta:
        model = CostRate
        import_id_fields = ["id"]
