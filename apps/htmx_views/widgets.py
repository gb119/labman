# -*- coding: utf-8 -*-
"""Provide an HTMX-backed linked select widget."""

# Python imports
from urllib.parse import urlencode

# Django imports
from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import Select
from django.urls import reverse_lazy
from django.utils.text import format_lazy

# external imports
from ajax_select import registry


class HTMXSelectWidget(Select):
    """Update a select's options when a linked form field changes.

    Args:
        lookup_channel (str):
            Registered ``ajax_select`` lookup channel.
        parent (str | None):
            Name of the linked form field. If omitted, use the lookup's ``parameter_name``.
        *args (object):
            Positional arguments passed to Django's ``Select`` widget.

    Keyword Parameters:
        **kwargs (object):
            Keyword arguments passed to Django's ``Select`` widget.

    Raises:
        ImproperlyConfigured:
            If the lookup channel is unknown or no parent field can be determined.

    Examples:
        Create a linked category field::

            >>> widget = HTMXSelectWidget("categories", parent="module")
            >>> widget.parent_name
            'module'

    """

    def __init__(self, lookup_channel, parent=None, *args, **kwargs):
        """Initialise the linked select widget."""
        try:
            self.lookup = registry.get(lookup_channel)
        except ImproperlyConfigured as error:
            raise ImproperlyConfigured(
                f"Attempting to use a htmx_views widget with lookup channel {lookup_channel} that does not exist."
            ) from error

        self.lookup_channel = lookup_channel
        if parent is None:
            parent = getattr(self.lookup, "parameter_name", None)
        if parent is None:
            raise ImproperlyConfigured(
                f"Creating an htmx_views widget for {lookup_channel} without knowing the trigger."
            )

        self.parent_name = parent
        endpoint = reverse_lazy("htmx_views:select", args=(self.lookup_channel,))
        query_string = urlencode({"_htmx_parent": self.parent_name})
        attrs = dict(kwargs.pop("attrs", {}))
        attrs.update(
            {
                "hx-get": format_lazy("{}?{}", endpoint, query_string),
                "hx-trigger": f"change from:#id_{self.parent_name}",
                "hx-include": f"#id_{self.parent_name}",
            }
        )
        kwargs["attrs"] = attrs
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        """Add the rendered select as its own HTMX replacement target.

        Args:
            name (str):
                Form field name.
            value (object):
                Current widget value.
            attrs (dict | None):
                Render-time HTML attributes.

        Returns:
            (dict):
                Django widget context.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(HTMXSelectWidget.get_context)
                True

        """
        attrs = dict(attrs or {})
        attrs["hx-target"] = f"#id_{name}"
        return super().get_context(name, value, attrs)
