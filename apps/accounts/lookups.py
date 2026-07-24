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
    """Lookup for the ResearchGroup model by name or code.

    Examples:
        Inspect the public interface in an interactive session::

            >>> ResearchGroupLookup.__name__
            'ResearchGroupLookup'

    """

    model = ResearchGroup

    def get_query(self, querystring, request):
        """Lookup entry by code of name.

        Args:
            querystring (object):
                Value supplied for ``querystring``.
            request (object):
                Value supplied for ``request``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(ResearchGroupLookup.get_query)
                True

        """
        code = Q(code__istartswith=querystring)
        name = Q(name__istartswith=querystring)
        return self.model.objects.filter(code | name)

    def format_item_display(self, obj):
        """Output function to format by name.

        Args:
            obj (object):
                Value supplied for ``obj``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(ResearchGroupLookup.format_item_display)
                True

        """
        return obj.name

    def format_match(self, obj):
        """Output by name.

        Args:
            obj (object):
                Value supplied for ``obj``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(ResearchGroupLookup.format_match)
                True

        """
        return obj.name

    def check_auth(self, request):
        """Require a logged in user.

        Args:
            request (object):
                Value supplied for ``request``.

        Raises:
            PermissionDenied:
                If the request does not belong to an authenticated user.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(ResearchGroupLookup.check_auth)
                True

        """
        if not request.user.is_authenticated:
            raise PermissionDenied


@register("account")
class AccountLookup(LookupChannel):
    """Lookup Account models by name or username or email.

    Examples:
        Inspect the public interface in an interactive session::

            >>> AccountLookup.__name__
            'AccountLookup'

    """

    model = Account

    def get_query(self, querystring, request):
        """Do the lookup by filtering on first_name, last_name, email and username.

        Args:
            querystring (object):
                Value supplied for ``querystring``.
            request (object):
                Value supplied for ``request``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(AccountLookup.get_query)
                True

        """
        username = Q(username__istartswith=querystring)
        name = Q(first_name__istartswith=querystring) | Q(last_name__istartswith=querystring)
        email = Q(email__istartswith=querystring)
        return self.model.objects.filter(username | name | email)

    def format_item_display(self, obj):
        """Output is always the display_name property.

        Args:
            obj (object):
                Value supplied for ``obj``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(AccountLookup.format_item_display)
                True

        """
        return obj.display_name

    def format_match(self, obj):
        """Output is always the display_name property.

        Args:
            obj (object):
                Value supplied for ``obj``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(AccountLookup.format_match)
                True

        """
        return obj.display_name

    def check_auth(self, request):
        """Require a logged in user.

        Args:
            request (object):
                Value supplied for ``request``.

        Raises:
            PermissionDenied:
                If the request does not belong to an authenticated user.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(AccountLookup.check_auth)
                True

        """
        if not request.user.is_authenticated:
            raise PermissionDenied


class UserAutocomplete(autocomplete.Select2QuerySetView):
    """Lookup the user for the given equipment.

    Examples:
        Inspect the public interface in an interactive session::

            >>> UserAutocomplete.__name__
            'UserAutocomplete'

    """

    def get_queryset(self):
        """Lookup up the equipment parameter and then start filtering on name, email or username.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(UserAutocomplete.get_queryset)
                True

        """
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
