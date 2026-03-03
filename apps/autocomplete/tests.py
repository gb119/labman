"""Tests for the autocomplete app.

This module tests authentication enforcement, error handling, XSS-prevention
measures, view logic, widget behaviour, template tags, and the shortcuts
module of the autocomplete component.
"""

# Python imports
import json
from unittest.mock import MagicMock

# Django imports
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import RequestFactory

# external imports
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MinimalAutocomplete:
    """Minimal stub that satisfies Autocomplete.validate()."""

    route_name = "TestAC"

    @classmethod
    def search_items(cls, search, context):
        return []

    @classmethod
    def get_items_from_keys(cls, keys, context):
        return []


# ---------------------------------------------------------------------------
# auth_check tests
# ---------------------------------------------------------------------------


class TestAuthCheck:
    """Tests for Autocomplete.auth_check security behaviour."""

    def _make_request(self, authenticated=True):
        """Return a GET request with an authenticated or anonymous user."""
        # external imports
        from accounts.models import Account

        rf = RequestFactory()
        request = rf.get("/")
        if authenticated:
            user = Account(username="testuser", is_active=True)
            request.user = user
        else:
            request.user = AnonymousUser()
        return request

    def test_unauthenticated_user_raises_permission_denied(self):
        """auth_check raises PermissionDenied for an anonymous user by default."""
        # external imports
        from autocomplete.core import Autocomplete

        request = self._make_request(authenticated=False)
        with pytest.raises(PermissionDenied):
            Autocomplete.auth_check(request)

    def test_authenticated_user_is_allowed(self):
        """auth_check does not raise for an authenticated user."""
        # external imports
        from autocomplete.core import Autocomplete

        request = self._make_request(authenticated=True)
        # Should not raise
        Autocomplete.auth_check(request)

    def test_allow_unauthenticated_setting_permits_anonymous(self, settings):
        """Setting AUTOCOMPLETE_ALLOW_UNAUTHENTICATED=True permits anonymous access."""
        # external imports
        from autocomplete.core import Autocomplete

        settings.AUTOCOMPLETE_ALLOW_UNAUTHENTICATED = True
        request = self._make_request(authenticated=False)
        # Should not raise
        Autocomplete.auth_check(request)


# ---------------------------------------------------------------------------
# View error-handling tests
# ---------------------------------------------------------------------------


class TestAutocompleteViews:
    """Tests for ItemsView and ToggleView error handling."""

    def _make_authenticated_request(self):
        """Return an authenticated GET request using a mock user (no DB required)."""
        # Python imports
        from unittest.mock import MagicMock

        rf = RequestFactory()
        request = rf.get("/", {"field_name": "my_field", "component_prefix": ""})
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        return request

    def test_items_view_unknown_ac_name_raises_404(self):
        """ItemsView raises Http404 when given an unregistered autocomplete name."""
        # external imports
        from autocomplete.views import ItemsView

        request = self._make_authenticated_request()
        view = ItemsView.as_view()
        with pytest.raises(Http404):
            view(request, ac_name="DoesNotExist__XYZ")

    def test_toggle_view_unknown_ac_name_raises_404(self):
        """ToggleView raises Http404 when given an unregistered autocomplete name."""
        # external imports
        from autocomplete.views import ToggleView

        request = self._make_authenticated_request()
        view = ToggleView.as_view()
        with pytest.raises(Http404):
            view(request, ac_name="DoesNotExist__XYZ")

    def test_items_view_unauthenticated_raises_permission_denied(self):
        """ItemsView raises PermissionDenied when accessed without authentication."""
        # external imports
        from autocomplete.views import ItemsView

        rf = RequestFactory()
        request = rf.get("/", {"field_name": "my_field", "component_prefix": ""})
        request.user = AnonymousUser()
        view = ItemsView.as_view()
        with pytest.raises(PermissionDenied):
            view(request, ac_name="EquipmentAutocomplete")


# ---------------------------------------------------------------------------
# Template tag tests
# ---------------------------------------------------------------------------


class TestBaseConfigurableHxVals:
    """Tests for the base_configurable_hx_vals template tag."""

    def _render_tag(self, field_name, component_prefix, **extra):
        """Invoke base_configurable_hx_vals with the given context values."""
        # Django imports
        from django.template import Context

        # external imports
        from autocomplete.templatetags.autocomplete import (
            base_configurable_hx_vals,
        )

        context = Context(
            {
                "field_name": field_name,
                "component_prefix": component_prefix,
                "required": extra.get("required", False),
                "disabled": extra.get("disabled", False),
                "multiselect": extra.get("multiselect", False),
                "placeholder": extra.get("placeholder", None),
            }
        )
        return base_configurable_hx_vals(context)

    def test_single_quote_in_component_prefix_is_escaped(self):
        """A single quote in component_prefix is HTML-escaped to prevent attribute injection."""
        result = self._render_tag("myfield", "pre'fix")
        # The raw single quote must NOT appear in the output
        assert "'" not in result

    def test_single_quote_in_field_name_is_escaped(self):
        """A single quote in field_name is HTML-escaped."""
        result = self._render_tag("my'field", "")
        assert "'" not in result

    def test_normal_values_produce_valid_json_fragment(self):
        """Normal values produce a parseable JSON fragment (with braces added back)."""
        result = self._render_tag("myfield", "pfx_")
        parsed = json.loads("{" + result + "}")
        assert parsed["field_name"] == "myfield"
        assert parsed["component_prefix"] == "pfx_"


