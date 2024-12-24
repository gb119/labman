# -*- coding: utf-8 -*-R
"""Config settings for bookings app."""
from __future__ import unicode_literals

# Python imports
from os.path import basename, dirname

# Django imports
from django.apps import AppConfig


class BookingsConfig(AppConfig):
    """Bookings App config class."""

    name = basename(dirname(__file__))
