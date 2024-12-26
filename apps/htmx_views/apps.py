from __future__ import unicode_literals

# Python imports
from os.path import basename, dirname

# Django imports
from django.apps import AppConfig

# app imports
from . import views


class EquipmentConfig(AppConfig):
    name = basename(dirname(__file__))
