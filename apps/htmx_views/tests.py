# -*- coding: utf-8 -*-
"""Tests for the htmx_views app.

This module tests the pure-Python view logic provided by the htmx_views app:

- ``temp_attr`` context manager
- ``dispatch`` HTMX-aware dispatch function (monkey-patched onto ``View``)
- ``HTMXProcessMixin`` — trigger-based routing for all HTTP verbs, template
  selection, and context-data delegation
- ``HTMXFormMixin`` — form_valid / form_invalid HTMX delegation

All tests here are pure unit tests that do **not** require database access.
"""
# Python imports
from unittest.mock import MagicMock

# Django imports
import pytest
from django.http import HttpResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _MockHtmx:
    """Minimal stand-in for django_htmx.middleware.HtmxDetails."""

    def __init__(self, trigger_name=None, trigger=None, target=None):
        self.trigger_name = trigger_name
        self.trigger = trigger
        self.target = target


def _make_request(method="GET", htmx=None):
    """Build a minimal mock request.

    Args:
        method (str): HTTP verb.
        htmx: Value for ``request.htmx``; falsy → non-HTMX request.

    Returns:
        (MagicMock): A mock request object.
    """
    req = MagicMock()
    req.method = method
    req.htmx = htmx or False
    return req


class _StubBase:
    """Minimal base class implementing the methods that mixins call via super()."""

    template_name = "stub.html"

    def get_template_names(self):
        return [self.template_name]

    def get_context_data(self, **kwargs):
        return {"base": True, **kwargs}

    def get_context_object_name(self, object_list):
        return "base_list"

    def form_valid(self, form):
        return HttpResponse("super_form_valid")

    def form_invalid(self, form):
        return HttpResponse("super_form_invalid")

    def http_method_not_allowed(self, request, *args, **kwargs):
        return HttpResponse("method_not_allowed", status=405)


# ---------------------------------------------------------------------------
# Tests for temp_attr
# ---------------------------------------------------------------------------

class TestTempAttr:
    """Tests for the ``temp_attr`` context manager."""

    def test_sets_attribute_while_inside_block(self):
        """The attribute is updated to the new value inside the block."""
        from htmx_views.views import temp_attr

        obj = MagicMock()
        obj.flag = False
        with temp_attr(obj, "flag", True):
            assert obj.flag is True

    def test_restores_original_value_after_block(self):
        """The original attribute value is restored after the block exits."""
        from htmx_views.views import temp_attr

        obj = MagicMock()
        obj.flag = "original"
        with temp_attr(obj, "flag", "temporary"):
            pass
        assert obj.flag == "original"

    def test_creates_attribute_when_it_does_not_exist(self):
        """An attribute that did not exist is created inside the block."""
        from htmx_views.views import temp_attr

        class Plain:
            pass

        obj = Plain()
        with temp_attr(obj, "new_attr", 42):
            assert obj.new_attr == 42

    def test_deletes_attribute_after_block_when_it_did_not_exist(self):
        """An attribute that was created by the context manager is deleted on exit."""
        from htmx_views.views import temp_attr

        class Plain:
            pass

        obj = Plain()
        with temp_attr(obj, "new_attr", 42):
            pass
        assert not hasattr(obj, "new_attr")

    def test_restores_attribute_when_exception_is_raised(self):
        """The original value is restored even if an exception occurs inside the block."""
        from htmx_views.views import temp_attr

        obj = MagicMock()
        obj.flag = "original"
        with pytest.raises(RuntimeError):
            with temp_attr(obj, "flag", "temporary"):
                raise RuntimeError("boom")
        assert obj.flag == "original"


# ---------------------------------------------------------------------------
# Tests for dispatch
# ---------------------------------------------------------------------------

