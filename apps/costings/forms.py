# -*- coding: utf-8 -*-
"""Forms for the costings app.

This module provides form classes for managing cost centres and related
financial tracking objects within the labman application.
"""
# Django imports
from django import forms

# app imports
from .models import CostCentre


class CostCentreDialogForm(forms.ModelForm):
    """Form for creating and editing cost centres.

    This form allows users to add or modify cost centre information including
    name, description, short name, account code, parent, rate, and contact.
    
    Attributes:
        Meta (class): Meta configuration for the ModelForm.
    """

    class Meta:
        model = CostCentre
        fields = ["name", "short_name", "account_code", "description", "parent", "rate", "contact"]
