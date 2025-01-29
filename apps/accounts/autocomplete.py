# -*- coding: utf-8 -*-
"""HTMX Autocomplete classes for people."""

# Python imports
import operator
from functools import reduce

# Django imports
from django.db.models import Q

# external imports
from autocomplete import ModelAutocomplete, QuerysetMappedIterable
from equipment.models import UserListEntry

# app imports
from .models import Account, Project


class UserListAutoComplete(ModelAutocomplete):
    """An Autocomplete class for Accounts that are users of a piece of equipment.

    The Equipment item must be in a field called equipment in the form."""

    model = Account
    search_attrs = ["first_name", "last_name", "username"]

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        base_qs = cls.get_queryset()
        if equipment := context.request.GET.get("equipment", None):
            try:
                equipment = int(equipment)
                entries = UserListEntry.objects.filter(hold=False, admin_hold=False, equipment__pk=equipment)
                base_qs = base_qs.filter(Q(user_of__in=entries) | Q(username="service"))
            except (ValueError, TypeError):
                pass
        conditions = [Q(**{f"{attr}__icontains": search}) for attr in cls.get_search_attrs()]
        condition_filter = reduce(operator.or_, conditions)
        queryset = base_qs.filter(condition_filter)
        return queryset


class AllUsersComplete(ModelAutocomplete):
    """An Autocomplete class for Accounts that are users of a piece of equipment.

    The Equipment item must be in a field called equipment in the form."""

    model = Account
    search_attrs = ["first_name", "last_name", "username"]


class ProjectsAutocomplete(ModelAutocomplete):
    """An Autocomplete class for Project objects - searching by Project name, code and description."""

    model = Project
    search_attrs = ["name", "short_name", "code", "description"]