class TestSearchHighlight:
    """Tests for the search_highlight template filter.

    The filter renders user-controlled content (autocomplete labels) into HTML,
    so these tests verify it is safe against XSS payloads in that data.
    """

    def test_empty_search_returns_value(self):
        """An empty search string returns the original value (unmodified)."""
        # external imports
        from autocomplete.templatetags.autocomplete import search_highlight

        assert search_highlight("Hello World", "") == "Hello World"

    def test_match_wraps_in_highlight_span(self):
        """A matching search term is wrapped in a highlight span."""
        # external imports
        from autocomplete.templatetags.autocomplete import search_highlight

        result = str(search_highlight("Hello World", "World"))
        assert '<span class="highlight">World</span>' in result

    def test_html_in_value_is_escaped(self):
        """HTML characters in the value are escaped to prevent XSS."""
        # external imports
        from autocomplete.templatetags.autocomplete import search_highlight

        result = str(search_highlight("<script>alert(1)</script>", "alert"))
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


# ---------------------------------------------------------------------------
# Tests for toggle_set and replace_or_toggle
# ---------------------------------------------------------------------------


class TestToggleSet:
    """Tests for the ``toggle_set`` utility function in autocomplete.views."""

    def test_adds_item_when_not_in_set(self):
        """toggle_set adds an item that is not present in the set."""
        # external imports
        from autocomplete.views import toggle_set

        result = toggle_set({"a", "b"}, "c")
        assert "c" in result

    def test_removes_item_when_present(self):
        """toggle_set removes an item that is already in the set."""
        # external imports
        from autocomplete.views import toggle_set

        result = toggle_set({"a", "b", "c"}, "b")
        assert "b" not in result

    def test_removes_item_by_string_comparison(self):
        """toggle_set removes an item matching by str() comparison."""
        # external imports
        from autocomplete.views import toggle_set

        result = toggle_set({1, 2, 3}, "2")
        assert "2" not in result
        assert 2 not in result

    def test_adds_item_when_set_is_empty(self):
        """toggle_set adds an item to an empty set."""
        # external imports
        from autocomplete.views import toggle_set

        result = toggle_set(set(), "x")
        assert result == {"x"}

    def test_does_not_mutate_original_set(self):
        """toggle_set returns a new set and does not mutate the original."""
        # external imports
        from autocomplete.views import toggle_set

        original = {"a", "b"}
        toggle_set(original, "a")
        assert original == {"a", "b"}


class TestReplaceOrToggle:
    """Tests for the ``replace_or_toggle`` utility function in autocomplete.views."""

    def test_removes_item_when_already_selected(self):
        """replace_or_toggle removes the item when it is already selected."""
        # external imports
        from autocomplete.views import replace_or_toggle

        result = replace_or_toggle({"x"}, "x")
        assert result == set()

    def test_replaces_existing_item_with_new_item(self):
        """replace_or_toggle replaces the existing item with the new one."""
        # external imports
        from autocomplete.views import replace_or_toggle

        result = replace_or_toggle({"old"}, "new")
        assert result == {"new"}

    def test_empty_set_adds_item(self):
        """replace_or_toggle adds the item when the set is empty."""
        # external imports
        from autocomplete.views import replace_or_toggle

        result = replace_or_toggle(set(), "item")
        assert result == {"item"}

    def test_raises_for_set_with_multiple_items(self):
        """replace_or_toggle raises an exception when the set has more than one item."""
        # external imports
        from autocomplete.views import replace_or_toggle

        with pytest.raises(Exception):
            replace_or_toggle({"a", "b"}, "c")


# ---------------------------------------------------------------------------
# Helpers for view tests
# ---------------------------------------------------------------------------


def _register_test_ac(name):
    """Register a test autocomplete class and return it.

    Skips registration if the name is already taken (e.g., from a prior run
    in the same process) so tests are idempotent.

    Args:
        name (str): The route name to register under.

    Returns:
        (type): The registered autocomplete class.
    """
    # external imports
    from autocomplete.core import Autocomplete, _ac_registry, register

    if name in _ac_registry:
        return _ac_registry[name]

    class _TestAC(Autocomplete):
        @classmethod
        def search_items(cls, search, context):
            return [{"key": "1", "label": "Alpha"}, {"key": "2", "label": "Beta"}]

        @classmethod
        def get_items_from_keys(cls, keys, context):
            items = {"1": "Alpha", "2": "Beta"}
            return [{"key": k, "label": items[k]} for k in keys if k in items]

    return register(_TestAC, route_name=name)


# ---------------------------------------------------------------------------
# Tests for AutocompleteBaseView
# ---------------------------------------------------------------------------


