# -*- coding: utf-8 -*-
"""
Created on Tue Jul 18 21:05:11 2023

@author: phygbu
"""
# Django imports
from django import forms

# external imports
from accounts.models import Account

# app imports
from .models import Document


class SignOffForm(forms.Form):

    """Form for signing off the documents."""

    user = forms.ModelChoiceField(Account.objects.all(), widget=forms.HiddenInput)
    document = forms.ModelChoiceField(Document.objects.all(), widget=forms.HiddenInput)
    version = forms.IntegerField(widget=forms.HiddenInput)
    signed = forms.BooleanField()
