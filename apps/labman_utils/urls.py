# -*- coding: utf-8 -*-
"""
Created on Sun Aug  6 16:31:16 2023

@author: phygbu
"""
# Django imports
from django.urls import path, register_converter


class FloatUrlParameterConverter:
    regex = r"[0-9]+\.?[0-9]+"

    def to_python(self, value):
        return float(value)

    def to_url(self, value):
        return str(value)


register_converter(FloatUrlParameterConverter, "float")

urlpatterns = []
