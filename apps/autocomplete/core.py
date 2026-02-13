"""Core autocomplete functionality for registering and managing autocomplete classes.

This module provides the base Autocomplete class and registration mechanism for
autocomplete components. It handles the registry of autocomplete classes, validation,
and provides the foundation for creating custom autocomplete implementations.
"""

# Python imports
from dataclasses import dataclass

# Django imports
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

# This is the registry of registered autocomplete classes,
# i.e. the ones who respond to requests
_ac_registry = {}


AC_CLASS_CONFIGURABLE_VALUES = {
    "disabled",
    "no_result_text",
    "narrow_search_text",
    "minimum_search_length",
    "max_results",
    "component_prefix",
    "placeholder",
    "indicator",
}


def register(ac_class: type, route_name: str = None):
    """Register an autocomplete class in the global registry.

    Args:
        ac_class (type):
            The autocomplete class to register. Must be a subclass of Autocomplete
            and implement the required methods.

    Keyword Parameters:
        route_name (str):
            The unique name used to identify this autocomplete in URLs. If not
            provided, the class name is used.

    Returns:
        (type): The registered autocomplete class.

    Raises:
        ValueError:
            If an autocomplete with the same route_name is already registered or
            if the class fails validation.

    Examples:
        >>> @register
        ... class MyAutocomplete(Autocomplete):
        ...     pass
        >>> register(MyAutocomplete, route_name='custom-name')
    """
    if not route_name:
        route_name = ac_class.__name__

    ac_class.validate()

    if route_name in _ac_registry:
        raise ValueError(f"Autocomplete with name '{route_name}' is already registered.")

    ac_class.route_name = route_name

    _ac_registry[route_name] = ac_class

    return ac_class


class Autocomplete:
    """Base class for creating autocomplete components.

    This class provides the foundation for implementing custom autocomplete
    functionality. Subclasses must implement the search_items and get_items_from_keys
    methods to define the search and retrieval behaviour.

    Attributes:
        no_result_text (str):
            Message displayed when no results are found.
        narrow_search_text (str):
            Message displayed when results are truncated. Supports %(page_size)s
            and %(total)s format placeholders.
        type_at_least_n_characters (str):
            Message displayed when search query is too short. Supports %(n)s
            format placeholder.
        minimum_search_length (int):
            Minimum number of characters required before search is performed.
        max_results (int):
            Maximum number of results to return in a single search.
        component_prefix (str):
            Prefix added to component IDs for namespacing.
        route_name (str):
            The unique name used in URLs, set during registration.

    Notes:
        Subclasses must implement:
        - search_items(search, context): Search for items matching the query
        - get_items_from_keys(keys, context): Retrieve specific items by their keys

    Examples:
        >>> class MyAutocomplete(Autocomplete):
        ...     @classmethod
        ...     def search_items(cls, search, context):
        ...         return [{"key": "1", "label": "Item 1"}]
        ...
        ...     @classmethod
        ...     def get_items_from_keys(cls, keys, context):
        ...         return [{"key": k, "label": f"Item {k}"} for k in keys]
    """

    no_result_text = _("No results found.")
    narrow_search_text = _("Showing %(page_size)s of %(total)s items. Narrow your search for more results.")
    type_at_least_n_characters = _("Type at least %(n)s characters")
    minimum_search_length = 3
    max_results = 100
    component_prefix = ""

    @classmethod
    def auth_check(cls, request):
        """Perform authentication and authorisation checks for autocomplete access.

        Override this method to implement custom authentication logic. By default,
        checks the AUTOCOMPLETE_BLOCK_UNAUTHENTICATED setting to determine if
        unauthenticated users should be blocked.

        Args:
            request (HttpRequest):
                The Django HTTP request object containing user information.

        Raises:
            PermissionDenied:
                If the user is not authorised to use the autocomplete or if
                AUTOCOMPLETE_BLOCK_UNAUTHENTICATED is True and user is not
                authenticated.
        """
        if getattr(settings, "AUTOCOMPLETE_BLOCK_UNAUTHENTICATED", False) and not request.user.is_authenticated:
            raise PermissionDenied("Must be logged in to use autocomplete")

        pass

    @classmethod
    def validate(cls):
        """Validate that the autocomplete class implements required methods.

        Raises:
            ValueError:
                If the class does not implement search_items or get_items_from_keys
                methods.
        """
        if not hasattr(cls, "search_items"):
            raise ValueError("You must implement a search_items method.")

        if not hasattr(cls, "get_items_from_keys"):
            raise ValueError("You must implement a get_items_from_keys method.")

    @classmethod
    def map_search_results(cls, items_iterable, selected_keys=None):
        """Map search results to a standardised format for display.

        Transforms raw search results into a consistent structure with key, label,
        and selected attributes. Override this method to customise result mapping
        or to work with complex data structures like Django QuerySets.

        Args:
            items_iterable (Iterable):
                Iterable of items returned by search_items. Each item should be a
                dictionary with 'key' and 'label' fields.

        Keyword Parameters:
            selected_keys (set):
                Set of keys that are currently selected. Used to mark items as
                selected in the results.

        Returns:
            (list): List of dictionaries with 'key', 'label', and 'selected' fields.

        Notes:
            The default implementation expects items_iterable to yield dictionaries
            with 'key' and 'label' keys.
        """

        return [
            {  # this is the default mapping
                "key": str(i["key"]),
                "label": i["label"],
                "selected": i["key"] in selected_keys or str(i["key"]) in selected_keys,
            }
            for i in items_iterable
        ]

    @classmethod
    def get_custom_strings(cls):
        """Get localised UI strings for the autocomplete component.

        Returns:
            (dict): Dictionary containing localised strings for 'no_results',
                'more_results', and 'type_at_least_n_characters'.
        """
        return {
            "no_results": cls.no_result_text,
            "more_results": cls.narrow_search_text,
            "type_at_least_n_characters": cls.type_at_least_n_characters,
        }

    @classmethod
    def get_extra_text_input_hx_vals(cls):
        """Get additional HTMX values for the text input element.

        Override this method to provide additional key-value pairs that will be
        included in the hx-vals attribute of the search input element.

        Returns:
            (dict): Dictionary of additional HTMX values. Keys and values must not
                contain single quotes. Values are not quoted to support inline
                JavaScript expressions.

        Notes:
            - Values must not contain single quotes
            - Values are not automatically quoted to allow JavaScript expressions
        """

        return {}


@dataclass
class ContextArg:
    """Context information passed to autocomplete search methods.

    Attributes:
        request (HttpRequest):
            The Django HTTP request object.
        client_kwargs (dict):
            Additional parameters from the client request, typically from query
            parameters or form data.

    Examples:
        >>> context = ContextArg(request=request, client_kwargs=request.GET)
        >>> results = MyAutocomplete.search_items("query", context)
    """
    request: HttpRequest
    client_kwargs: dict
