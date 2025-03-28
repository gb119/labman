#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Account url mapping."""
# Python imports
from os.path import basename, dirname

# Django imports
from django.urls import path

# app imports
from . import lookups, views

app_name = basename(dirname(__file__))


urlpatterns = [
    path("me/", views.MyAccountView.as_view(), name="my_account"),
    path("user/<str:username>/", views.UserAccountView.as_view(), name="user_account"),
    path("lookups/userlist/", lookups.UserAutocomplete.as_view(), name="userlist_complete"),
    path("list/collapse_<str:group>/", views.AccountListByGroupView.as_view(), name="list_accounts_by_group"),
]
