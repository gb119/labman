# -*- coding: utf-8 -*-
"""Forms for the costings app.

This module provides form classes for managing cost centres and related
financial tracking objects within the labman application.
"""

# Django imports
from django import forms
from django.apps import apps

# external imports
from labman_utils.fields import ObfuscatedCharField
from labman_utils.forms import SortedCheckboxMultipleChoiceField
from labman_utils.widgets import ObfuscatedTinyMCE

# app imports
from .models import CostCentre

Account = apps.get_model(app_label="accounts", model_name="account")


class CostCentreDialogForm(forms.ModelForm):
    """Form for creating and editing cost centres.

    This form allows users to add or modify cost centre information including
    name, description, short name, account code, parent, rate, contact, and
    associated accounts (people).

    The description field uses ObfuscatedTinyMCE widget and ObfuscatedCharField to
    handle ROT13 and Base64 encoding/decoding, allowing safe transmission of HTML
    content through the web application firewall.

    Attributes:
        accounts (SortedCheckboxMultipleChoiceField): Field for selecting multiple
            accounts to associate with this cost centre.
        Meta (class): Meta configuration for the ModelForm.
    """

    accounts = SortedCheckboxMultipleChoiceField(
        Account.objects.filter(is_active=True).order_by("last_name", "first_name"), required=False, label="People"
    )

    class Meta:
        model = CostCentre
        fields = ["name", "short_name", "account_code", "description", "parent", "rate", "contact"]
        widgets = {"description": ObfuscatedTinyMCE()}
        field_classes = {"description": ObfuscatedCharField}
