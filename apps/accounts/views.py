#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Views for the accounts apps."""
# Django imports
from django import views

# external imports
from htmx_views.views import HTMXProcessMixin
from labman_utils.views import IsAuthenticaedViewMixin

# app imports
from .models import Account


# Create your views here.
class MyAccountView(IsAuthenticaedViewMixin, HTMXProcessMixin, views.generic.DetailView):
    """A template detail view that gets the current logged in user."""

    context_object_name = "account"
    template_name = "accounts/myaccount.html"
    template_name_projecttab = "accounts/parts/myaccount_projects.html"
    template_name_underlingstab = "accounts/parts/myaccount_underlings.html"
    template_name_userlisttab = "accounts/parts/myaccount_userlist.html"

    def get_object(self, queryset=None):
        """Always return the current logged in user."""
        return self.request.user


class UserAccountView(IsAuthenticaedViewMixin, views.generic.DetailView):
    """A template detail view that gets a specific user."""

    context_object_name = "account"
    template_name = "accounts/user_account.html"
    slug_field = "username"
    slug_url_kwarg = "username"
    model = Account
