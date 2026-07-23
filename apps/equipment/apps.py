"""Provide apps functionality for the apps.equipment package."""

from __future__ import unicode_literals

# Python imports
from os.path import basename, dirname

# Django imports
from django.apps import AppConfig


class EquipmentConfig(AppConfig):
    """Provide the EquipmentConfig implementation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> EquipmentConfig.__name__
            'EquipmentConfig'
    """

    name = basename(dirname(__file__))
