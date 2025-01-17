# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 21:30:01 2023

@author: phygbu
"""
# Django imports
from django import template

register = template.Library()


@register.filter(name="zip")
def zip_lists(a, b):
    return zip(a, b)


@register.filter
def item(mapping, key):
    if key.isnumeric():
        key = int(key)
    try:
        return mapping[key]
    except KeyError:
        return ""


@register.filter
def can_edit(equipment, target):
    """Proxy through to the edit."""
    return equipment.can_edit(target)
