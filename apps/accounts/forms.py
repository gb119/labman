#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Form definitions for the accounts apps."""

# Django imports
from django.forms.widgets import Select

# external imports
import floppyforms as forms

# app imports
from .models import Account


class StaffSelectForm(forms.Form):
    """Restrict selection of user accounts to staff user accounts."""

    staff = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_staff=True).order_by("last_name"),
        widget=Select(attrs={"onChange": "this.form.submit();"}),
    )
