# -*- coding: utf-8 -*-
"""URL mapping for the bookings app."""
# Python imports
from os.path import basename, dirname

# Django imports
from django.urls import path, register_converter

# app imports
from . import views

app_name = basename(dirname(__file__))


class FloatUrlParameterConverter:
    """Allows paths to capture floats in urls."""

    regex = r"[0-9]+\.?[0-9]+"

    def to_python(self, value):
        """Convert string to floating point value."""
        return float(value)

    def to_url(self, value):
        """Convert the float to a string."""
        return str(value)


register_converter(FloatUrlParameterConverter, "float")


urlpatterns = [
    path("cal/<int:equipment>/<int:date>/", views.CalendarView.as_view(), name="equipment_calendar"),
    path("cal/all/<int:date>/", views.AllCalendarView.as_view(), name="all_equipment_calendar"),
    path("cal/all/", views.AllCalendarView.as_view(), name="all_equipment_calendar"),
    path("book/<int:equipment>/<float:ts>/", views.BookingDialog.as_view(), name="equipment_booking"),
]
