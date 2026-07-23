# -*- coding: utf-8 -*-
"""Custom Django form fields for secure data handling.

This module provides specialised form fields that handle obfuscated data transmission
to prevent triggering web application firewalls whilst maintaining data integrity and
security.
"""
# Python imports
import base64
import codecs
from copy import deepcopy

# Django imports
from django import forms

# external imports
import nh3
from charset_normalizer import from_bytes
from tinymce.models import HTMLField

# app imports
from .widgets import ObfuscatedTinyMCE


class ObfuscatedCharField(forms.CharField):
    """An obfuscated charfield that will decode base 64 and then rot13 it/"""

    def to_python(self, value):
        """Try rot13 and then base64 decoding."""
        if value.startswith("ROT13+B64:"):
            value = value[10:]
        else:
            return value
        try:
            rot13_decoded = codecs.decode(value, "rot_13").encode("utf-8")

            # Base64 decoding
            base64_decoded = str(from_bytes(base64.b64decode(rot13_decoded)).best())

            # Use ammonia to sanitize the html - but allow class attriobutes on pre and div tags.
            attributes = deepcopy(nh3.ALLOWED_ATTRIBUTES)
            # for k in attributes:
            #     attributes[k].add("class")
            attributes["div"] = {"class"}
            attributes["pre"] = {"class"}
            attributes["span"] = {"style"}

            cleaned = nh3.clean(base64_decoded, attributes=attributes)
            return cleaned
        except (ValueError, base64.binascii.Error, TypeError, UnicodeDecodeError):
            return value


class ObfuscatedHTMLField(HTMLField):
    def formfield(self, **kwargs):
        """Replicate TinyMCE's HTMLFIeld but force a custom subfield."""
        defaults = {"form_class": ObfuscatedCharField, "widget": ObfuscatedTinyMCE}
        defaults.update(kwargs)
        return super().formfield(**defaults)
