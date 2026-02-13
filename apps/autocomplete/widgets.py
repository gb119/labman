"""Django widget implementation for autocomplete form fields.

This module enables the autocomplete component to be used as a standard Django
form widget, integrating seamlessly with Django forms and providing configuration
options for customising the autocomplete behaviour and appearance.
"""

# Django imports
from django.forms import Widget

# app imports
from .core import AC_CLASS_CONFIGURABLE_VALUES, Autocomplete


class AutocompleteWidget(Widget):
    """Django form widget for rendering autocomplete components.

    This widget integrates autocomplete functionality into Django forms, handling
    both single and multi-select modes. It manages value extraction from form
    data and provides a template-based rendering system.

    Attributes:
        template_name (str):
            Path to the template used for rendering the widget.
        configurable_values (list):
            List of configuration options that can be set via the options parameter.
        ac_class (type):
            The autocomplete class that provides search and retrieval functionality.
        config (dict):
            Dictionary of configuration values set for this widget instance.

    Examples:
        >>> widget = AutocompleteWidget(
        ...     MyAutocomplete,
        ...     options={'multiselect': True, 'placeholder': 'Search...'}
        ... )
    """
    template_name = "autocomplete/component.html"

    configurable_values = [
        "indicator",
        "multiselect",
        "label",
        "component_prefix",
        # the below are also configurable from the AC class
        "placeholder",
    ]

    def __init__(self, ac_class, attrs=None, options=None):
        """Initialise the autocomplete widget with a specific autocomplete class.

        Args:
            ac_class (type):
                The autocomplete class to use for this widget. Must be a subclass
                of Autocomplete.

        Keyword Parameters:
            attrs (dict):
                HTML attributes to apply to the widget element.
            options (dict):
                Widget configuration options. Valid keys are defined in
                configurable_values.

        Raises:
            ValueError:
                If an invalid option key is provided.
        """
        self.ac_class = ac_class
        super().__init__(attrs)

        if not options:
            options = {}

        self.config = {}
        for k, v in options.items():
            if k in self.configurable_values:
                self.config[k] = v
            else:
                raise ValueError(f"Invalid option {k}")

    def value_from_datadict(self, data, files, name):
        """Extract the field value from form data.

        Handles both single and multi-select modes, extracting values from Django's
        QueryDict or plain dictionaries (e.g., JSON data).

        Args:
            data (QueryDict or dict):
                Form data containing the field values.
            files (MultiValueDict):
                Uploaded files (not used by this widget).
            name (str):
                The field name to extract.

        Returns:
            The extracted value(s). For multi-select, returns a list; for single-select,
            returns a single value.
        """
        if self.is_multi:
            try:
                # classic POSTs go though django's QueryDict structure
                # which has a getlist method
                value = data.getlist(name)
            except AttributeError:
                # some clients just provide lists in JSON
                value = data.get(name)

        else:
            value = data.get(name)

        return value

    def value_omitted_from_data(self, data, files, name):
        """Check if the field value was omitted from the form data.

        For multi-select widgets, always returns an empty list since an unselected
        multi-select field doesn't appear in POST data.

        Args:
            data (QueryDict or dict):
                Form data to check.
            files (MultiValueDict):
                Uploaded files (not used by this widget).
            name (str):
                The field name to check.

        Returns:
            (list): Empty list indicating the field was not omitted.
        """
        # An unselected <select multiple> doesn't appear in POST data, so it's
        # never known if the value is actually omitted.
        return []

    def get_component_id(self, field_name):
        """Generate the component ID by combining prefix and field name.

        Args:
            field_name (str):
                The name of the form field.

        Returns:
            (str): The unique component identifier.
        """
        prefix = self.get_configurable_value("component_prefix")

        return prefix + field_name

    def get_configurable_value(self, key):
        """Retrieve a configuration value from widget config or autocomplete class.

        Configuration values are first checked in the widget's config dictionary,
        then fall back to the autocomplete class attributes.

        Args:
            key (str):
                The configuration key to retrieve.

        Returns:
            The configuration value, or None if not found.
        """
        if key in self.config:
            return self.config.get(key)

        if key in AC_CLASS_CONFIGURABLE_VALUES and hasattr(self.ac_class, key):
            return getattr(self.ac_class, key)

        return None

    @property
    def is_multi(self):
        """Determine if the widget is in multi-select mode.

        Returns:
            (bool): True if multi-select is enabled, False otherwise.
        """
        return self.get_configurable_value("multiselect")

    def get_context(self, name, value, attrs):
        """Build the template context for rendering the widget.

        Args:
            name (str):
                The name of the form field.
            value:
                The current value(s) of the field. Can be a single value or list
                of values for multi-select.
            attrs (dict):
                HTML attributes for the widget element.

        Returns:
            (dict): Context dictionary for template rendering, including the
                autocomplete class, field configuration, and selected items.
        """
        context = super().get_context(name, value, attrs)

        proper_attrs = self.build_attrs(self.attrs, attrs)

        if value is None:
            selected_options = []
        else:
            if self.is_multi:
                selected_options = self.ac_class.get_items_from_keys(value, None)
            else:
                selected_options = self.ac_class.get_items_from_keys([value], None)

        context["ac_class"] = self.ac_class
        context["field_name"] = name
        context["id"] = attrs.get("id", self.attrs.get("id", None))
        context["route_name"] = self.ac_class.route_name

        context["disabled"] = proper_attrs.get("disabled", False)
        context["required"] = proper_attrs.get("required", False)

        context["indicator"] = self.get_configurable_value("indicator")
        context["multiselect"] = self.is_multi

        context["label"] = self.get_configurable_value("label")
        context["placeholder"] = self.get_configurable_value("placeholder")
        # context["values"] = list(self.a_c.item_values(self.a_c, selected_options))
        context["values"] = [x["key"] for x in selected_options]
        context["selected_items"] = selected_options
        context["component_prefix"] = self.get_configurable_value("component_prefix")
        context["component_id"] = self.get_component_id(name)

        return context
