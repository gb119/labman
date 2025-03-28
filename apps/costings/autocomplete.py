# -*- coding: utf-8 -*-
"""HTMX Autocomplete classes for people."""

# external imports
from autocomplete import ModelAutocomplete

# app imports
from .models import CostCentre


class CostCentreAutocomplete(ModelAutocomplete):
    """An Autocomplete class for CostCentre objects - searching by CostCentre name, code and description."""

    model = CostCentre
    search_attrs = ["name", "short_name", "account_code", "description"]
