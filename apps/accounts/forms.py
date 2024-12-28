#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Form definitions for the accounts apps."""

# Django imports
from django import forms
from django.forms.widgets import Select

# app imports
from .models import Account


class StaffSelectForm(forms.Form):
    """Restrict selection of user accounts to staff user accounts."""

    staff = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_staff=True).order_by("last_name"),
        widget=Select(attrs={"onChange": "this.form.submit();"}),
    )


class UserAdminForm(forms.ModelForm):
    """Model form definition for user accounts."""

    class Meta:
        model = Account
        widgets = {
            "first_name": forms.TextInput(attrs={"size": 20}),
            "last_name": forms.TextInput(attrs={"size": 20}),
        }
        fields = "__all__"
