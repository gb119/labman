#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Views for the accounts apps."""
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
    """A template detail view that gets a specific user."""

    context_object_name = "account"
    template_name = "accounts/user_account.html"
    template_name_projecttab = "accounts/parts/myaccount_projects.html"
    template_name_underlingstab = "accounts/parts/myaccount_underlings.html"
    template_name_userlisttab = "accounts/parts/myaccount_userlist.html"
    slug_field = "username"
    slug_url_kwarg = "username"
    model = Account

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        me = context["account"]
        future = DateTimeTZRange(tz.now(), None)
        context["bookings"] = me.bookings.filter(slot__overlap=future)
        return context


class MyAccountView(UserAccountView):
    """A template detail view that gets the current logged in user."""

    context_object_name = "account"
    template_name = "accounts/myaccount.html"
    template_name_projecttab = "accounts/parts/myaccount_projects.html"
    template_name_underlingstab = "accounts/parts/myaccount_underlings.html"
    template_name_userlisttab = "accounts/parts/myaccount_userlist.html"

    def get_object(self, queryset=None):
        """Always return the current logged in user."""
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        me = context["account"]
        future = DateTimeTZRange(tz.now(), None)
        context["bookings"] = me.bookings.filter(slot__overlap=future)
        return context


class AccountListByGroupView(IsAuthenticaedViewMixin, ListView):
    """ListView for listing ccounts by group."""

    template_name = "accounts/parts/account_list_by_group.html"
    model = Account
    context_object_name = "account_list"

    def get_queryset(self):
        """Get the queryset based on the groupname."""
        grp = self.kwargs.get("group", "Project")
        return self.model.objects.filter(groups__name=grp)