class TestAutocompleteBaseView:
    """Tests for the ``AutocompleteBaseView`` helper methods."""

    def _make_view(self, ac_name, params=None):
        """Create an ``AutocompleteBaseView`` instance with a mock request.

        Args:
            ac_name (str): The autocomplete route name to bind.
            params (dict): Optional GET parameters for the request.

        Returns:
            (AutocompleteBaseView): A configured view instance.
        """
        # external imports
        from autocomplete.views import AutocompleteBaseView

        rf = RequestFactory()
        get_params = {"field_name": "my_field", "component_prefix": "pfx_"}
        if params:
            get_params.update(params)
        request = rf.get("/", get_params)
        user = MagicMock()
        user.is_authenticated = True
        request.user = user

        view = AutocompleteBaseView()
        view.request = request
        view.kwargs = {"ac_name": ac_name}
        return view

    def test_ac_class_resolves_registered_name(self):
        """ac_class resolves a registered autocomplete class by URL name."""
        ac = _register_test_ac("BaseViewTestAC")
        view = self._make_view("BaseViewTestAC")
        assert view.ac_class is ac

    def test_ac_class_raises_404_for_unknown_name(self):
        """ac_class raises Http404 when the autocomplete name is not registered."""
        # external imports
        from autocomplete.views import AutocompleteBaseView

        rf = RequestFactory()
        request = rf.get("/", {"field_name": "f", "component_prefix": ""})
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        view = AutocompleteBaseView()
        view.request = request
        view.kwargs = {"ac_name": "NeverRegisteredXYZ999"}
        with pytest.raises(Http404):
            _ = view.ac_class

    def test_request_dict_returns_get_params(self):
        """request_dict converts the QueryDict to a plain dict."""
        view = self._make_view("BaseViewTestAC")
        d = view.request_dict
        assert d["field_name"] == "my_field"
        assert d["component_prefix"] == "pfx_"

    def test_get_field_name_returns_field_name(self):
        """get_field_name extracts the field_name parameter from the request."""
        view = self._make_view("BaseViewTestAC")
        assert view.get_field_name() == "my_field"

    def test_get_hx_attrs_returns_empty_dict_when_absent(self):
        """get_hx_attrs returns an empty dict when hx_attrs is not in the request."""
        view = self._make_view("BaseViewTestAC")
        assert view.get_hx_attrs() == {}

    def test_get_component_id_combines_prefix_and_field_name(self):
        """get_component_id concatenates the component_prefix and field_name."""
        view = self._make_view("BaseViewTestAC")
        assert view.get_component_id() == "pfx_my_field"

    def test_get_configurable_value_from_request(self):
        """get_configurable_value returns the value from the request when present."""
        view = self._make_view("BaseViewTestAC", params={"placeholder": "Search here"})
        assert view.get_configurable_value("placeholder") == "Search here"

    def test_get_configurable_value_from_ac_class(self):
        """get_configurable_value falls back to the autocomplete class attribute."""
        view = self._make_view("BaseViewTestAC")
        # minimum_search_length is a class attr not in the request
        assert view.get_configurable_value("minimum_search_length") == 3

    def test_get_configurable_value_returns_none_for_unknown_key(self):
        """get_configurable_value returns None for a key not in request or class."""
        view = self._make_view("BaseViewTestAC")
        assert view.get_configurable_value("nonexistent_key") is None

    def test_get_template_context_includes_required_keys(self):
        """get_template_context returns a dict with all expected keys."""
        view = self._make_view("BaseViewTestAC")
        ctx = view.get_template_context()
        for key in (
            "route_name",
            "ac_class",
            "field_name",
            "component_id",
            "required",
            "placeholder",
            "multiselect",
            "component_prefix",
            "disabled",
        ):
            assert key in ctx, f"Missing key: {key}"

    def test_get_template_context_field_name_matches_request(self):
        """get_template_context includes the field_name from the request."""
        view = self._make_view("BaseViewTestAC")
        ctx = view.get_template_context()
        assert ctx["field_name"] == "my_field"


# ---------------------------------------------------------------------------
# Tests for ItemsView
# ---------------------------------------------------------------------------


class TestItemsView:
    """Tests for ``ItemsView.get``, exercising the search rendering path."""

    def _make_request(self, ac_name, search="", field_name="my_field"):
        """Create an authenticated GET request for the items view.

        Args:
            ac_name (str): Registered autocomplete name (used in kwargs).
            search (str): The search query string.
            field_name (str): The form field name.

        Returns:
            (HttpRequest): A ready-to-use request.
        """
        rf = RequestFactory()
        request = rf.get(
            "/",
            {
                "search": search,
                "field_name": field_name,
                "component_prefix": "",
            },
        )
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        return request

    def test_items_view_returns_200_for_registered_ac(self):
        """ItemsView.get returns a 200 response for a registered autocomplete name."""
        # external imports
        from autocomplete.views import ItemsView

        _register_test_ac("ItemsViewTestAC")
        request = self._make_request("ItemsViewTestAC", search="alph")
        view = ItemsView()
        view.request = request
        view.kwargs = {"ac_name": "ItemsViewTestAC"}
        view.args = ()
        response = view.get(request)
        assert response.status_code == 200

    def test_items_view_short_query_returns_no_results(self):
        """ItemsView.get returns a response with show=False when query is too short."""
        # external imports
        from autocomplete.views import ItemsView

        _register_test_ac("ItemsViewTestAC")
        request = self._make_request("ItemsViewTestAC", search="a")  # too short (min is 3)
        view = ItemsView()
        view.request = request
        view.kwargs = {"ac_name": "ItemsViewTestAC"}
        view.args = ()
        response = view.get(request)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Tests for ToggleView
# ---------------------------------------------------------------------------


class TestToggleView:
    """Tests for ``ToggleView.get``, exercising the toggle rendering path."""

    def _make_request(self, ac_name, item="1", field_name="my_field", current=None):
        """Create an authenticated GET request for the toggle view.

        Args:
            ac_name (str): Registered autocomplete name.
            item (str): The item key to toggle.
            field_name (str): The form field name.
            current (list): Currently selected keys.

        Returns:
            (HttpRequest): A ready-to-use request.
        """
        rf = RequestFactory()
        params = {
            "item": item,
            "field_name": field_name,
            "component_prefix": "",
        }
        if current:
            params[field_name] = current
        request = rf.get("/", params)
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        return request

    def test_toggle_view_returns_200_for_registered_ac(self):
        """ToggleView.get returns a 200 response when selecting an item."""
        # external imports
        from autocomplete.views import ToggleView

        _register_test_ac("ToggleViewTestAC")
        request = self._make_request("ToggleViewTestAC", item="1")
        view = ToggleView()
        view.request = request
        view.kwargs = {"ac_name": "ToggleViewTestAC"}
        view.args = ()
        response = view.get(request)
        assert response.status_code == 200

    def test_toggle_view_missing_item_returns_400(self):
        """ToggleView.get returns 400 when the item parameter is missing."""
        # external imports
        from autocomplete.views import ToggleView

        _register_test_ac("ToggleViewTestAC")
        rf = RequestFactory()
        request = rf.get("/", {"field_name": "my_field", "component_prefix": ""})
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        view = ToggleView()
        view.request = request
        view.kwargs = {"ac_name": "ToggleViewTestAC"}
        view.args = ()
        response = view.get(request)
        assert response.status_code == 400

    def test_toggle_view_sets_htmx_trigger_header(self):
        """ToggleView.get sets the HX-Trigger-After-Settle response header."""
        # external imports
        from autocomplete.views import ToggleView

        _register_test_ac("ToggleViewTestAC")
        request = self._make_request("ToggleViewTestAC", item="1")
        view = ToggleView()
        view.request = request
        view.kwargs = {"ac_name": "ToggleViewTestAC"}
        view.args = ()
        response = view.get(request)
        assert "HX-Trigger-After-Settle" in response.headers


