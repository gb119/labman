#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Views for the accounts app.

This module provides Django class-based views for user account management,
including user profile pages, project listings, and account lists grouped
by user roles. Supports both personal account views and general user browsing.
"""
# Django imports
from django import views
from django.db.backends.postgresql.psycopg_any import DateTimeTZRange
from django.utils import timezone as tz
from django.views.generic import ListView, TemplateView

# external imports
from bookings.forms import BookinngDialogForm
from costings.models import CostCentre  # Hack for now
from htmx_views.views import HTMXProcessMixin
from labman_utils.views import IsAuthenticaedViewMixin

# app imports
from .models import Account


# Create your views here.
class UserAccountView(IsAuthenticaedViewMixin, HTMXProcessMixin, views.generic.DetailView):
    """Template detail view for displaying a specific user's account.

    Provides a comprehensive account detail page with tabbed interface showing
    user projects, underlings (supervised users), equipment user lists, and
    future bookings. Supports HTMX for dynamic tab loading.

    Attributes:
        context_object_name (str): Name for the account object in context.
        template_name (str): Main template for user account display.
        template_name_projecttab (str): Template for projects tab.
        template_name_underlingstab (str): Template for underlings tab.
        template_name_userlisttab (str): Template for user list tab.
        slug_field (str): Model field used for URL slug lookup.
        slug_url_kwarg (str): URL keyword argument for user lookup.
        model: Account model class.
    """

    context_object_name = "account"
    template_name = "accounts/user_account.html"
    template_name_projecttab = "accounts/parts/myaccount_projects.html"
    template_name_underlingstab = "accounts/parts/myaccount_underlings.html"
    template_name_userlisttab = "accounts/parts/myaccount_userlist.html"
    slug_field = "username"
    slug_url_kwarg = "username"
    model = Account

    def get_context_data(self, **kwargs):
        """Build context data including user's future bookings.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary with account and future bookings.
        """
        context = super().get_context_data(**kwargs)
        me = context["account"]
        future = DateTimeTZRange(tz.now(), None)
        context["bookings"] = me.bookings.filter(slot__overlap=future)
        return context


class MyAccountView(UserAccountView):
    """Template detail view for the currently logged-in user's account.

    Extends UserAccountView to always display the current user's account page
    regardless of URL parameters. Provides the same tabbed interface showing
    projects, underlings, user lists, and future bookings.

    Attributes:
        context_object_name (str): Name for the account object in context.
        template_name (str): Main template for user's own account display.
        template_name_projecttab (str): Template for projects tab.
        template_name_underlingstab (str): Template for underlings tab.
        template_name_userlisttab (str): Template for user list tab.
    """

    context_object_name = "account"
    template_name = "accounts/myaccount.html"
    template_name_projecttab = "accounts/parts/myaccount_projects.html"
    template_name_underlingstab = "accounts/parts/myaccount_underlings.html"
    template_name_userlisttab = "accounts/parts/myaccount_userlist.html"

    def get_object(self, queryset=None):
        """Always return the current logged-in user.

        Keyword Parameters:
            queryset (QuerySet or None): Optional queryset (ignored).

        Returns:
            (Account): The currently authenticated user's account.
        """
        return self.request.user

    def get_context_data(self, **kwargs):
        """Build context data including user's future bookings.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary with account and future bookings.
        """
        context = super().get_context_data(**kwargs)
        me = context["account"]
        future = DateTimeTZRange(tz.now(), None)
        context["bookings"] = me.bookings.filter(slot__overlap=future)
        return context


class AccountListByGroupView(IsAuthenticaedViewMixin, ListView):
    """ListView for listing accounts grouped by user role or group.

    Displays a list of user accounts filtered by their group membership,
    such as Academic, Staff, PDRA, PostGrad, Visitor, or Project groups.

    Attributes:
        template_name (str): Template for the account list display.
        model: Account model class.
        context_object_name (str): Name for the account list in context.
    """

    template_name = "accounts/parts/account_list_by_group.html"
    model = Account
    context_object_name = "account_list"

    def get_queryset(self):
        """Get the queryset based on the group name.

        Filters accounts by the group name specified in the URL kwargs.
        Defaults to 'Project' group if not specified.

        Returns:
            (QuerySet): Filtered queryset of accounts in the specified group.
        """
        grp = self.kwargs.get("group", "Project")
        return self.model.objects.filter(groups__name=grp)
