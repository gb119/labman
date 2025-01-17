# -*- coding: utf-8 -*-
"""
Created on Sun Aug  6 16:31:16 2023

@author: phygbu
"""
# Python imports
from os.path import basename, dirname

# Django imports
from django.urls import path, register_converter

# app imports
from . import views


class FloatUrlParameterConverter:
    regex = r"[0-9]+\.?[0-9]+"

    def to_python(self, value):
        return float(value)

    def to_url(self, value):
        return str(value)


app_name = basename(dirname(__file__))

register_converter(FloatUrlParameterConverter, "float")

urlpatterns = [
    path("photo_tag/<slug:slug>/", views.PhotoDisplay.as_view(), name="photo_tag"),
    path("new_document/equipment/<int:equipment>/", views.DocumentDIalog.as_view(), name="new_equipment_document"),
    path(
        "edit_document/equipment/<int:equipment>/<int:pk>/",
        views.DocumentDIalog.as_view(),
        name="edit_equipment_document",
    ),
]
