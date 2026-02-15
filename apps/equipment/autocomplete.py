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
        
        if matching_locations.exists():
            # Build Q objects for each location tree (uses MPTT indexed fields)
            location_conditions = []
            for loc in matching_locations:
                # Use MPTT tree fields for efficient filtering (single indexed lookup per tree)
                location_conditions.append(
                    Q(location__tree_id=loc.tree_id, location__lft__gte=loc.lft, location__rght__lte=loc.rght)
                )
            
            # Combine all location conditions with OR
            if location_conditions:
                conditions.append(reduce(operator.or_, location_conditions))
        
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
