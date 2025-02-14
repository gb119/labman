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
        locations = Location.objects.filter(name__icontains=search).values("code").distinct()
        locations_conditions = [Q(location__code__startswith=x["code"]) for x in locations.all()]
        conditions.extend(locations_conditions)
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
