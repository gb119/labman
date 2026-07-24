# -*- coding: utf-8 -*-
"""Configure URLs for the HTMX views application."""

# Django imports
from django.urls import path

# app imports
from .views import LinkedSelectEndpointView

app_name = "htmx_views"

urlpatterns = [
    path("select/<str:lookup_channel>/", LinkedSelectEndpointView.as_view(), name="select"),
]
