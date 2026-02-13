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
    path("new_document/equipment/<int:equipment>/", views.DocumentDialog.as_view(), name="new_equipment_document"),
    path(
        "edit_document/equipment/<int:equipment>/<int:pk>/",
        views.DocumentDialog.as_view(),
        name="edit_equipment_document",
    ),
    path("new_document/location/<int:location>/", views.DocumentDialog.as_view(), name="new_location_document"),
    path(
        "edit_document/location/<int:location>/<int:pk>/",
        views.DocumentDialog.as_view(),
        name="edit_location_document",
    ),
    path("edit_document/<int:pk>/", views.DocumentDialog.as_view(), name="edit_document"),
    path("new_document/", views.DocumentDialog.as_view(), name="new_document"),
    path(
        "link_documents/equipment/<int:equipment>/",
        views.DocumentLinkDialog.as_view(),
        name="link_document_equipment",
    ),
    path("link_documents/location/<int:location>/", views.DocumentLinkDialog.as_view(), name="link_document_location"),
    path("link_document/<int:pk>/", views.DocumentLinkDialog.as_view(), name="link_document"),
    path("new_photo/equipment/<int:equipment>/", views.PhotoDialog.as_view(), name="new_equipment_photo"),
    path(
        "edit_photo/equipment/<int:equipment>/<int:pk>/",
        views.PhotoDialog.as_view(),
        name="edit_equipment_photo",
    ),
    path("new_photo/location/<int:location>/", views.PhotoDialog.as_view(), name="new_location_photo"),
    path(
        "edit_photo/location/<int:location>/<int:pk>/",
        views.PhotoDialog.as_view(),
        name="edit_location_photo",
    ),
    path("new_photo/account/<int:account>/", views.PhotoDialog.as_view(), name="new_account_photo"),
    path(
        "edit_photo/account/<int:account>/<int:pk>/",
        views.PhotoDialog.as_view(),
        name="edit_account_photo",
    ),
    path("edit_photo/<int:pk>/", views.PhotoDialog.as_view(), name="edit_photo"),
    path("new_photo/", views.PhotoDialog.as_view(), name="new_photo"),
    path(
        "link_photos/equipment/<int:equipment>/",
        views.PhotoLinkDialog.as_view(),
        name="link_photo_equipment",
    ),
    path("link_photos/location/<int:location>/", views.PhotoLinkDialog.as_view(), name="link_photo_location"),
    path("link_photo/<int:pk>/", views.PhotoLinkDialog.as_view(), name="link_photo"),
    path("new_flatpage/equipment/<int:equipment>/", views.FlatPageDialog.as_view(), name="new_equipment_flatpage"),
    path(
        "edit_flatpage/equipment/<int:equipment>/<int:pk>/",
        views.FlatPageDialog.as_view(),
        name="edit_equipment_flatpage",
    ),
    path("new_flatpage/location/<int:location>/", views.FlatPageDialog.as_view(), name="new_location_flatpage"),
    path(
        "edit_flatpage/location/<int:location>/<int:pk>/",
        views.FlatPageDialog.as_view(),
        name="edit_location_flatpage",
    ),
    path("edit_flatpage/<int:pk>/", views.FlatPageDialog.as_view(), name="edit_flatpage"),
    path("new_flatpage/", views.FlatPageDialog.as_view(), name="new_flatpage"),
    path(
        "link_flatpages/equipment/<int:equipment>/",
        views.FlatPageLinkDialog.as_view(),
        name="link_flatpage_equipment",
    ),
    path("link_flatpages/location/<int:location>/", views.FlatPageLinkDialog.as_view(), name="link_flatpage_location"),
    path("link_flatpage/<int:pk>/", views.FlatPageLinkDialog.as_view(), name="link_flatpage"),
]
