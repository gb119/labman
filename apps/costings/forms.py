# -*- coding: utf-8 -*-
"""Forms for the costings app.

This module provides form classes for managing cost centres and related
financial tracking objects within the labman application.
"""

# Django imports
from django import forms
from django.apps import apps

# external imports
from labman_utils.widgets import ObfuscatedTinyMCE
from sortedm2m.forms import SortedCheckboxMultipleChoiceField

# app imports
from .models import CostCentre

Account = apps.get_model(app_label="accounts", model_name="account")


class CostCentreDialogForm(forms.ModelForm):
    """Form for creating and editing cost centres.

    This form allows users to add or modify cost centre information including
    name, description, short name, account code, parent, rate, contact, and
    associated accounts (people).

    Attributes:
        accounts (SortedCheckboxMultipleChoiceField): Field for selecting multiple
            accounts to associate with this cost centre.
        Meta (class): Meta configuration for the ModelForm.
    """

    accounts = SortedCheckboxMultipleChoiceField(
        Account.objects.all().order_by("last_name", "first_name"), required=False, label="People"
    )

    class Meta:
        model = CostCentre
        fields = ["name", "short_name", "account_code", "description", "parent", "rate", "contact"]
        widgets = {"description": ObfuscatedTinyMCE()}
