# -*- coding: utf-8 -*-
"""Django forms for managing documents, photos, and content with obfuscation support.

This module provides form classes for handling various content types including documents,
photos, and flat pages. It includes support for obfuscated data transmission to bypass
web application firewall restrictions whilst maintaining data security. The forms integrate
with equipment, location, and account models to enable proper content association and
management.
"""
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
    """A multiple choice field with sorted checkboxes for user selection.

    This field extends SortedMultipleChoiceField to use checkbox widgets whilst maintaining
    the sorting functionality for choice options.

    Attributes:
        widget (SortedCheckboxSelectMultiple):
            The widget used to render the field as sorted checkboxes.
    """

    widget = SortedCheckboxSelectMultiple


class DateTimeCustomInput(forms.DateTimeInput):
    """HTML5 datetime-local input widget for date and time selection.

    Attributes:
        input_type (str):
            Set to 'datetime-local' to use the HTML5 datetime picker.
    """

    input_type = "datetime-local"


class DateCustomInput(forms.DateInput):
    """HTML5 date input widget for date selection.

    Attributes:
        input_type (str):
            Set to 'date' to use the HTML5 date picker.
    """

    input_type = "date"


class TimeCustomInput(forms.TimeInput):
    """HTML5 time input widget for time selection.

    Attributes:
        input_type (str):
            Set to 'time' to use the HTML5 time picker.
    """

    input_type = "time"


class DocumentDialogForm(forms.ModelForm):
    """Form for creating and editing documents associated with equipment or locations.

    This form allows users to add or modify document information including title,
    description, category, version, review date, and the file itself. The form can
    be associated with either an equipment item or a location through hidden fields.

    Attributes:
        equipment (forms.ModelChoiceField):
            Hidden field for associating the document with an equipment item.
        location (forms.ModelChoiceField):
            Hidden field for associating the document with a location.
    """

    equipment = forms.ModelChoiceField(queryset=Equipment.objects.all(), required=False, widget=forms.HiddenInput())
    location = forms.ModelChoiceField(queryset=Location.objects.all(), required=False, widget=forms.HiddenInput())

    class Meta:
        model = Document
        fields = ["title", "extra_text", "category", "version", "review_date", "saved_file"]
        widgets = {"review_date": DateCustomInput()}

    class Media:
        js: ["/static/bootstrap_datepick_plus/js/datepicker-widget.js"]


class DocumentLinksForm(forms.ModelForm):
    """Form for managing associations between documents and equipment or locations.

    This form provides an interface for linking existing documents to multiple equipment
    items and locations using sorted checkbox selection fields.

    Attributes:
        equipment (SortedCheckboxMultipleChoiceField):
            Field for selecting multiple equipment items to link to the document.
        location (SortedCheckboxMultipleChoiceField):
            Field for selecting multiple locations to link to the document.
    """

    class Meta:
        model = Document
        fields = ["id"]
        widgets = {"id": forms.HiddenInput()}

    equipment = SortedCheckboxMultipleChoiceField(Equipment.objects.all().order_by("category", "name"), required=False)
    location = SortedCheckboxMultipleChoiceField(
        Location.objects.all().order_by("tree_id", "lft", "name"), required=False
    )


