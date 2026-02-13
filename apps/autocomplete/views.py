"""Views for handling autocomplete HTTP requests and rendering responses.

This module provides Django class-based views for managing autocomplete interactions,
including searching for items, toggling selections, and handling the component lifecycle.
Views integrate with HTMX for dynamic updates without full page reloads.
"""

# Python imports
import json

# Django imports
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.urls import path
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views import View

# app imports
from .core import AC_CLASS_CONFIGURABLE_VALUES, ContextArg, _ac_registry


class AutocompleteBaseView(View):
    """Base view providing common functionality for autocomplete views.

    This view handles autocomplete class resolution, authentication checks,
    and provides utility methods for extracting request parameters and
    building template context.

    Attributes:
        ac_class (type):
            The autocomplete class for this view, resolved from the URL.
    """
    @cached_property
    def ac_class(self):
        """Resolve and return the autocomplete class from the URL.

        Returns:
            (type): The autocomplete class registered under the URL name.

        Raises:
            ValueError:
                If no autocomplete is registered with the specified name.
        """
        ac_name = self.kwargs["ac_name"]

        try:
            return _ac_registry[ac_name]

        except KeyError as e:
            raise ValueError(f"No registered autocomplete with name {ac_name}") from e

    def dispatch(self, request, *args, **kwargs):
        """Perform authentication check before dispatching to view method.

        Args:
            request (HttpRequest):
                The Django HTTP request object.
            *args:
                Positional arguments passed to the view.
            **kwargs:
                Keyword arguments passed to the view.

        Returns:
            (HttpResponse): The response from the view method.

        Raises:
            PermissionDenied:
                If the authentication check fails.
        """
        self.ac_class.auth_check(request)

        return super().dispatch(request, *args, **kwargs)

    @cached_property
    def request_dict(self):
        """Convert request QueryDict to a regular dictionary.

        Returns:
            (dict): Dictionary containing the request GET parameters.
        """
        # convert the request's QueryDict into a regular dict
        return self.request.GET.dict()

    def get_field_name(self):
        """Extract the field name from the request.

        Returns:
            (str): The name of the form field being autocompleted.
        """
        return self.request_dict["field_name"]

    def get_hx_attrs(self):
        """Extract HTMX attributes from the request.

        Returns:
            (dict): Dictionary of HTMX attributes, or empty dict if not present.
        """
        return self.request_dict.get("hx_attrs", {})

    def get_component_id(self):
        """Generate the component ID by combining prefix and field name.

        Returns:
            (str): The unique component identifier.
        """
        prefix = self.get_configurable_value("component_prefix")

        return prefix + self.get_field_name()

    def get_configurable_value(self, key):
        """Retrieve a configuration value from request or autocomplete class.

        Configuration values are first checked in the request parameters, then
        fall back to the autocomplete class attributes.

        Args:
            key (str):
                The configuration key to retrieve.

        Returns:
            The configuration value, or None if not found.
        """
        if key in self.request_dict:
            return self.request.GET.get(key)

        if key in AC_CLASS_CONFIGURABLE_VALUES and hasattr(self.ac_class, key):
            return getattr(self.ac_class, key)

        return None

    def get_template_context(self):
        """Build the base template context for rendering autocomplete components.

        Returns:
            (dict): Dictionary containing configuration values and component settings
                for template rendering.
        """
        # many things will come from the request
        # others will be picked up from the AC class

        return {
            "route_name": self.ac_class.route_name,
            "ac_class": self.ac_class,
            "field_name": self.get_field_name(),
            "component_id": self.get_component_id(),
            "required": bool(self.get_configurable_value("required")),
            "placeholder": self.get_configurable_value("placeholder"),
            "indicator": self.get_configurable_value("indicator"),
            "custom_strings": self.ac_class.get_custom_strings(),
            "multiselect": bool(self.get_configurable_value("multiselect")),
            "component_prefix": self.get_configurable_value("component_prefix"),
            "disabled": bool(self.get_configurable_value("disabled")),
            "hx_attrs": self.get_hx_attrs(),
        }


def toggle_set(_set, item):
    """Toggle an item's presence in a set.

    If the item exists in the set (as itself or as a string), it is removed.
    Otherwise, it is added to the set.

    Args:
        _set (set):
            The set to toggle the item in.
        item:
            The item to toggle.

    Returns:
        (set): A new set with the item toggled.
    """
    s = _set.copy()

    if item in s:
        s.remove(item)

    elif str(item) in s:
        s.remove(str(item))

    elif item in {str(x) for x in s}:
        s = {x for x in s if str(x) != item}

    else:
        s.add(item)

    return s


