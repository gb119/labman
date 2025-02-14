# -*- coding: utf-8 -*-
"""A Form Field for obfuscating submitted data to stop tripping the WAF."""
# Python imports

# Django imports
from django import forms
from django.apps import apps
from django.contrib.flatpages.models import FlatPage
from django.utils.text import slugify

# external imports
from photologue.models import Photo
from sortedm2m.forms import (
    SortedCheckboxSelectMultiple,
    SortedMultipleChoiceField,
)

# app imports
from .fields import ObfuscatedCharField
from .widgets import ObfuscatedTinyMCE

Equipment = apps.get_model(app_label="equipment", model_name="equipment")
Location = apps.get_model(app_label="equipment", model_name="location")
Account = apps.get_model(app_label="accounts", model_name="account")
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


class PhotoDialogForm(forms.ModelForm):
    """Form for adding a document to a location of item of equipment."""

    equipment = forms.ModelChoiceField(queryset=Equipment.objects.all(), required=False, widget=forms.HiddenInput())
    location = forms.ModelChoiceField(queryset=Location.objects.all(), required=False, widget=forms.HiddenInput())
    account = forms.ModelChoiceField(queryset=Account.objects.all(), required=False, widget=forms.HiddenInput())

    class Meta:
        model = Photo
        fields = ["image", "title", "caption", "slug", "id"]
        widgets = {"slug": forms.HiddenInput(), "id": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False

    def clean(self):
        """Ensure slug is set in the cleaned_data."""
        cleaned_data = super().clean()
        for fld in ["equipment", "location", "account"]:
            if not cleaned_data.get("title", None) and cleaned_data[fld]:
                cleaned_data["title"] = cleaned_data[fld]
            if not cleaned_data.get("slug", None) and cleaned_data[fld]:
                cleaned_data["slug"] = slugify(cleaned_data[fld].name)
        if not cleaned_data.get("slug", None):
            cleaned_data["slug"] = None  # This will trigger the object save properly.
        return cleaned_data


class PhotoLinksForm(forms.ModelForm):
    """A form to manage lihking documents."""

    class Meta:
        model = Photo
        fields = ["id"]
        widgets = {"id": forms.HiddenInput()}

    equipment = SortedCheckboxMultipleChoiceField(Equipment.objects.all().order_by("category", "name"), required=False)
    location = SortedCheckboxMultipleChoiceField(Location.objects.all().order_by("location", "name"), required=False)


class FlatPageForm(forms.ModelForm):
    """A form for editing flatpages on the site."""

    class Meta:
        model = FlatPage
        fields = ["title", "url", "content", "id"]
        widgets = {"content": ObfuscatedTinyMCE(), "id": forms.HiddenInput()}
        field_classes = {"content": ObfuscatedCharField}

    equipment = forms.ModelChoiceField(queryset=Equipment.objects.all(), required=False, widget=forms.HiddenInput())
    location = forms.ModelChoiceField(queryset=Location.objects.all(), required=False, widget=forms.HiddenInput())


class FlatPagesLinksForm(forms.ModelForm):
    """A form to manage lihking documents."""

    class Meta:
        model = FlatPage
        fields = ["id"]
        widgets = {"id": forms.HiddenInput()}

    equipment = SortedCheckboxMultipleChoiceField(Equipment.objects.all().order_by("category", "name"), required=False)
    location = SortedCheckboxMultipleChoiceField(Location.objects.all().order_by("location", "name"), required=False)
