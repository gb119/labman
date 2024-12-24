# Python imports
"""URL patterns for the equipment app."""
# Python imports
from os.path import basename, dirname

# Django imports
from django.urls import path

# app imports
from . import views

app_name = basename(dirname(__file__))


urlpatterns = [
    path("sign-off/<int:equipment>/", views.SignOffFormSetView.as_view(), name="sign-off"),
    path("equipment_detail/<int:pk>/", views.EquipmentDetailView.as_view(), name="equipment_detail"),
]
