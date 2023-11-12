from __future__ import unicode_literals

# Python imports
from os.path import basename, dirname

# Django imports
from django.apps import AppConfig


class EquipmentConfig(AppConfig):
    name = basename(dirname(__file__))
