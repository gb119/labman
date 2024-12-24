#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Config settings for the accounts app."""
from __future__ import unicode_literals

# Python imports
from os.path import basename, dirname

# Django imports
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Django config class for the accounts app."""

    name = basename(dirname(__file__))