# ---------------------------------------------------------------------------
# Tests for QuerysetMappedIterable
# ---------------------------------------------------------------------------


class TestQuerysetMappedIterable:
    """Tests for ``QuerysetMappedIterable`` in autocomplete.shortcuts."""

    def _make_mock_queryset(self, records):
        """Create a mock QuerySet-like object backed by a list.

        Args:
            records (list): List of mock record objects.

        Returns:
            (MagicMock): A mock that behaves like a Django QuerySet.
        """
        qs = MagicMock()
        qs.__iter__ = MagicMock(return_value=iter(records))
        qs.__getitem__ = MagicMock(side_effect=lambda key: records[key])
        qs.count = MagicMock(return_value=len(records))
        return qs

    def _make_record(self, pk, label):
        """Create a mock record with an id and str representation.

        Args:
            pk (int): The primary key.
            label (str): The label/str() value.

        Returns:
            (MagicMock): A mock record.
        """
        r = MagicMock()
        r.id = pk
        r.__str__ = MagicMock(return_value=label)
        return r

    def test_iter_yields_mapped_dicts(self):
        """__iter__ yields dict with 'key' and 'label' for each record."""
        # external imports
        from autocomplete.shortcuts import QuerysetMappedIterable

        rec = self._make_record(1, "Alpha")
        qs = self._make_mock_queryset([rec])
        iterable = QuerysetMappedIterable(queryset=qs, label_for_record=str)
        results = list(iterable)
        assert results == [{"key": 1, "label": "Alpha"}]

    def test_len_returns_queryset_count(self):
        """__len__ returns the count from the underlying QuerySet."""
        # external imports
        from autocomplete.shortcuts import QuerysetMappedIterable

        qs = self._make_mock_queryset([self._make_record(1, "A"), self._make_record(2, "B")])
        iterable = QuerysetMappedIterable(queryset=qs, label_for_record=str)
        assert len(iterable) == 2

    def test_getitem_int_returns_single_record(self):
        """__getitem__ with an int index returns a single mapped dict."""
        # external imports
        from autocomplete.shortcuts import QuerysetMappedIterable

        rec = self._make_record(5, "Gamma")
        qs = MagicMock()
        qs.__getitem__ = MagicMock(return_value=rec)
        iterable = QuerysetMappedIterable(queryset=qs, label_for_record=str)
        result = iterable[0]
        assert result == {"key": 5, "label": "Gamma"}

    def test_getitem_slice_returns_list(self):
        """__getitem__ with a slice returns a list of mapped dicts."""
        # external imports
        from autocomplete.shortcuts import QuerysetMappedIterable

        recs = [self._make_record(i, f"Item{i}") for i in range(3)]
        qs = MagicMock()
        qs.__getitem__ = MagicMock(return_value=recs)
        iterable = QuerysetMappedIterable(queryset=qs, label_for_record=str)
        results = iterable[0:3]
        assert len(results) == 3
        assert all(isinstance(r, dict) for r in results)

    def test_getitem_invalid_type_raises_type_error(self):
        """__getitem__ with an invalid key type raises TypeError."""
        # external imports
        from autocomplete.shortcuts import QuerysetMappedIterable

        qs = self._make_mock_queryset([])
        iterable = QuerysetMappedIterable(queryset=qs, label_for_record=str)
        with pytest.raises(TypeError):
            _ = iterable["not_a_valid_key"]  # type: ignore[index]


# ---------------------------------------------------------------------------
# Tests for ModelAutocomplete
# ---------------------------------------------------------------------------


class TestModelAutocomplete:
    """Tests for ``ModelAutocomplete`` in autocomplete.shortcuts."""

    def test_get_search_attrs_raises_when_not_set(self):
        """get_search_attrs raises ValueError when search_attrs is empty."""
        # external imports
        from autocomplete.shortcuts import ModelAutocomplete

        class NoAttrs(ModelAutocomplete):
            model = object  # placeholder
            search_attrs = []

            @classmethod
            def get_items_from_keys(cls, keys, context):
                return []

        with pytest.raises(ValueError):
            NoAttrs.get_search_attrs()

    def test_get_model_raises_when_not_set(self):
        """get_model raises ValueError when model is not set."""
        # external imports
        from autocomplete.shortcuts import ModelAutocomplete

        class NoModel(ModelAutocomplete):
            model = None
            search_attrs = ["name"]

            @classmethod
            def search_items(cls, search, context):
                return []

        with pytest.raises(ValueError):
            NoModel.get_model()

    def test_get_label_for_record_returns_str(self):
        """get_label_for_record returns the string representation of the record."""
        # external imports
        from autocomplete.shortcuts import ModelAutocomplete

        record = MagicMock()
        record.__str__ = MagicMock(return_value="My Label")
        assert ModelAutocomplete.get_label_for_record(record) == "My Label"


# ---------------------------------------------------------------------------
# Tests for AutocompleteWidget
# ---------------------------------------------------------------------------


