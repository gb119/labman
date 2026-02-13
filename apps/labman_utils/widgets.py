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
    """A TinyMCE widget with client-side obfuscation for secure data transmission.

    This widget extends the standard TinyMCE rich text editor by adding JavaScript that
    obfuscates the content before submission. This prevents the content from triggering
    web application firewall rules whilst maintaining data integrity.

    Attributes:
        The widget inherits all attributes from TinyMCE and adds custom CSS class for
        JavaScript targeting.
    """

    def __init__(self, content_language=None, attrs=None, mce_attrs=None):
        """Initialise the obfuscated TinyMCE widget with required CSS class.

        Args:
            content_language (str):
                The language code for the content editor.

        Keyword Parameters:
            attrs (dict):
                HTML attributes for the widget. The 'obfuscate_html' class is automatically
                added to enable JavaScript obfuscation. The default is None.
            mce_attrs (dict):
                TinyMCE-specific configuration attributes. The default is None.

        Notes:
            The 'obfuscate_html' CSS class is essential for the JavaScript obfuscation
            code to identify and process this widget's content before form submission.
        """
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
        """Define the media resources required by the widget.

        Returns:
            (forms.Media):
                A Media object containing the CSS and JavaScript files required for the
                widget to function, including the standard TinyMCE resources and the
                custom obfuscation JavaScript.

        Notes:
            This method adds '/static/js/obfuscatre_htmlfield.js' to the standard TinyMCE
            media resources to provide the client-side obfuscation functionality.
        """
        media = super().media
        js = media._js_lists[0]
        css = media._css_lists[0]
        js += ["/static/js/obfuscatre_htmlfield.js"]
        return forms.Media(css=css, js=js)


class AdminObfuscatedTinyMCE(ObfuscatedTinyMCE, admin_widgets.AdminTextareaWidget):
    """An obfuscated TinyMCE widget for use in Django admin interface.

    This widget combines the obfuscation capabilities of ObfuscatedTinyMCE with the
    styling and functionality of Django's AdminTextareaWidget, making it suitable
    for use in the Django admin interface.

    Notes:
        This widget inherits behaviour from both ObfuscatedTinyMCE and AdminTextareaWidget,
        providing a rich text editor with obfuscation in the admin interface.
    """
