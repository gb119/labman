"""Tests for the autocomplete app security fixes.

This module tests authentication enforcement, error handling, and XSS-prevention
measures in the autocomplete component.
"""

# Python imports
import json

# Django imports
import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import RequestFactory


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
        from autocomplete.core import Autocomplete

        request = self._make_request(authenticated=False)
        with pytest.raises(PermissionDenied):
            Autocomplete.auth_check(request)

    def test_authenticated_user_is_allowed(self):
        """auth_check does not raise for an authenticated user."""
        from autocomplete.core import Autocomplete

        request = self._make_request(authenticated=True)
        # Should not raise
        Autocomplete.auth_check(request)

    def test_allow_unauthenticated_setting_permits_anonymous(self, settings):
        """Setting AUTOCOMPLETE_ALLOW_UNAUTHENTICATED=True permits anonymous access."""
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
        from unittest.mock import MagicMock

        rf = RequestFactory()
        request = rf.get("/", {"field_name": "my_field", "component_prefix": ""})
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        return request

    def test_items_view_unknown_ac_name_raises_404(self):
        """ItemsView raises Http404 when given an unregistered autocomplete name."""
        from autocomplete.views import ItemsView

        request = self._make_authenticated_request()
        view = ItemsView.as_view()
        with pytest.raises(Http404):
            view(request, ac_name="DoesNotExist__XYZ")

    def test_toggle_view_unknown_ac_name_raises_404(self):
        """ToggleView raises Http404 when given an unregistered autocomplete name."""
        from autocomplete.views import ToggleView

        request = self._make_authenticated_request()
        view = ToggleView.as_view()
        with pytest.raises(Http404):
            view(request, ac_name="DoesNotExist__XYZ")

    def test_items_view_unauthenticated_raises_permission_denied(self):
        """ItemsView raises PermissionDenied when accessed without authentication."""
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
        from django.template import Context

        from autocomplete.templatetags.autocomplete import base_configurable_hx_vals

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
        from autocomplete.templatetags.autocomplete import search_highlight

        assert search_highlight("Hello World", "") == "Hello World"

    def test_match_wraps_in_highlight_span(self):
        """A matching search term is wrapped in a highlight span."""
        from autocomplete.templatetags.autocomplete import search_highlight

        result = str(search_highlight("Hello World", "World"))
        assert '<span class="highlight">World</span>' in result

    def test_html_in_value_is_escaped(self):
        """HTML characters in the value are escaped to prevent XSS."""
        from autocomplete.templatetags.autocomplete import search_highlight

        result = str(search_highlight("<script>alert(1)</script>", "alert"))
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
