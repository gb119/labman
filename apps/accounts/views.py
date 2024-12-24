#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Views for the accounts apps."""
# Django imports
from django import views

# external imports
from labman_utils.views import IsAuthenticaedViewMixin

# app imports
from .models import Account


# Create your views here.
class MyAccountView(IsAuthenticaedViewMixin, views.generic.DetailView):
    """A template detail view that gets the current logged in user."""

    context_object_name = "account"
    template_name = "accounts/myaccount.html"

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