class TestDispatch:
    """Tests for the monkey-patched HTMX-aware ``dispatch`` function."""

    def _make_view(self, http_method_names=None):
        """Create a mock view object suitable for calling dispatch."""
        from htmx_views.views import dispatch

        view = MagicMock()
        view.http_method_names = http_method_names or ["get", "post", "delete", "patch", "put"]
        # Ensure dispatch is callable on this mock as a bound method
        view.dispatch = lambda req, *a, **kw: dispatch(view, req, *a, **kw)
        return view

    def test_non_htmx_request_calls_non_htmx_dispatch(self):
        """A non-HTMX request is forwarded to ``_non_htmx_dispatch``."""
        from htmx_views.views import dispatch

        view = self._make_view()
        request = _make_request("GET", htmx=False)
        dispatch(view, request)
        view._non_htmx_dispatch.assert_called_once_with(request)

    def test_htmx_request_calls_htmx_verb_method(self):
        """An HTMX GET request calls ``htmx_get`` when the method exists."""
        from htmx_views.views import dispatch

        view = self._make_view()
        request = _make_request("GET", htmx=_MockHtmx())
        dispatch(view, request)
        view.htmx_get.assert_called_once_with(request)

    def test_htmx_request_falls_back_to_verb_method_when_no_htmx_handler(self):
        """Falls back to ``get`` when ``htmx_get`` is not defined on the view."""
        from htmx_views.views import dispatch

        class MinimalView:
            http_method_names = ["get", "post"]

            def _non_htmx_dispatch(self, request, *a, **kw):
                return HttpResponse("non_htmx")

            def get(self, request, *a, **kw):
                return HttpResponse("get")

            def http_method_not_allowed(self, request, *a, **kw):
                return HttpResponse("not_allowed", status=405)

        view = MinimalView()
        request = _make_request("GET", htmx=_MockHtmx())
        result = dispatch(view, request)
        assert result.content == b"get"

    def test_htmx_method_not_in_allowed_names_calls_not_allowed(self):
        """An HTMX request with a method outside ``http_method_names`` calls ``http_method_not_allowed``."""
        from htmx_views.views import dispatch

        view = self._make_view(http_method_names=["get", "post"])
        request = _make_request("DELETE", htmx=_MockHtmx())
        dispatch(view, request)
        view.http_method_not_allowed.assert_called_once_with(request)

    def test_view_class_is_monkey_patched(self):
        """``View._non_htmx_dispatch`` exists, confirming the monkey-patch was applied."""
        from django.views import View

        assert hasattr(View, "_non_htmx_dispatch"), (
            "View should have been monkey-patched with _non_htmx_dispatch on module import"
        )
        assert hasattr(View, "dispatch")


# ---------------------------------------------------------------------------
# Tests for HTMXProcessMixin
# ---------------------------------------------------------------------------

class TestHTMXElementsIteration:
    """Tests for ``HTMXProcessMixin.htmx_elements``."""

    def _make_mixin(self, htmx):
        from htmx_views.views import HTMXProcessMixin

        class Concrete(HTMXProcessMixin, _StubBase):
            pass

        obj = Concrete.__new__(Concrete)
        obj._htmx_get_context_data = False
        obj._htmx_get_context_object_name = False
        obj._htmx_get_template_names = False
        obj.request = _make_request(htmx=htmx)
        return obj

    def test_yields_trigger_name_trigger_target_in_order(self):
        """htmx_elements yields elements from trigger_name, trigger, target in that order."""
        obj = self._make_mixin(_MockHtmx(trigger_name="btn-save", trigger="form1", target="result-div"))
        elements = list(obj.htmx_elements())
        assert elements == ["btnsave", "form1", "resultdiv"]

    def test_skips_none_attributes(self):
        """htmx_elements skips attributes that are None."""
        obj = self._make_mixin(_MockHtmx(trigger_name="save", trigger=None, target=None))
        elements = list(obj.htmx_elements())
        assert elements == ["save"]

    def test_yields_nothing_when_all_attributes_are_none(self):
        """htmx_elements yields nothing when all HTMX attributes are None."""
        obj = self._make_mixin(_MockHtmx())
        elements = list(obj.htmx_elements())
        assert elements == []

    def test_sanitises_special_characters(self):
        """htmx_elements removes non-alphanumeric, non-underscore characters and lowercases."""
        obj = self._make_mixin(_MockHtmx(trigger_name="My Button! #1"))
        elements = list(obj.htmx_elements())
        assert elements == ["mybutton1"]

    def test_lowercases_element_names(self):
        """htmx_elements lowercases element names."""
        obj = self._make_mixin(_MockHtmx(trigger_name="SaveButton"))
        elements = list(obj.htmx_elements())
        assert elements == ["savebutton"]

    def test_preserves_underscores(self):
        """htmx_elements preserves underscores in element names."""
        obj = self._make_mixin(_MockHtmx(trigger_name="my_trigger_name"))
        elements = list(obj.htmx_elements())
        assert elements == ["my_trigger_name"]