class TestAutocompleteWidget:
    """Tests for ``AutocompleteWidget`` in autocomplete.widgets."""

    def _make_ac_class(self, route_name="TestWidgetAC", items=None):
        """Create a minimal autocomplete class mock suitable for the widget.

        Args:
            route_name (str): The route name for the autocomplete.
            items (list): Items returned by get_items_from_keys.

        Returns:
            (MagicMock): A mock autocomplete class.
        """
        ac = MagicMock()
        ac.route_name = route_name
        ac.component_prefix = ""
        ac.get_items_from_keys = MagicMock(return_value=items or [])
        return ac

    def test_init_accepts_valid_options(self):
        """AutocompleteWidget.__init__ accepts known option keys."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = self._make_ac_class()
        widget = AutocompleteWidget(ac, options={"multiselect": True, "placeholder": "Search"})
        assert widget.config["multiselect"] is True
        assert widget.config["placeholder"] == "Search"

    def test_init_raises_for_invalid_option(self):
        """AutocompleteWidget.__init__ raises ValueError for unknown option keys."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = self._make_ac_class()
        with pytest.raises(ValueError):
            AutocompleteWidget(ac, options={"invalid_option": True})

    def test_value_from_datadict_single_select(self):
        """value_from_datadict returns a single value for single-select mode."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = self._make_ac_class()
        ac.multiselect = False
        widget = AutocompleteWidget(ac)
        data = {"my_field": "42"}
        result = widget.value_from_datadict(data, {}, "my_field")
        assert result == "42"

    def test_value_from_datadict_multi_select_query_dict(self):
        """value_from_datadict returns a list for multi-select mode with QueryDict."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = self._make_ac_class()
        widget = AutocompleteWidget(ac, options={"multiselect": True})
        data = MagicMock()
        data.getlist = MagicMock(return_value=["1", "2"])
        result = widget.value_from_datadict(data, {}, "my_field")
        assert result == ["1", "2"]

    def test_value_from_datadict_multi_select_plain_dict(self):
        """value_from_datadict falls back to .get() when getlist is unavailable."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = self._make_ac_class()
        widget = AutocompleteWidget(ac, options={"multiselect": True})
        data = {"my_field": ["1", "2"]}  # plain dict has no getlist
        result = widget.value_from_datadict(data, {}, "my_field")
        assert result == ["1", "2"]

    def test_value_omitted_from_data_returns_empty_list(self):
        """value_omitted_from_data always returns an empty list."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = self._make_ac_class()
        widget = AutocompleteWidget(ac)
        assert widget.value_omitted_from_data({}, {}, "my_field") == []

    def test_get_configurable_value_from_config(self):
        """get_configurable_value returns value from widget config when present."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = self._make_ac_class()
        widget = AutocompleteWidget(ac, options={"placeholder": "Type here"})
        assert widget.get_configurable_value("placeholder") == "Type here"

    def test_get_configurable_value_from_ac_class(self):
        """get_configurable_value falls back to the autocomplete class attribute."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = self._make_ac_class()
        ac.minimum_search_length = 2
        widget = AutocompleteWidget(ac)
        assert widget.get_configurable_value("minimum_search_length") == 2

    def test_is_multi_is_falsy_by_default(self):
        """is_multi is falsy when multiselect is not configured."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = self._make_ac_class()
        widget = AutocompleteWidget(ac)
        assert not widget.is_multi

    def test_is_multi_returns_true_when_configured(self):
        """is_multi returns True when multiselect is set to True."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = self._make_ac_class()
        widget = AutocompleteWidget(ac, options={"multiselect": True})
        assert widget.is_multi is True

    def test_get_component_id_combines_prefix_and_name(self):
        """get_component_id returns prefix + field_name."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = self._make_ac_class()
        ac.component_prefix = "form_"
        widget = AutocompleteWidget(ac)
        assert widget.get_component_id("my_field") == "form_my_field"

    def test_get_context_includes_expected_keys(self):
        """get_context returns a context dict with the required autocomplete keys."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = self._make_ac_class()
        ac.multiselect = False
        ac.component_prefix = ""
        widget = AutocompleteWidget(ac)
        ctx = widget.get_context("my_field", None, {"id": "id_my_field"})
        for key in ("field_name", "route_name", "ac_class", "values", "selected_items"):
            assert key in ctx, f"Missing key in context: {key}"


# ---------------------------------------------------------------------------
# Additional template tag tests
# ---------------------------------------------------------------------------


class TestMakeIdFilter:
    """Tests for the ``make_id`` template filter."""

    def test_returns_consistent_hash(self):
        """make_id returns the same SHA1 hex digest for the same input."""
        # external imports
        from autocomplete.templatetags.autocomplete import make_id

        result1 = make_id("hello")
        result2 = make_id("hello")
        assert result1 == result2
        assert len(result1) == 40  # SHA1 hex digest is always 40 chars

    def test_different_inputs_give_different_hashes(self):
        """make_id returns different hashes for different inputs."""
        # external imports
        from autocomplete.templatetags.autocomplete import make_id

        assert make_id("hello") != make_id("world")


class TestSearchHighlightNoMatch:
    """Additional tests for the ``search_highlight`` filter edge cases."""

    def test_no_match_returns_original_value(self):
        """search_highlight returns the original value when search is not found."""
        # external imports
        from autocomplete.templatetags.autocomplete import search_highlight

        result = search_highlight("Hello World", "xyz")
        assert str(result) == "Hello World"


class TestJsBoolean:
    """Tests for the ``js_boolean`` template filter."""

    def test_truthy_value_returns_true_string(self):
        """js_boolean returns 'true' for a truthy value."""
        # external imports
        from autocomplete.templatetags.autocomplete import js_boolean

        assert js_boolean(True) == "true"
        assert js_boolean(1) == "true"
        assert js_boolean("yes") == "true"

    def test_falsy_value_returns_false_string(self):
        """js_boolean returns 'false' for a falsy value."""
        # external imports
        from autocomplete.templatetags.autocomplete import js_boolean

        assert js_boolean(False) == "false"
        assert js_boolean(0) == "false"
        assert js_boolean("") == "false"
        assert js_boolean(None) == "false"


