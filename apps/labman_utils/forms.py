# -*- coding: utf-8 -*-
"""A Form Field for obfuscating submitted data to stop tripping the WAF."""
# Python imports

# Django imports
from django import forms
from django.apps import apps

# external imports
from sortedm2m.forms import (
    SortedCheckboxSelectMultiple,
    SortedMultipleChoiceField,
)

Equipment = apps.get_model(app_label="equipment", model_name="equipment")
Location = apps.get_model(app_label="equipment", model_name="location")
Document = apps.get_model(app_label="labman_utils", model_name="document")


class SortedCheckboxMultipleChoiceField(SortedMultipleChoiceField):
    widget = SortedCheckboxSelectMultiple


class DateTimeCustomInput(forms.DateTimeInput):
    """JTML5 DatetimePicker Widget"""

    input_type = "datetime-local"


class DateCustomInput(forms.DateInput):
    """JTML5 DatePicker Widget"""

    input_type = "date"


class TimeCustomInput(forms.TimeInput):
    """JTML5 TimePicker Widget"""

    input_type = "time"


class DocumentDialogForm(forms.ModelForm):
    """Form for adding a document to a location of item of equipment."""

    equipment = forms.ModelChoiceField(queryset=Equipment.objects.all(), required=False, widget=forms.HiddenInput())
    location = forms.ModelChoiceField(queryset=Location.objects.all(), required=False, widget=forms.HiddenInput())

    class Meta:
        model = Document
        fields = ["title", "extra_text", "category", "version", "review_date", "saved_file"]
        widgets = {"review_date": DateCustomInput()}

    class Media:
        js: ["/static/bootstrap_datepick_plus/js/datepicker-widget.js"]


class DocumentLinksForm(forms.ModelForm):
    """A form to manage lihking documents."""

    class Meta:
        model = Document
        fields = ["id"]
        widgets = {"id": forms.HiddenInput()}

    equipment = SortedCheckboxMultipleChoiceField(Equipment.objects.all().order_by("category", "name"), required=False)
    location = SortedCheckboxMultipleChoiceField(Location.objects.all().order_by("location", "name"), required=False)
