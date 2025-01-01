#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Account url mapping."""
# Python imports
from os.path import basename, dirname

# Django imports
from django.urls import path

# app imports
from .views import ItemsView, ToggleView

app_name = basename(dirname(__file__))


urlpatterns = [
    path("<str:ac_name>/items", ItemsView.as_view(), name="items"),
    path("<str:ac_name>/toggle", ToggleView.as_view(), name="toggle"),
]