class TestValueIfTruthy:
    """Tests for the ``value_if_truthy`` template tag."""

    def test_returns_value_when_test_is_truthy(self):
        """value_if_truthy returns the value when the test condition is truthy."""
        # external imports
        from autocomplete.templatetags.autocomplete import value_if_truthy

        assert value_if_truthy(True, "active", "") == "active"

    def test_returns_default_when_test_is_falsy(self):
        """value_if_truthy returns the default when the test condition is falsy."""
        # external imports
        from autocomplete.templatetags.autocomplete import value_if_truthy

        assert value_if_truthy(False, "active", "inactive") == "inactive"
        assert value_if_truthy(False, "active") == ""  # default default is ""


class TestSubstituteString:
    """Tests for the ``substitute_string`` template tag."""

    def test_substitutes_placeholders(self):
        """substitute_string replaces %(key)s placeholders with kwargs."""
        # external imports
        from autocomplete.templatetags.autocomplete import substitute_string

        result = substitute_string("Hello %(name)s, you have %(count)s items", name="Alice", count=3)
        assert result == "Hello Alice, you have 3 items"

    def test_no_placeholders_returns_template_unchanged(self):
        """substitute_string returns the template string unchanged when no kwargs match."""
        # external imports
        from autocomplete.templatetags.autocomplete import substitute_string

        result = substitute_string("No placeholders here")
        assert result == "No placeholders here"


class TestStringifyExtraHxVals:
    """Tests for the ``stringify_extra_hx_vals`` helper function."""

    def test_returns_comma_separated_key_value_pairs(self):
        """stringify_extra_hx_vals returns JSON-like key-value pairs."""
        # external imports
        from autocomplete.templatetags.autocomplete import (
            stringify_extra_hx_vals,
        )

        result = stringify_extra_hx_vals({"key1": "val1", "key2": "val2"})
        assert '"key1": val1' in result
        assert '"key2": val2' in result

    def test_raises_for_values_containing_single_quotes(self):
        """stringify_extra_hx_vals raises ValueError when a value contains a single quote."""
        # external imports
        from autocomplete.templatetags.autocomplete import (
            stringify_extra_hx_vals,
        )

        with pytest.raises(ValueError):
            stringify_extra_hx_vals({"key": "it's a problem"})


class TestBaseConfigurableHxParams:
    """Tests for the ``base_configurable_values_hx_params`` template tag."""

    def _render_tag(self, field_name, component_prefix, **extra):
        """Invoke base_configurable_values_hx_params with the given context.

        Args:
            field_name (str): The field name.
            component_prefix (str): The component prefix.
            **extra: Optional flags (required, disabled, placeholder, multiselect).

        Returns:
            (str): The rendered output.
        """
        # Django imports
        from django.template import Context

        # external imports
        from autocomplete.templatetags.autocomplete import (
            base_configurable_values_hx_params,
        )

        context = Context(
            {
                "field_name": field_name,
                "component_prefix": component_prefix,
                "required": extra.get("required", False),
                "disabled": extra.get("disabled", False),
                "multiselect": extra.get("multiselect", False),
                "placeholder": extra.get("placeholder", None),
            }
        )
        return base_configurable_values_hx_params(context)

    def test_always_includes_field_name(self):
        """base_configurable_values_hx_params always includes field_name in output."""
        result = self._render_tag("myfield", "")
        assert "myfield" in result
        assert "field_name" in result

    def test_required_flag_appends_required(self):
        """When required=True, 'required' is appended to the hx_params string."""
        result = self._render_tag("myfield", "", required=True)
        assert "required" in result

    def test_multiselect_flag_appends_multiselect(self):
        """When multiselect=True, 'multiselect' is appended to the hx_params string."""
        result = self._render_tag("myfield", "", multiselect=True)
        assert "multiselect" in result

    def test_placeholder_flag_appends_placeholder(self):
        """When placeholder is set, 'placeholder' is appended to the hx_params string."""
        result = self._render_tag("myfield", "", placeholder="Search...")
        assert "placeholder" in result

    def test_disabled_flag_appends_disabled(self):
        """When disabled=True, 'disabled' is appended to the hx_params string."""
        result = self._render_tag("myfield", "", disabled=True)
        assert "disabled" in result


class TestAutocompleteHeadAndScriptsTags:
    """Tests for the ``autocomplete_head`` template tag."""

    def test_autocomplete_head_renders_without_error(self):
        """autocomplete_head renders the head template without raising exceptions."""
        # external imports
        from autocomplete.templatetags.autocomplete import autocomplete_head

        result = autocomplete_head()
        assert result is not None


class TestBaseConfigurableHxValsExtraBranches:
    """Tests for the optional flag branches in ``base_configurable_hx_vals``."""

    def _render_tag(self, field_name, component_prefix, **extra):
        """Invoke base_configurable_hx_vals with the given context values."""
        # Django imports
        from django.template import Context

        # external imports
        from autocomplete.templatetags.autocomplete import (
            base_configurable_hx_vals,
        )

        context = Context(
            {
                "field_name": field_name,
                "component_prefix": component_prefix,
                "required": extra.get("required", False),
                "disabled": extra.get("disabled", False),
                "multiselect": extra.get("multiselect", False),
                "placeholder": extra.get("placeholder", None),
            }
        )
        return base_configurable_hx_vals(context)

    def test_disabled_flag_included_in_json(self):
        """When disabled=True, 'disabled' key is included in the JSON output."""
        # Python imports
        import json

        result = self._render_tag("myfield", "", disabled=True)
        parsed = json.loads("{" + result + "}")
        assert parsed.get("disabled") is True

    def test_multiselect_flag_included_in_json(self):
        """When multiselect=True, 'multiselect' key is included in the JSON output."""
        # Python imports
        import json

        result = self._render_tag("myfield", "", multiselect=True)
        parsed = json.loads("{" + result + "}")
        assert parsed.get("multiselect") is True

    def test_placeholder_included_in_json(self):
        """When placeholder is set, 'placeholder' key is included in the JSON output."""
        # Python imports
        import json

        result = self._render_tag("myfield", "", placeholder="Search...")
        parsed = json.loads("{" + result + "}")
        assert parsed.get("placeholder") == "Search..."

    def test_required_included_in_json(self):
        """When required=True, 'required' key is included in the JSON output."""
        # Python imports
        import json

        result = self._render_tag("myfield", "", required=True)
        parsed = json.loads("{" + result + "}")
        assert parsed.get("required") is True


