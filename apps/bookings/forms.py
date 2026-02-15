# -*- coding: utf-8 -*-
"""Bookings forms module.

This module provides Django form classes for managing equipment bookings,
including booking entry forms, filtering forms, and custom widgets for
date-time range selection.
"""
# Django imports
from django import forms
from django.contrib.auth.models import Group
from django.contrib.postgres.forms import RangeWidget

# external imports
from accounts.autocomplete import AllUsersComplete, UserListAutoComplete
from accounts.models import Account
from autocomplete import AutocompleteWidget
from costings.autocomplete import CostCentreAutocomplete
from costings.models import CostCentre
from equipment.autocomplete import EquipmentAutocomplete
from equipment.models import Equipment
from labman_utils.forms import DateCustomInput, DateTimeCustomInput

# app imports
from .models import BookingEntry


class CustomSlotWidget(RangeWidget):
    """A custom widget for entering booking time slots using date-time pickers.

    This widget extends Django's RangeWidget to provide two Bootstrap
    DateTimePickers for entering start and end times of booking slots.
    It handles the decomposition of datetime ranges into separate date
    and time components for display.

    Attributes:
        input_type (str): The HTML input type, inherited from DateTimeCustomInput.
    """

    input_type = DateTimeCustomInput.input_type

    def __init__(self, *args, **kargs):
        """Construct the widget with custom date-time input sub-widgets.

        This constructor ensures that the widget uses DateTimeCustomInput
        widgets for both the start and end of the range, even if different
        widgets are specified.

        Args:
            *args: Variable length argument list, first argument should be
                a widget class for the sub-widgets.
            **kargs: Arbitrary keyword arguments passed to parent class.
        """
        if len(args) < 1:
            args = (DateTimeCustomInput,)
        if not issubclass(args[0], DateTimeCustomInput):
            args = list(args)
            args[0] = DateTimeCustomInput
        super().__init__(*args, **kargs)

    def decompress(self, value):
        """Convert a date-time range to separate date and time components.

        This method decomposes a datetime range into a format suitable for
        display in the two DateTimePickers, splitting each datetime into
        separate date and time values.

        Args:
            value: A datetime range object with lower and upper bounds, or None.

        Returns:
            (list): A list containing two sublists, each with [date, time]
                for the start and end of the range. Returns [[None, None],
                [None, None]] if value is None or empty.
        """
        if value:
            start, end = value.lower, value.upper
            return ([start.date(), start.time()], [end.date(), end.time()])
        return [[None, None], [None, None]]


class BookingEntryAdminForm(forms.ModelForm):
    """A form for editing booking slots in the Django admin interface.

    This ModelForm provides a comprehensive interface for administrators to
    manage booking entries, including all fields from the BookingEntry model.
    It uses the CustomSlotWidget for entering the time slot range and includes
    necessary JavaScript and CSS resources for the date-time pickers.

    Attributes:
        Meta.model (BookingEntry): The model class for this form.
        Meta.exclude (list): Fields excluded from the form (empty list, all
            fields included).
        Meta.widgets (dict): Custom widgets for form fields, specifically the
            CustomSlotWidget for the slot field.
        Media.js (list): JavaScript files required for the form functionality,
            including jQuery and jQuery UI.
        Media.css (dict): CSS files required for styling the date-time pickers.
    """

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
    """A form for creating and editing booking entries in the front-end interface.

    This ModelForm provides a user-friendly interface for managing bookings
    directly from the front-end application. It includes autocomplete for
    user selection and uses the CustomSlotWidget for time slot entry. The
    equipment and ID fields are hidden as they are typically pre-populated.

    Attributes:
        Meta.model (BookingEntry): The model class for this form.
        Meta.fields (list): Fields included in the form (equipment, id, user,
            booker, slot, cost_centre).
        Meta.widgets (dict): Custom widgets for form fields, including
            autocomplete for user selection, hidden fields for equipment and
            id, and CustomSlotWidget for the time slot.
    """

    class Meta:
        model = BookingEntry
        fields = ["equipment", "id", "user", "booker", "slot", "cost_centre"]
        widgets = {
            "user": AutocompleteWidget(ac_class=UserListAutoComplete),
            "equipment": forms.HiddenInput(),
            "id": forms.HiddenInput(),
            "slot": CustomSlotWidget(),
        }


class BookingEntryFilterForm(forms.Form):
    """A form for filtering and reporting on booking entries.

    This form provides comprehensive filtering and output options for booking
    entry reports. Users can filter by date range, users, equipment, user groups,
    and cost centres, with options to control the ordering and output format of results.
    Multiple selection is supported for user, equipment, user_group, and cost centre fields
    using autocomplete widgets.

    Attributes:
        from_date (forms.DateField): The start date for the report period,
            required field with custom date picker.
        to_date (forms.DateField): The end date for the report period,
            required field with custom date picker.
        user (forms.ModelMultipleChoiceField): Optional filter for specific
            users, supports multiple selection with autocomplete.
        user_group (forms.ModelMultipleChoiceField): Optional filter for specific
            user groups, supports multiple selection.
        equipment (forms.ModelMultipleChoiceField): Optional filter for
            specific equipment, supports multiple selection with autocomplete.
        cost_centre (forms.ModelMultipleChoiceField): Optional filter for
            specific cost centres, supports multiple selection with autocomplete.
        order (forms.ChoiceField): Selection of grouping and sub-totalling
            order for the report, with predefined combinations of user, user_group,
            equipment, and project (cost centre).
        reverse (forms.BooleanField): Optional flag to reverse the order of
            sub-totals in the report.
        output (forms.ChoiceField): Selection of output format, including
            HTML, CSV, Excel, PDF, or raw Excel records.
    """

    from_date = forms.DateField(required=True, widget=DateCustomInput())
    to_date = forms.DateField(required=True, widget=DateCustomInput())
    user = forms.ModelMultipleChoiceField(
        Account.objects.all(),
        required=False,
        widget=AutocompleteWidget(options={"multiselect": True}, ac_class=AllUsersComplete),
    )
    user_group = forms.ModelMultipleChoiceField(
        Group.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-control"}),
    )
    equipment = forms.ModelMultipleChoiceField(
        Equipment.objects.all(),
        required=False,
        widget=AutocompleteWidget(options={"multiselect": True}, ac_class=EquipmentAutocomplete),
    )

    cost_centre = forms.ModelMultipleChoiceField(
        CostCentre.objects.all(),
        required=False,
        widget=AutocompleteWidget(options={"multiselect": True}, ac_class=CostCentreAutocomplete),
    )
    order = forms.ChoiceField(
        choices=[
            ("user,equipment,cost_Centre", "User, Equipment & Project"),
            ("user,cost_centre,equipment", "User, Project & Equipment"),
            ("cost_centre,user,equipment", "Project, User & Equipment"),
            ("user_group,user,equipment", "User Group, User & Equipment"),
            ("user_group,equipment,cost_centre", "User Group, Equipment & Project"),
            ("user,equipment", "User & Equipment"),
            ("user,cost_centre", "User & Project"),
            ("equipment,cost_centre", "Equipment & Project"),
            ("user_group,user", "User Group & User"),
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
