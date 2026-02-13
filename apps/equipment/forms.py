# -*- coding: utf-8 -*-
"""Equipment forms module.

This module provides Django form classes for equipment management, including
date selection forms, document sign-off forms, and equipment editing forms.
"""
# Django imports
from django import forms

# external imports
from accounts.autocomplete import AllUsersComplete
from accounts.models import Account
from autocomplete import AutocompleteWidget
from labman_utils.forms import DateCustomInput
from labman_utils.widgets import ObfuscatedTinyMCE

# app imports
from .autocomplete import LocationAutocomplete
from .models import Document, Equipment, UserListEntry


class SelectDatefForm(forms.Form):
    """A simple form for selecting a date with auto-submit functionality.

    This form provides a single date field that automatically submits when
    a date is selected, useful for filtering or navigation based on dates.

    Attributes:
        date (forms.DateField): The date field with custom input widget that
            submits the form on change.
    """

    date = forms.DateField(widget=DateCustomInput(attrs={"onChange": "this.form.submit();"}))


class SignOffForm(forms.Form):
    """A form for recording document sign-off by users.

    This form captures user acknowledgement of documents, including the
    specific version signed. The user, document, and version fields are
    hidden as they are typically pre-populated from the context.

    Attributes:
        user (forms.ModelChoiceField): The user signing off the document,
            hidden field populated from Account model.
        document (forms.ModelChoiceField): The document being signed off,
            hidden field populated from Document model.
        version (forms.FloatField): The version number of the document being
            signed, hidden field.
        signed (forms.BooleanField): Checkbox indicating the user has signed
            off the document.
    """

    user = forms.ModelChoiceField(Account.objects.all(), widget=forms.HiddenInput)
    document = forms.ModelChoiceField(Document.objects.all(), widget=forms.HiddenInput)
    version = forms.FloatField(widget=forms.HiddenInput)
    signed = forms.BooleanField()


class UserListEnryForm(forms.ModelForm):
    """A form for editing user list entries associated with equipment.

    This ModelForm allows editing of user list entries, which track which
    users are authorised or associated with specific equipment. The equipment
    field is hidden as it's typically pre-selected, and the user field uses
    autocomplete for easy selection.

    Attributes:
        Meta.model (UserListEntry): The model class for this form.
        Meta.exclude (list): Fields excluded from the form (hold, updated).
        Meta.widgets (dict): Custom widgets for form fields, including hidden
            equipment field and autocomplete user field.
    """

    class Meta:
        model = UserListEntry
        exclude = ["hold", "updated"]
        widgets = {
            "equipment": forms.HiddenInput(),
            "user": AutocompleteWidget(ac_class=AllUsersComplete),
        }


class EquipmentForm(forms.ModelForm):
    """A form for creating and editing equipment records.

    This ModelForm provides fields for managing equipment details including
    name, description, owner, location, and offline status. Rich text editing
    is provided for descriptions, and autocomplete widgets are used for owner
    and location selection.

    Attributes:
        Meta.model (Equipment): The model class for this form.
        Meta.fields (list): Fields included in the form (name, description,
            owner, location, offline).
        Meta.widgets (dict): Custom widgets for form fields, including rich
            text editor for description and autocomplete for owner and location.
    """

    class Meta:
        model = Equipment
        fields = ["name", "description", "owner", "location", "offline"]

        widgets = {
            "description": ObfuscatedTinyMCE(),
            "owner": AutocompleteWidget(ac_class=AllUsersComplete),
            "location": AutocompleteWidget(ac_class=LocationAutocomplete),
        }
