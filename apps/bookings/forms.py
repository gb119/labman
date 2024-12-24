# -*- coding: utf-8 -*-
"""
Bookings related form definitions.
"""
# Django imports
from django import forms
from django.contrib.admin import widgets as admin_widgets
from django.contrib.postgres.forms import DateTimeRangeField, RangeWidget
from django.core.exceptions import ValidationError

# external imports
from bootstrap_datepicker_plus.widgets import DateTimePickerInput
from dal import autocomplete
from dateutil.parser import ParserError, parse
from psycopg2.extras import DateTimeTZRange
from pytz import timezone as tz

# app imports
from .models import BookingEntry


class CustomSlotWidget(RangeWidget):
    """Widget class to provide two Bootstrap DateTimePickers for entering a booking slot."""

    def __init__(self, *args, **kargs):
        """Construct the widget, forcing it to use the correct sub-widgets."""
        if len(args) < 1:
            args = (DateTimePickerInput,)
        if not issubclass(args[0], DateTimePickerInput):
            args = list(args)
            args[0] = DateTimePickerInput
        super().__init__(*args, **kargs)

    def decompress(self, value):
        """Convert the date-time range to a tuple of two lists of date,time."""
        if value:
            start, end = value.lower, value.upper
            return ([start.date(), start.time()], [end.date(), end.time()])
        return [[None, None], [None, None]]


class BookingEntryAdminForm(forms.ModelForm):
    """A form for editing the booking slots in the admin interface."""

    class Meta:
        model = BookingEntry
        exclude = []
        widgets = {
            "slot": CustomSlotWidget(),
        }


class BookinngDialogForm(forms.ModelForm):
    """A form for editing the booking entries in the front end."""

    class Meta:
        model = BookingEntry
        exclude = []
        widgets = {
            "user": autocomplete.ModelSelect2(url="accounts:userlist_complete", forward=["equipment"]),
            "equipment": forms.HiddenInput(),
            "slot": CustomSlotWidget(),
        }
