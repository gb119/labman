# -*- coding: utf-8 -*-
"""View support classes and functions for htmx-views."""

# Python imports
import re

# Django imports
from django.views import View


def dispatch(self, request, *args, **kwargs):
    """Dispatch method that becomes htmx aware.

    If the =`htmx` request attribute is set (by django-htmx) and the method name is in either
    `self.http_method_names` or `self.htmx_method_names` then try to locate the method
    `htmx_<http_verb>` method and call that or else fall back to the regular `<http_verb>` method.

    If an approrpiate method can't be located, call `self.http_method_bot_allowed` for error handline.

    If the `htmx` request attrobute is not set or is False, then fall back to the original dispatch.
    """
    if not getattr(request, "htmx", False):  # Not an HTMX aware request
        return self._non_htmx_dispatch(request, *args, **kwargs)

    # Allow different  allowed methods for htmx
    allowed_names = getattr(self, "htmx_http_method_names", self.http_method_names)

    if request.method.lower() in allowed_names:
        handler = getattr(
            self, f"htmx_{request.method.lower()}", getattr(self, request.method.lower(), self.http_method_not_allowed)
        )
    else:
        handler = self.http_method_not_allowed
    return handler(request, *args, **kwargs)


class HTMXProcessMixin:
    """Provide versions of the htmx_`<http_verb>` methods that will delegate to trigger specific methods.

    Each http verb DELETE,GET,PATCH,POST,PUT's htmx_<verb> method will look at the request.htmx attriobute
    to see if htmx_<verb>_<trigger_name>, htmx_<verb>_<trigger>, htmx_<verb>_<target> is a method and then pass
    on to the first matching method. If no match is foumd, the `http_method_not_allowed` method is used instead.
    """

    def htmx_elements(self):
        """Iterate over possible htmx element sources."""
        for attr in ["trigger_name", "trigger", "target"]:
            if elem := getattr(self.request.htmx, attr, None):
                elem = re.sub(r"[^A-Za-z0-9_]", "", elem).lower()
                yield elem

    def get_context_data(self, **kwargs):
        """Get context data being aware of htmx views."""
        if not getattr(self.request, "htmx", False):  # Default behaviour
            return super().get_context_data(**kwargs)

        # Look for a request specifc to the element involved.
        for elem in self.htmx_elements():
            handler = getattr(self, f"get_context_data_{elem}", False)
            if handler:
                return handler(**kwargs)
        return super().get_context_data(**kwargs)

    def get_template_names(self):
        """Look for htmx specific templates."""
        if not getattr(self.request, "htmx", False):  # Default behaviour
            return super().get_template_names()

        # Look for a request specifc to the element involved.
        for elem in self.htmx_elements():
            handler = getattr(self, f"get_template_names_{elem}", False)
            if handler:
                return handler()
            sub_name = getattr(self, f"template_name_{elem}", False)
            if sub_name:
                return sub_name
        return super().get_template_name()

    def htmx_delete(self, request, *args, **kwargs):
        """Delegate HTMX DELETE requests.

        Looks for the element that is related to the request by inspecting the `request.htmx` `trigger_name`, trigger
        and target attributes in turn. If no matching `htmx_delete_<name>` methods are found, return the
        `method_not_allowed` result instrad.
        """
        for elem in self.htmx_elements():
            handler = getattr(self, f"htmx_delete_{elem}")
            if handler:
                break
        else:
            handler = getattr(self, "delete", self.http_method_not_allowed)
        return handler(request, *args, **kwargs)

    def htmx_get(self, request, *args, **kwargs):
        """Delegate HTMX GET requests.

        Looks for the element that is related to the request by inspecting the `request.htmx` `trigger_name`, trigger
        and target attributes in turn. If no matching `htmx_get_<name>` methods are found, return the
        `method_not_allowed` result instrad.
        """
        for elem in self.htmx_elements():
            handler = getattr(self, f"htmx_get_{elem}", False)
            if handler:
                break
        else:
            handler = getattr(self, "get", self.http_method_not_allowed)
        return handler(request, *args, **kwargs)

    def htmx_patch(self, request, *args, **kwargs):
        """Delegate HTMX PATCH requests.

        Looks for the element that is related to the request by inspecting the `request.htmx` `trigger_name`, trigger
        and target attributes in turn. If no matching `htmx_patch_<name>` methods are found, return the
        `method_not_allowed` result instrad.
        """
        for elem in self.htmx_elements():
            handler = getattr(self, f"htmx_patch_{elem}")
            if handler:
                break
        else:
            handler = getattr(self, "patch", self.http_method_not_allowed)
        return handler(request, *args, **kwargs)

    def htmx_post(self, request, *args, **kwargs):
        """Delegate HTMX POST requests.

        Looks for the element that is related to the request by inspecting the `request.htmx` `trigger_name`, trigger
        and target attributes in turn. If no matching `htmx_post_<name>` methods are found, return the
        `method_not_allowed` result instrad.
        """
        for elem in self.htmx_elements():
            handler = getattr(self, f"htmx_post_{elem}")
            if handler:
                break
        else:
            handler = getattr(self, "post", self.http_method_not_allowed)
        return handler(request, *args, **kwargs)

    def htmx_put(self, request, *args, **kwargs):
        """Delegate HTMX PUT requests.

        Looks for the element that is related to the request by inspecting the `request.htmx` `trigger_name`, trigger
        and target attributes in turn. If no matching `htmx_put_<name>` methods are found, return the
        `method_not_allowed` result instrad.
        """
        for elem in self.htmx_elements():
            handler = getattr(self, f"htmx_put_{elem}")
            if handler:
                break
        else:
            handler = getattr(self, "put", self.http_method_not_allowed)
        return handler(request, *args, **kwargs)


if not hasattr(View, "_bon_htmx_dispatch"):  # View needs monkey patching
    setattr(View, "_non_htmx_dispatch", View.dispatch)
    setattr(View, "dispatch", dispatch)
    print("View.dispatch patched")