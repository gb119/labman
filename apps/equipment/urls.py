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
    path("location_detail/<int:pk>/", views.LocationDetailView.as_view(), name="location_detail"),
    path("lists/", views.ModelListView.as_view(), name="lists"),
    path("userlist/new/<int:equipment>/", views.UserlisttDialog.as_view(), name="userlist_new"),
    path("userlist/edit/<int:equipment>/<int:user>/", views.UserlisttDialog.as_view(), name="userlist_edit"),
    path("equipment/edit/<int:pk>/", views.EquipmentDialog.as_view(), name="edit_equipment"),
    path("account/toggle-active/<int:pk>/", views.ToggleAccountActiveView.as_view(), name="toggle_account_active"),
]
