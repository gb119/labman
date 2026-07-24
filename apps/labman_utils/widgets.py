# -*- coding: utf-8 -*-
"""Custom Django widgets for obfuscated data transmission through WAF.

This module provides specialised widgets that extend TinyMCE rich text editor functionality
with client-side obfuscation capabilities. This allows HTML content to be safely transmitted
through web application firewalls that might otherwise block legitimate content.
"""
# Django imports
from django import forms
from django.contrib.admin import widgets as admin_widgets
from django.urls import reverse

# external imports
import tinymce.settings
from tinymce.widgets import TinyMCE


class ObfuscatedTinyMCE(TinyMCE):
    """A hacked version of TinyMCE that adds extra javascript.

    Examples:
        Inspect the public interface in an interactive session::

            >>> ObfuscatedTinyMCE.__name__
            'ObfuscatedTinyMCE'

    """

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
        """Perform the media operation.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(ObfuscatedTinyMCE.media)
                True

        """
        css = None
        if tinymce.settings.USE_COMPRESSOR:
            js = [reverse("tinymce-compressor")]
        else:
            js = [tinymce.settings.JS_URL]
        js += ["/static/js/obfuscatre_htmlfield.js"]
        if tinymce.settings.USE_FILEBROWSER:
            js.append(reverse("tinymce-filebrowser"))
        if tinymce.settings.USE_EXTRA_MEDIA:
            if "js" in tinymce.settings.USE_EXTRA_MEDIA:
                js += tinymce.settings.USE_EXTRA_MEDIA["js"]

            if "css" in tinymce.settings.USE_EXTRA_MEDIA:
                css = tinymce.settings.USE_EXTRA_MEDIA["css"]
        js.append("django_tinymce/init_tinymce.js")

        return forms.Media(css=css, js=js)


class AdminObfuscatedTinyMCE(ObfuscatedTinyMCE, admin_widgets.AdminTextareaWidget):
    """An obfuscated TinyMCE widget for use in Django admin interface.

            This widget combines the obfuscation capabilities of ObfuscatedTinyMCE with the
            styling and functionality of Django's AdminTextareaWidget, making it suitable
            for use in the Django admin interface.

    Notes:
        This widget inherits behaviour from both ObfuscatedTinyMCE and AdminTextareaWidget,
        providing a rich text editor with obfuscation in the admin interface.


    Examples:
        Inspect the public interface in an interactive session::

            >>> AdminObfuscatedTinyMCE.__name__
            'AdminObfuscatedTinyMCE'

    """
