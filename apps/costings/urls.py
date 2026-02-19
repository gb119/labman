#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Account url mapping."""
# Python imports
from os.path import basename, dirname

# Django imports
from django.urls import path

# app imports
from . import views

app_name = basename(dirname(__file__))


urlpatterns = [
    path("lookups/cost_centres/", views.Cost_CentreView.as_view(), name="cost_centre_filter"),
    path("new_cost_centre/", views.CostCentreDialog.as_view(), name="new_cost_centre"),
    path("edit_cost_centre/<int:pk>/", views.CostCentreDialog.as_view(), name="edit_cost_centre"),
]
