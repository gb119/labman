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


class ObfuscatedCharField(forms.CharField):
    """A character field that decodes ROT13 and Base64 encoded values.

    This field is designed to receive data that has been obfuscated using ROT13 encoding
    followed by Base64 encoding. It decodes the data and sanitises any HTML content to
    prevent XSS attacks whilst allowing certain safe HTML tags and attributes.

    Notes:
        The decoding process attempts to:
        1. Validate the input as Base64 encoded data
        2. Apply ROT13 decoding
        3. Apply Base64 decoding
        4. Try UTF-8 and Latin-1 character encoding
        5. Sanitise HTML using the nh3 library with custom allowed attributes

        If any decoding step fails, the original value is returned unchanged.
    """

    def to_python(self, value):
        """Convert obfuscated field value to sanitised HTML.

        This method performs ROT13 and Base64 decoding on the input value, then sanitises
        the resulting HTML to prevent security issues whilst preserving legitimate formatting.

        Args:
            value (str):
                The obfuscated input value, expected to be ROT13 encoded then Base64 encoded.

        Returns:
            (str):
                The decoded and sanitised HTML content, or the original value if decoding fails.

        Notes:
            The sanitisation process allows the 'class' attribute on 'div' and 'pre' tags
            in addition to the default allowed HTML elements and attributes defined by nh3.
            Character encoding is attempted first with UTF-8, then falls back to Latin-1.
        """
        try:
            _ = base64.b64decode(value, validate=True)  # Even rot13 will decode.
        except (ValueError, base64.binascii.Error, TypeError, UnicodeDecodeError) as err:
            return value
        try:
            rot13_decoded = codecs.decode(value, "rot_13").encode("utf-8")

            # Base64 decoding
            base64_decoded = base64.b64decode(rot13_decoded)
            for codec in ["utf-8", "latin-1"]:  # Try utf-8 first and if that fails try latin-1
                try:
                    base64_decoded = base64_decoded.decode(codec)
                except (ValueError, UnicodeError):
                    continue
                break
            # Use ammonia to sanitize the html - but allow class attriobutes on pre and div tags.
            attributes = deepcopy(nh3.ALLOWED_ATTRIBUTES)
            # for k in attributes:
            #     attributes[k].add("class")
            attributes["div"] = {"class"}
            attributes["pre"] = {"class"}

            cleaned = nh3.clean(base64_decoded, attributes=attributes)
            return cleaned
        except (ValueError, base64.binascii.Error, TypeError, UnicodeDecodeError) as err:
            assert False
            return value
