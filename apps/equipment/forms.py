# -*- coding: utf-8 -*-
"""
Created on Tue Jul 18 21:05:11 2023

@author: phygbu
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
    """Supersimple form to select a date."""

    date = forms.DateField(widget=DateCustomInput(attrs={"onChange": "this.form.submit();"}))


class SignOffForm(forms.Form):
    """Form for signing off the documents."""

    user = forms.ModelChoiceField(Account.objects.all(), widget=forms.HiddenInput)
    document = forms.ModelChoiceField(Document.objects.all(), widget=forms.HiddenInput)
    version = forms.FloatField(widget=forms.HiddenInput)
    signed = forms.BooleanField()


class UserListEnryForm(forms.ModelForm):
    """Form for editing userlist entries from equipment list."""

    class Meta:
        model = UserListEntry
        exclude = ["hold", "updated"]
        widgets = {
            "equipment": forms.HiddenInput(),
            "user": AutocompleteWidget(ac_class=AllUsersComplete),
        }


class EquipmentForm(forms.ModelForm):
    """Form for editing userlist entries from equipment list."""

    class Meta:
        model = Equipment
        fields = ["name", "description", "owner", "location", "offline"]

        widgets = {
            "description": ObfuscatedTinyMCE(),
            "owner": AutocompleteWidget(ac_class=AllUsersComplete),
            "location": AutocompleteWidget(ac_class=LocationAutocomplete),
        }
