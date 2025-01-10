# -*- coding: utf-8 -*-
"""A Form Field for obfuscating submitted data to stop tripping the WAF."""
# Python imports
import base64
import codecs
from copy import deepcopy

# external imports
import floppyforms.__future__ as forms
import nh3


class ObfuscatedCharField(forms.CharField):
    """An obfuscated charfield that will decode base 64 and then rot13 it/"""

    def to_python(self, value):
        """Try rot13 and then base64 decoding."""
        try:
            base64.b64decode(value)  # Even rot13 will decode.
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
            return value