class TestHTMXProcessMixinTemplateNames:
    """Tests for ``HTMXProcessMixin.get_template_names``."""

    def _make_view(self, htmx=None, extra_attrs=None):
        from htmx_views.views import HTMXProcessMixin

        class Concrete(HTMXProcessMixin, _StubBase):
            pass

        view = Concrete.__new__(Concrete)
        view._htmx_get_context_data = False
        view._htmx_get_context_object_name = False
        view._htmx_get_template_names = False
        view.request = _make_request(htmx=htmx)
        if extra_attrs:
            for k, v in extra_attrs.items():
                setattr(view, k, v)
        return view

    def test_non_htmx_request_returns_base_template(self):
        """get_template_names falls back to super() for non-HTMX requests."""
        view = self._make_view(htmx=None)
        assert view.get_template_names() == ["stub.html"]

    def test_already_in_htmx_context_falls_back_to_super(self):
        """get_template_names falls back to super() when _htmx_get_template_names is True."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="save"))
        view._htmx_get_template_names = True
        assert view.get_template_names() == ["stub.html"]

    def test_htmx_uses_template_name_attr_for_matching_element(self):
        """get_template_names returns ``template_name_<elem>`` when present."""
        view = self._make_view(
            htmx=_MockHtmx(trigger_name="save"),
            extra_attrs={"template_name_save": "htmx/save.html"},
        )
        assert view.get_template_names() == "htmx/save.html"

    def test_htmx_uses_get_template_names_handler_for_matching_element(self):
        """get_template_names calls ``get_template_names_<elem>`` when present."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="refresh"))
        view.get_template_names_refresh = lambda: ["htmx/refresh.html"]
        assert view.get_template_names() == ["htmx/refresh.html"]

    def test_htmx_no_match_falls_back_to_super(self):
        """get_template_names falls back to super() when no element-specific handler matches."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="unknown_trigger"))
        assert view.get_template_names() == ["stub.html"]


class TestHTMXProcessMixinContextData:
    """Tests for ``HTMXProcessMixin.get_context_data``."""

    def _make_view(self, htmx=None, extra_attrs=None):
        from htmx_views.views import HTMXProcessMixin

        class Concrete(HTMXProcessMixin, _StubBase):
            pass

        view = Concrete.__new__(Concrete)
        view._htmx_get_context_data = False
        view._htmx_get_context_object_name = False
        view._htmx_get_template_names = False
        view.request = _make_request(htmx=htmx)
        if extra_attrs:
            for k, v in extra_attrs.items():
                setattr(view, k, v)
        return view

    def test_non_htmx_returns_base_context(self):
        """get_context_data delegates to super() for non-HTMX requests."""
        view = self._make_view(htmx=None)
        ctx = view.get_context_data()
        assert ctx == {"base": True}

    def test_htmx_calls_element_specific_context_handler(self):
        """get_context_data calls ``get_context_data_<elem>`` when present."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="detail"))
        view.get_context_data_detail = lambda **kw: {"htmx_detail": True}
        ctx = view.get_context_data()
        assert ctx == {"htmx_detail": True}

    def test_htmx_no_handler_falls_back_to_super(self):
        """get_context_data falls back to super() when no element-specific handler exists."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="unknown"))
        ctx = view.get_context_data()
        assert ctx == {"base": True}


class TestHTMXProcessMixinVerbDelegation:
    """Tests for ``HTMXProcessMixin.htmx_<verb>`` delegation methods."""

    def _make_view(self, htmx=None, extra_attrs=None):
        from htmx_views.views import HTMXProcessMixin

        class Concrete(HTMXProcessMixin, _StubBase):
            def get(self, request, *a, **kw):
                return HttpResponse("get")

            def post(self, request, *a, **kw):
                return HttpResponse("post")

            def delete(self, request, *a, **kw):
                return HttpResponse("delete")

            def patch(self, request, *a, **kw):
                return HttpResponse("patch")

            def put(self, request, *a, **kw):
                return HttpResponse("put")

        view = Concrete.__new__(Concrete)
        view._htmx_get_context_data = False
        view._htmx_get_context_object_name = False
        view._htmx_get_template_names = False
        view.request = _make_request(htmx=htmx)
        if extra_attrs:
            for k, v in extra_attrs.items():
                setattr(view, k, v)
        return view

    def test_htmx_get_calls_element_specific_handler(self):
        """htmx_get dispatches to ``htmx_get_<elem>`` when present."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="mywidget"))
        sentinel_response = HttpResponse("htmx_get_mywidget")
        view.htmx_get_mywidget = lambda req, *a, **kw: sentinel_response
        result = view.htmx_get(view.request)
        assert result is sentinel_response

    def test_htmx_get_falls_back_to_get(self):
        """htmx_get falls back to ``get`` when no element-specific handler is found."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="unknown"))
        result = view.htmx_get(view.request)
        assert result.content == b"get"

    def test_htmx_post_calls_element_specific_handler(self):
        """htmx_post dispatches to ``htmx_post_<elem>`` when present."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="submit"))
        sentinel_response = HttpResponse("htmx_post_submit")
        view.htmx_post_submit = lambda req, *a, **kw: sentinel_response
        result = view.htmx_post(view.request)
        assert result is sentinel_response

    def test_htmx_post_falls_back_to_post(self):
        """htmx_post falls back to ``post`` when no element-specific handler is found."""
        view = self._make_view(htmx=_MockHtmx())
        result = view.htmx_post(view.request)
        assert result.content == b"post"

    def test_htmx_delete_calls_element_specific_handler(self):
        """htmx_delete dispatches to ``htmx_delete_<elem>`` when present."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="remove"))
        sentinel_response = HttpResponse("htmx_delete_remove")
        view.htmx_delete_remove = lambda req, *a, **kw: sentinel_response
        result = view.htmx_delete(view.request)
        assert result is sentinel_response

    def test_htmx_delete_falls_back_to_delete(self):
        """htmx_delete falls back to ``delete`` when no element-specific handler is found."""
        view = self._make_view(htmx=_MockHtmx())
        result = view.htmx_delete(view.request)
        assert result.content == b"delete"

    def test_htmx_patch_calls_element_specific_handler(self):
        """htmx_patch dispatches to ``htmx_patch_<elem>`` when present."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="update"))
        sentinel_response = HttpResponse("htmx_patch_update")
        view.htmx_patch_update = lambda req, *a, **kw: sentinel_response
        result = view.htmx_patch(view.request)
        assert result is sentinel_response

    def test_htmx_patch_falls_back_to_patch(self):
        """htmx_patch falls back to ``patch`` when no element-specific handler is found."""
        view = self._make_view(htmx=_MockHtmx())
        result = view.htmx_patch(view.request)
        assert result.content == b"patch"

    def test_htmx_put_calls_element_specific_handler(self):
        """htmx_put dispatches to ``htmx_put_<elem>`` when present."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="replace"))
        sentinel_response = HttpResponse("htmx_put_replace")
        view.htmx_put_replace = lambda req, *a, **kw: sentinel_response
        result = view.htmx_put(view.request)
        assert result is sentinel_response

    def test_htmx_put_falls_back_to_put(self):
        """htmx_put falls back to ``put`` when no element-specific handler is found."""
        view = self._make_view(htmx=_MockHtmx())
        result = view.htmx_put(view.request)
        assert result.content == b"put"


# ---------------------------------------------------------------------------
# Tests for HTMXFormMixin
# ---------------------------------------------------------------------------

class TestHTMXFormMixinFormValid:
    """Tests for ``HTMXFormMixin.form_valid``."""

    def _make_view(self, htmx=None, extra_attrs=None):
        from htmx_views.views import HTMXFormMixin

        class Concrete(HTMXFormMixin, _StubBase):
            pass

        view = Concrete.__new__(Concrete)
        view._htmx_get_context_data = False
        view._htmx_get_context_object_name = False
        view._htmx_get_template_names = False
        view._htmx_form_valid = False
        view._htmx_form_invalid = False
        view.request = _make_request(htmx=htmx)
        if extra_attrs:
            for k, v in extra_attrs.items():
                setattr(view, k, v)
        return view

    def test_non_htmx_calls_super_form_valid(self):
        """form_valid delegates to super() for non-HTMX requests."""
        view = self._make_view(htmx=None)
        form = MagicMock()
        result = view.form_valid(form)
        assert result.content == b"super_form_valid"

    def test_already_in_htmx_form_valid_context_calls_super(self):
        """form_valid delegates to super() when ``_htmx_form_valid`` is True."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="save"))
        view._htmx_form_valid = True
        form = MagicMock()
        result = view.form_valid(form)
        assert result.content == b"super_form_valid"

    def test_htmx_calls_element_specific_form_valid_handler(self):
        """form_valid calls ``htmx_form_valid_<elem>`` when present."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="save"))
        expected = HttpResponse("htmx_form_valid_save")
        view.htmx_form_valid_save = lambda form: expected
        form = MagicMock()
        result = view.form_valid(form)
        assert result is expected

    def test_htmx_calls_generic_htmx_form_valid_handler(self):
        """form_valid calls ``htmx_form_valid`` (without element suffix) when present."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="unknown_element"))
        expected = HttpResponse("htmx_form_valid_generic")
        view.htmx_form_valid = lambda form: expected
        form = MagicMock()
        result = view.form_valid(form)
        assert result is expected

    def test_htmx_falls_back_to_super_when_no_handler(self):
        """form_valid falls back to super() when no HTMX handler is found."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="unknown_element"))
        form = MagicMock()
        result = view.form_valid(form)
        assert result.content == b"super_form_valid"


class TestHTMXFormMixinFormInvalid:
    """Tests for ``HTMXFormMixin.form_invalid``."""

    def _make_view(self, htmx=None, extra_attrs=None):
        from htmx_views.views import HTMXFormMixin

        class Concrete(HTMXFormMixin, _StubBase):
            pass

        view = Concrete.__new__(Concrete)
        view._htmx_get_context_data = False
        view._htmx_get_context_object_name = False
        view._htmx_get_template_names = False
        view._htmx_form_valid = False
        view._htmx_form_invalid = False
        view.request = _make_request(htmx=htmx)
        if extra_attrs:
            for k, v in extra_attrs.items():
                setattr(view, k, v)
        return view

    def test_non_htmx_calls_super_form_invalid(self):
        """form_invalid delegates to super() for non-HTMX requests."""
        view = self._make_view(htmx=None)
        form = MagicMock()
        result = view.form_invalid(form)
        assert result.content == b"super_form_invalid"

    def test_already_in_htmx_form_invalid_context_calls_super(self):
        """form_invalid delegates to super() when ``_htmx_form_invalid`` is True."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="save"))
        view._htmx_form_invalid = True
        form = MagicMock()
        result = view.form_invalid(form)
        assert result.content == b"super_form_invalid"

    def test_htmx_calls_element_specific_form_invalid_handler(self):
        """form_invalid calls ``htmx_form_invalid_<elem>`` when present."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="save"))
        expected = HttpResponse("htmx_form_invalid_save")
        view.htmx_form_invalid_save = lambda form: expected
        form = MagicMock()
        result = view.form_invalid(form)
        assert result is expected

    def test_htmx_calls_generic_htmx_form_invalid_handler(self):
        """form_invalid calls ``htmx_form_invalid`` (without element suffix) when present."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="unknown_element"))
        expected = HttpResponse("htmx_form_invalid_generic")
        view.htmx_form_invalid = lambda form: expected
        form = MagicMock()
        result = view.form_invalid(form)
        assert result is expected

    def test_htmx_falls_back_to_super_when_no_handler(self):
        """form_invalid falls back to super() when no HTMX handler is found."""
        view = self._make_view(htmx=_MockHtmx(trigger_name="unknown_element"))
        form = MagicMock()
        result = view.form_invalid(form)
        assert result.content == b"super_form_invalid"