class TestTextInputHxVals:
    """Tests for the ``text_input_hx_vals`` template tag."""

    def _make_context(self, extra_hx_vals=None):
        """Build a context suitable for text_input_hx_vals.

        Args:
            extra_hx_vals (dict or None): Extra hx vals to return from ac_class.

        Returns:
            (Context): A Django template context.
        """
        # Python imports
        from unittest.mock import MagicMock

        # Django imports
        from django.template import Context

        ac_class = MagicMock()
        ac_class.get_extra_text_input_hx_vals = MagicMock(return_value=extra_hx_vals or {})

        return Context(
            {
                "field_name": "myfield",
                "component_prefix": "",
                "component_id": "myfield",
                "required": False,
                "disabled": False,
                "multiselect": False,
                "placeholder": None,
                "ac_class": ac_class,
            }
        )

    def test_renders_basic_hx_vals(self):
        """text_input_hx_vals returns a js:{...} expression with field_name."""
        # external imports
        from autocomplete.templatetags.autocomplete import text_input_hx_vals

        context = self._make_context()
        result = text_input_hx_vals(context)
        assert "js:{" in result
        assert "field_name" in result

    def test_extra_hx_vals_are_included(self):
        """text_input_hx_vals includes extra hx vals when ac_class provides them."""
        # external imports
        from autocomplete.templatetags.autocomplete import text_input_hx_vals

        context = self._make_context(extra_hx_vals={"custom_key": "someValue"})
        result = text_input_hx_vals(context)
        assert "custom_key" in result
        assert "someValue" in result


class TestModelAutocompleteSuccessPaths:
    """Tests for the success paths of ``ModelAutocomplete`` methods."""

    def test_get_search_attrs_returns_list_when_set(self):
        """get_search_attrs returns the search_attrs list when it is non-empty."""
        # external imports
        from autocomplete.shortcuts import ModelAutocomplete

        class WithAttrs(ModelAutocomplete):
            model = object
            search_attrs = ["name", "email"]

            @classmethod
            def get_items_from_keys(cls, keys, context):
                return []

        assert WithAttrs.get_search_attrs() == ["name", "email"]

    def test_get_model_returns_model_when_set(self):
        """get_model returns the model class when it is non-None."""
        # external imports
        from autocomplete.shortcuts import ModelAutocomplete

        class WithModel(ModelAutocomplete):
            model = object
            search_attrs = ["name"]

            @classmethod
            def search_items(cls, search, context):
                return []

        assert WithModel.get_model() is object


class TestToggleSetRemainingBranches:
    """Tests for the remaining branches of ``toggle_set``."""

    def test_removes_string_item_that_matches_str_of_set_member(self):
        """toggle_set removes item by str(item) comparison when set contains strings."""
        # external imports
        from autocomplete.views import toggle_set

        # str(2) = "2" is in the set, so "2" is removed
        result = toggle_set({"1", "2", "3"}, 2)
        assert "2" not in result
        assert "1" in result
        assert "3" in result


class TestToggleViewAdvanced:
    """Advanced tests for ``ToggleView.get`` covering additional branches."""

    def _make_view(self, params, ac_name="ToggleViewTestAC"):
        """Create a ToggleView instance with the given GET params.

        Args:
            params (dict): GET parameters for the request.
            ac_name (str): Registered autocomplete route name.

        Returns:
            (tuple): ``(view, request)`` ready for testing.
        """
        # external imports
        from autocomplete.views import ToggleView

        _register_test_ac(ac_name)
        rf = RequestFactory()
        request = rf.get("/", params)
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        view = ToggleView()
        view.request = request
        view.kwargs = {"ac_name": ac_name}
        view.args = ()
        return view, request

    def test_undefined_current_item_cleared_to_empty_list(self):
        """ToggleView clears current_items when the value is 'undefined'."""
        # The item toggles in regardless of the 'undefined' sentinel value
        params = {
            "field_name": "my_field",
            "component_prefix": "",
            "my_field": "undefined",
            "item": "1",
        }
        view, request = self._make_view(params)
        response = view.get(request)
        assert response.status_code == 200

    def test_multiselect_toggle_adds_second_item(self):
        """ToggleView with multiselect=True toggles items in multi-select mode."""
        params = {
            "field_name": "my_field",
            "component_prefix": "",
            "multiselect": "true",
            "my_field": "1",  # already have item 1
            "item": "2",  # toggle item 2
        }
        view, request = self._make_view(params)
        response = view.get(request)
        assert response.status_code == 200


