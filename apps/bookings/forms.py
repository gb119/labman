# -*- coding: utf-8 -*-
"""Bookings related form definitions."""
# Django imports
from django import forms
from django.contrib.postgres.forms import RangeWidget

# external imports
from accounts.autocomplete import (
    AllUsersComplete,
    ProjectsAutocomplete,
    UserListAutoComplete,
)
from accounts.models import Account, Project
from autocomplete import AutocompleteWidget
from equipment.autocomplete import EquipmentAutocomplete
from equipment.models import Equipment
from labman_utils.forms import DateCustomInput, DateTimeCustomInput

# app imports
from .models import BookingEntry


class CustomSlotWidget(RangeWidget):
    """Widget class to provide two Bootstrap DateTimePickers for entering a booking slot."""

    input_type = DateTimeCustomInput.input_type

    def __init__(self, *args, **kargs):
        """Construct the widget, forcing it to use the correct sub-widgets."""
        if len(args) < 1:
            args = (DateTimeCustomInput,)
        if not issubclass(args[0], DateTimeCustomInput):
            args = list(args)
            args[0] = DateTimeCustomInput
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

    class Media:
        js = ["https://code.jquery.com/jquery-3.7.1.min.js", "https://code.jquery.com/ui/1.14.1/jquery-ui.min.js"]
        css = {
            "all": [
                "https://code.jquery.com/ui/1.14.1/themes/smoothness/jquery-ui.css",
                "https://code.jquery.com/ui/1.14.1/themes/base/jquery-ui.css",
            ]
        }


class BookinngDialogForm(forms.ModelForm):
    """A form for editing the booking entries in the front end."""

    class Meta:
        model = BookingEntry
        exclude = ["shifts"]
        widgets = {
            "user": AutocompleteWidget(ac_class=UserListAutoComplete),
            "equipment": forms.HiddenInput(),
            "slot": CustomSlotWidget(),
        }


class BookingEntryFilterForm(forms.Form):
    """A form to filter booking entries for reporting."""

    from_date = forms.DateField(required=True, widget=DateCustomInput())
    to_date = forms.DateField(required=True, widget=DateCustomInput())
    user = forms.ModelMultipleChoiceField(
        Account.objects.all(),
        required=False,
        widget=AutocompleteWidget(options={"multiselect": True}, ac_class=AllUsersComplete),
    )
    equipment = forms.ModelMultipleChoiceField(
        Equipment.objects.all(),
        required=False,
        widget=AutocompleteWidget(options={"multiselect": True}, ac_class=EquipmentAutocomplete),
    )

    project = forms.ModelMultipleChoiceField(
        Project.objects.all(),
        required=False,
        widget=AutocompleteWidget(options={"multiselect": True}, ac_class=ProjectsAutocomplete),
    )
    order = forms.ChoiceField(
        choices=[
            ("user,equipment,project", "User,Equipment & Project"),
            ("user,project,equipment", "User, Project & Equipment"),
            ("project,user,equipment", "Project, User & Equipment"),
            ("user,equipment", "User & Equipment"),
            ("user,project", "User & Project"),
            ("equipment,project", "Equipment & Project"),
        ],
        help_text="Select the levels to sub-total usage",
    )
    reverse = forms.BooleanField(help_text="Reverse the order for subtotals", required=False)
    output = forms.ChoiceField(
        choices=[
            ("html", "Web page"),
            ("csv", "CSV File"),
            ("xlsx", "Excel Spreadsheet"),
            ("pdf", "PDF file"),
            ("raw", "Raw records (Excel)"),
        ],
        help_text="Output Format",
    )
