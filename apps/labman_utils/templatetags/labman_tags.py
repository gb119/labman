# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 21:30:01 2023

@author: phygbu
"""
from django import template

register = template.Library()

@register.filter(name='zip')
def zip_lists(a, b):
  return zip(a, b)
