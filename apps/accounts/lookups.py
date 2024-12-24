#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide restframework look ups of accounts app models."""

# Django imports
from django.core.exceptions import PermissionDenied
from django.db.models import Q

# external imports
from ajax_select import LookupChannel, register
from dal import autocomplete

# app imports
from .models import Account, ResearchGroup


@register("groups")
class ResearchGroupLookup(LookupChannel):
    """Lookup for the ResearchGroup model by name or code."""

    model = ResearchGroup

    def get_query(self, querystring, request):
        """Lookup entry by code of name."""
        code = Q(code__istartswith=querystring)
        name = Q(name__istartswith=querystring)
        return self.model.objects.filter(code | name)

    def format_item_display(self, obj):
        """Output function to format by name."""
        return obj.name

    def format_match(self, obj):
        """Output by name."""
        return obj.name

    def check_auth(self, request):
        """Require a logged in user."""
        if not request.user.is_authenticated:
            raise PermissionDenied


@register("account")
class AccountLookup(LookupChannel):
    """Lookup Account models by name or username or email."""

    model = Account

    def get_query(self, querystring, request):
        """Do the lookup by filtering on first_name, last_name, email and username."""
        username = Q(username__istartswith=querystring)
        name = Q(first_name__istartswith=querystring) | Q(last_name__istartswith=querystring)
        email = Q(email__istartswith=querystring)
        return self.model.objects.filter(username | name | email)

    def format_item_display(self, obj):
        """Output is always the display_name property."""
        return obj.display_name

    def format_match(self, obj):
        """Output is always the display_name property."""
        return obj.display_name

    def check_auth(self, request):
        """Require a logged in user."""
        if not request.user.is_authenticated:
            raise PermissionDenied


class UserAutocomplete(autocomplete.Select2QuerySetView):
    """Lookup the user for the given equipment."""

    def get_queryset(self):
        """Lookup up the equipment parameter and then start filtering on name, email or username."""
        if not self.request.user.is_authenticated:
            return Account.objects.none()

        equipment = self.forwarded.get("equipment", None)

        if equipment is None or equipment == "":
            return Account.objects.none()

        queryset = Account.objects.filter(user_of__equipment=equipment)

        if self.q:
            username = Q(username__istartswith=self.q)
            name = Q(first_name__istartswith=self.q) | Q(last_name__istartswith=self.q)
            email = Q(email__istartswith=self.q)
            queryset = queryset.filter(username | name | email)

        return queryset
