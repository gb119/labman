# -*- coding: utf-8 -*-
"""HTMX Autocomplete classes for equipment."""

# Python imports
import operator
from functools import reduce

# Django imports
from django.db.models import Q

# external imports
from autocomplete import ModelAutocomplete, QuerysetMappedIterable

# app imports
from .models import Equipment, Location


class EquipmentAutocomplete(ModelAutocomplete):
    """An Autocomplete class for Equipment objects."""

    model = Equipment

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        base_qs = cls.get_queryset()
        conditions = [Q(**{f"{attr}__icontains": search}) for attr in ["name", "description"]]
        
        # Find locations matching the search
        matching_locations = Location.objects.filter(name__icontains=search)
        
        # For each matching location, get all its descendants
        location_ids = []
        for loc in matching_locations:
            # Include the location itself and all descendants
            location_ids.extend(loc.get_descendants(include_self=True).values_list("id", flat=True))
        
        # Add condition for equipment in any of these locations
        if location_ids:
            conditions.append(Q(location__id__in=location_ids))
        
        condition_filter = reduce(operator.or_, conditions)
        queryset = base_qs.filter(condition_filter)
        return queryset


class LocationAutocomplete(ModelAutocomplete):
    """An Autocomplete class for Equipment objects."""

    model = Location

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        base_qs = cls.get_queryset()
        conditions = [Q(**{f"{attr}__icontains": search}) for attr in ["name", "description"]]
        condition_filter = reduce(operator.or_, conditions)
        queryset = base_qs.filter(condition_filter)
        return queryset
