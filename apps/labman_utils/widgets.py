# -*- coding: utf-8 -*-
"""Special Widgets for tranmitting suspcious data through the WAF."""
# Django imports
from django import forms
from django.contrib.admin import widgets as admin_widgets
from django.urls import reverse

# external imports
import tinymce.settings
from tinymce.widgets import TinyMCE


class ObfuscatedTinyMCE(TinyMCE):
    """A hacked version of TinyMCE that adds extra javascript."""

    def __init__(self, content_language=None, attrs=None, mce_attrs=None):
        """Make sure we set the class to incloude saomething fopr the JavaScript to latch on to."""
        if attrs is None:
            attrs = {}
        if css_class := attrs.get("class", None):
            css_class += " obfuscate_html"
        else:
            css_class = "obfuscate_html"
        attrs["class"] = css_class
        super().__init__(content_language=content_language, attrs=attrs, mce_attrs=mce_attrs)

    @TinyMCE.media.getter
    def media(self):
        media = super().media
        js = media._js_lists[0]
        css = media._css_lists[0]
        js += ["/static/js/obfuscatre_htmlfield.js"]
        return forms.Media(css=css, js=js)


class AdminObfuscatedTinyMCE(ObfuscatedTinyMCE, admin_widgets.AdminTextareaWidget):
    """Create an admin widget for the obfuscated text areas."""

    pass