class PhotoDialogForm(forms.ModelForm):
    """Form for uploading and editing photos associated with equipment, locations, or accounts.

    This form handles photo uploads and metadata including title, caption, and slug.
    The slug is automatically generated if not provided, based on the associated entity's
    name.

    Attributes:
        equipment (forms.ModelChoiceField):
            Hidden field for associating the photo with an equipment item.
        location (forms.ModelChoiceField):
            Hidden field for associating the photo with a location.
        account (forms.ModelChoiceField):
            Hidden field for associating the photo with an account.
    """

    equipment = forms.ModelChoiceField(queryset=Equipment.objects.all(), required=False, widget=forms.HiddenInput())
    location = forms.ModelChoiceField(queryset=Location.objects.all(), required=False, widget=forms.HiddenInput())
    account = forms.ModelChoiceField(queryset=Account.objects.all(), required=False, widget=forms.HiddenInput())

    class Meta:
        model = Photo
        fields = ["image", "title", "caption", "slug", "id"]
        widgets = {"slug": forms.HiddenInput(), "id": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        """Initialise the form and mark slug field as optional.

        Args:
            *args:
                Positional arguments passed to the parent ModelForm.

        Keyword Parameters:
            **kwargs:
                Keyword arguments passed to the parent ModelForm.

        Notes:
            The slug field is marked as not required since it can be automatically
            generated from the associated entity's name during form validation.
        """
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False

    def clean(self):
        """Validate form data and automatically generate title and slug if not provided.

        Returns:
            (dict):
                The cleaned data dictionary with title and slug values populated from
                associated entities if they were not explicitly provided.

        Notes:
            If title or slug are not provided, this method attempts to populate them
            from the associated equipment, location, or account. The slug is generated
            using Django's slugify function on the entity's name. If no slug can be
            determined, it is set to None to trigger proper object save behaviour.
        """
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
    """Form for managing associations between photos and equipment or locations.

    This form provides an interface for linking existing photos to multiple equipment
    items and locations using sorted checkbox selection fields.

    Attributes:
        equipment (SortedCheckboxMultipleChoiceField):
            Field for selecting multiple equipment items to link to the photo.
        location (SortedCheckboxMultipleChoiceField):
            Field for selecting multiple locations to link to the photo.
    """

    class Meta:
        model = Photo
        fields = ["id"]
        widgets = {"id": forms.HiddenInput()}

    equipment = SortedCheckboxMultipleChoiceField(Equipment.objects.all().order_by("category", "name"), required=False)
    location = SortedCheckboxMultipleChoiceField(
        Location.objects.all().order_by("tree_id", "lft", "name"), required=False
    )


class FlatPageForm(forms.ModelForm):
    """Form for creating and editing flat pages with obfuscated HTML content.

    This form uses an obfuscated TinyMCE editor and custom field to safely transmit
    HTML content through web application firewalls. It can be associated with equipment
    or location entities through hidden fields.

    Attributes:
        equipment (forms.ModelChoiceField):
            Hidden field for associating the flat page with an equipment item.
        location (forms.ModelChoiceField):
            Hidden field for associating the flat page with a location.

    Notes:
        The content field uses ObfuscatedTinyMCE widget and ObfuscatedCharField to
        handle ROT13 and Base64 encoding/decoding, allowing safe transmission of HTML
        content that might otherwise be blocked by security filters.
    """

    class Meta:
        model = FlatPage
        fields = ["title", "url", "content", "id"]
        widgets = {"content": ObfuscatedTinyMCE(), "id": forms.HiddenInput()}
        field_classes = {"content": ObfuscatedCharField}

    equipment = forms.ModelChoiceField(queryset=Equipment.objects.all(), required=False, widget=forms.HiddenInput())
    location = forms.ModelChoiceField(queryset=Location.objects.all(), required=False, widget=forms.HiddenInput())


class FlatPagesLinksForm(forms.ModelForm):
    """Form for managing associations between flat pages and equipment or locations.

    This form provides an interface for linking existing flat pages to multiple equipment
    items and locations using sorted checkbox selection fields.

    Attributes:
        equipment (SortedCheckboxMultipleChoiceField):
            Field for selecting multiple equipment items to link to the flat page.
        location (SortedCheckboxMultipleChoiceField):
            Field for selecting multiple locations to link to the flat page.
    """

    class Meta:
        model = FlatPage
        fields = ["id"]
        widgets = {"id": forms.HiddenInput()}

    equipment = SortedCheckboxMultipleChoiceField(Equipment.objects.all().order_by("category", "name"), required=False)
    location = SortedCheckboxMultipleChoiceField(
        Location.objects.all().order_by("tree_id", "lft", "name"), required=False
    )