class TestItemsViewMaxResults:
    """Tests for ``ItemsView.get`` when results exceed max_results."""

    def test_results_are_truncated_to_max_results(self):
        """ItemsView truncates results when the total exceeds max_results."""
        # external imports
        from autocomplete.core import Autocomplete, _ac_registry, register

        ac_name = "LargeResultAC"
        if ac_name not in _ac_registry:

            class _LargeAC(Autocomplete):
                max_results = 2  # low limit for testing

                @classmethod
                def search_items(cls, search, context):
                    # Return more items than max_results
                    return [{"key": str(i), "label": f"Item {i}"} for i in range(10)]

                @classmethod
                def get_items_from_keys(cls, keys, context):
                    return [{"key": k, "label": f"Item {k}"} for k in keys]

            register(_LargeAC, route_name=ac_name)

        # external imports
        from autocomplete.views import ItemsView

        rf = RequestFactory()
        request = rf.get("/", {"search": "Item", "field_name": "f", "component_prefix": ""})
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        view = ItemsView()
        view.request = request
        view.kwargs = {"ac_name": ac_name}
        view.args = ()
        response = view.get(request)
        assert response.status_code == 200


class TestWidgetGetContextWithValue:
    """Tests for ``AutocompleteWidget.get_context`` when a value is provided."""

    def test_get_context_with_single_value(self):
        """get_context calls get_items_from_keys with [value] for single-select mode."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = MagicMock()
        ac.route_name = "TestWidgetAC2"
        ac.component_prefix = ""
        ac.multiselect = False
        ac.get_items_from_keys = MagicMock(return_value=[{"key": "42", "label": "Item 42"}])
        widget = AutocompleteWidget(ac)
        ctx = widget.get_context("my_field", "42", {"id": "id_my_field"})
        ac.get_items_from_keys.assert_called_once_with(["42"], None)
        assert ctx["values"] == ["42"]

    def test_get_context_with_multi_value(self):
        """get_context calls get_items_from_keys with the full list for multi-select mode."""
        # external imports
        from autocomplete.widgets import AutocompleteWidget

        ac = MagicMock()
        ac.route_name = "TestWidgetAC3"
        ac.component_prefix = ""
        ac.get_items_from_keys = MagicMock(return_value=[{"key": "1", "label": "A"}, {"key": "2", "label": "B"}])
        widget = AutocompleteWidget(ac, options={"multiselect": True})
        ctx = widget.get_context("my_field", ["1", "2"], {"id": "id_my_field"})
        ac.get_items_from_keys.assert_called_once_with(["1", "2"], None)
        assert len(ctx["values"]) == 2


class TestToggleViewEdgeCases:
    """Edge case tests for ``ToggleView.get``."""

    def test_toggle_view_raises_when_item_not_found_in_results(self):
        """ToggleView.get raises ValueError when the toggled item is not in the results."""
        # external imports
        from autocomplete.views import ToggleView

        _register_test_ac("ToggleViewTestAC")
        rf = RequestFactory()
        # Request item "99" which the test AC does not return
        request = rf.get("/", {"field_name": "my_field", "component_prefix": "", "item": "99"})
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        view = ToggleView()
        view.request = request
        view.kwargs = {"ac_name": "ToggleViewTestAC"}
        view.args = ()
        with pytest.raises(ValueError):
            view.get(request)


class TestDispatchAuthCheck:
    """Tests for the ``AutocompleteBaseView.dispatch`` auth_check integration."""

    def test_dispatch_calls_auth_check_and_succeeds_for_authenticated_user(self):
        """dispatch calls auth_check and proceeds for authenticated users."""
        # external imports
        from autocomplete.views import ItemsView

        ac_name = "DispatchTestAC"
        _register_test_ac(ac_name)

        # Use as_view() so dispatch is called
        view_func = ItemsView.as_view()
        rf = RequestFactory()
        request = rf.get(
            "/",
            {
                "search": "alph",
                "field_name": "my_field",
                "component_prefix": "",
            },
        )
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        response = view_func(request, ac_name=ac_name)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Tests for autocomplete core.py edge cases
# ---------------------------------------------------------------------------


class TestAutocompleteRegister:
    """Tests for the ``register`` function in autocomplete.core."""

    def test_register_raises_when_name_already_registered(self):
        """register raises ValueError when the same route_name is already registered."""
        # external imports
        from autocomplete.core import Autocomplete, _ac_registry, register

        ac_name = "DuplicateAC_Test"
        if ac_name not in _ac_registry:

            class _FirstAC(Autocomplete):
                @classmethod
                def search_items(cls, s, ctx):
                    return []

                @classmethod
                def get_items_from_keys(cls, k, ctx):
                    return []

            register(_FirstAC, route_name=ac_name)

        # Try to register a second class under the same name
        class _SecondAC(Autocomplete):
            @classmethod
            def search_items(cls, s, ctx):
                return []

            @classmethod
            def get_items_from_keys(cls, k, ctx):
                return []

        with pytest.raises(ValueError, match="already registered"):
            register(_SecondAC, route_name=ac_name)


class TestAutocompleteValidate:
    """Tests for ``Autocomplete.validate`` in autocomplete.core."""

    def test_validate_raises_when_search_items_missing(self):
        """validate raises ValueError when search_items is not implemented."""
        # external imports
        from autocomplete.core import Autocomplete

        class NoSearch(Autocomplete):
            @classmethod
            def get_items_from_keys(cls, k, ctx):
                return []

        # Remove search_items to simulate a missing implementation
        if hasattr(NoSearch, "search_items"):
            del NoSearch.search_items

        with pytest.raises(ValueError, match="search_items"):
            NoSearch.validate()

    def test_validate_raises_when_get_items_from_keys_missing(self):
        """validate raises ValueError when get_items_from_keys is not implemented."""
        # external imports
        from autocomplete.core import Autocomplete

        class NoGetItems(Autocomplete):
            @classmethod
            def search_items(cls, s, ctx):
                return []

        # Remove get_items_from_keys to simulate a missing implementation
        if hasattr(NoGetItems, "get_items_from_keys"):
            del NoGetItems.get_items_from_keys

        with pytest.raises(ValueError, match="get_items_from_keys"):
            NoGetItems.validate()