def replace_or_toggle(_set, item):
    """Replace or toggle a single item in a set for single-select mode.

    For single-select autocomplete, this function removes the item if it's already
    selected, otherwise replaces any existing selection with the new item.

    Args:
        _set (set):
            The set containing at most one item.
        item:
            The item to replace or toggle.

    Returns:
        (set): A set containing either the new item or an empty set.

    Raises:
        Exception:
            If the set contains more than one item.
    """

    if len(_set) > 1:
        raise Exception("this function is only for sets with one item")

    toggled = toggle_set(_set, item)

    if len(toggled) > 1:
        return {item}

    return toggled


class ToggleView(AutocompleteBaseView):
    """Handle toggling of selected items in the autocomplete component.

    This view manages selecting and deselecting items, supporting both single
    and multi-select modes. It returns the updated selection state with HTMX
    triggers for client-side updates.
    """
    def get(self, request, *args, **kwargs):
        """Process a toggle request for selecting or deselecting an item.

        Args:
            request (HttpRequest):
                The Django HTTP request containing field_name, current items,
                and the item to toggle.
            *args:
                Positional arguments from the URL.
            **kwargs:
                Keyword arguments from the URL.

        Returns:
            (HttpResponse): Rendered HTML response with updated selection state
                and HTMX trigger for change events.

        Raises:
            HttpResponseBadRequest:
                If the item parameter is missing.
            ValueError:
                If the requested item is not found.
        """
        field_name = self.request_dict["field_name"]

        current_items = self.request.GET.getlist(field_name)
        if current_items == ["undefined"] or current_items == [""]:
            current_items = []

        key_to_toggle = request.GET.get("item")

        if key_to_toggle is None:
            return HttpResponseBadRequest()

        is_multi = self.get_configurable_value("multiselect")

        if is_multi:
            new_selected_keys = toggle_set(set(current_items), key_to_toggle)
        else:
            new_selected_keys = replace_or_toggle(set(current_items), key_to_toggle)
        keys_to_fetch = set(new_selected_keys).union({key_to_toggle})

        context_obj = ContextArg(request=request, client_kwargs=request.GET)
        all_values = self.ac_class.get_items_from_keys(keys_to_fetch, context_obj)

        items = self.ac_class.map_search_results(all_values, new_selected_keys)

        # OOB is used if the user clicks the X on a chip,
        # to update the selected style of the option
        # if it is currently in the dropdown list
        swap_oob = request.GET.get("remove", False)

        target_item = next((x for x in items if x["key"] == key_to_toggle), None)

        new_items = [x for x in items if x["key"] in new_selected_keys]

        def sort_items(item):
            try:
                return current_items.index(f"{item['key']}")
            except ValueError:
                return len(new_items)

        new_items = sorted(new_items, key=sort_items)

        if target_item is None:
            raise ValueError("Requested item to toggle not found.")

        resp = render(
            request,
            "autocomplete/item.html",
            {
                **self.get_template_context(),
                "search": "",
                "values": new_selected_keys,
                "item_as_list": [target_item],
                "item": target_item,
                "toggle": new_items,
                "swap_oob": swap_oob,
            },
        )
        resp.headers["HX-Trigger-After-Settle"] = json.dumps(
            {
                f"{field_name}_change": {
                    "search": "",
                    "values": list(new_selected_keys),
                    "item_as_list": [target_item],
                    "item": target_item,
                    "toggle": new_items,
                    "swap_oob": swap_oob,
                }
            }
        )
        return resp


class ItemsView(AutocompleteBaseView):
    """Handle search requests and return matching items.

    This view processes search queries, applies minimum search length validation,
    and returns paginated results respecting the configured maximum result limit.
    """
    def get(self, request, *args, **kwargs):
        """Process a search request and return matching items.

        Args:
            request (HttpRequest):
                The Django HTTP request containing search query and field name.
            *args:
                Positional arguments from the URL.
            **kwargs:
                Keyword arguments from the URL.

        Returns:
            (HttpResponse): Rendered HTML response with search results, or a message
                if the query is too short.

        Notes:
            Results are limited by the autocomplete class's max_results setting.
            Queries shorter than minimum_search_length return no results.
        """
        context_obj = ContextArg(request=request, client_kwargs=request.GET)

        search_query = request.GET.get("search", "")
        search_results = self.ac_class.search_items(
            # or whatever
            search_query,
            context_obj,
        )

        field_name = self.get_configurable_value("field_name")
        selected_keys = request.GET.getlist(field_name)

        query_too_short = len(search_query) < self.ac_class.minimum_search_length

        if query_too_short:
            total_results = 0
            search_results = []

        else:
            total_results = len(search_results)
            if total_results > self.ac_class.max_results:
                search_results = search_results[: self.ac_class.max_results]

        items = self.ac_class.map_search_results(search_results, selected_keys)

        # render items ...
        return render(
            request,
            "autocomplete/item_list.html",
            {
                # note: name -> field_name
                **self.get_template_context(),
                "show": not (query_too_short),
                "query_too_short": query_too_short,
                "search": search_query,
                "items": items,
                "total_results": total_results,
                "minimum_search_length": self.ac_class.minimum_search_length,
            },
        )
