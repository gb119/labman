# -*- coding: utf-8 -*-
"""View support classes and functions for htmx-views."""

# Python imports
import logging
import re
from contextlib import contextmanager

# Django imports
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.views import View
from django.views.generic import TemplateView

# external imports
from ajax_select import registry

logger = logging.getLogger(__name__)


@contextmanager
def temp_attr(obj, attr, value):
    """Temporarily set the value of an attribute and restore it afterwards.

    Args:
        obj (object):
            Value supplied for ``obj``.
        attr (object):
            Value supplied for ``attr``.
        value (object):
            Value supplied for ``value``.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(temp_attr)
            True

    """
    # Check if the attribute originally exists on the object
    has_attr = hasattr(obj, attr)
    original_value = getattr(obj, attr, None)

    # Set the attribute to the new value
    setattr(obj, attr, value)

    try:
        # Yield control back to the caller
        yield
    finally:
        if has_attr:
            # Restore the original value if the attribute existed
            setattr(obj, attr, original_value)
        else:
            # Delete the attribute if it didn't exist originally
            delattr(obj, attr)


def dispatch(self, request, *args, **kwargs):
    """Dispatch method that becomes htmx aware.

            If the =`htmx` request attribute is set (by django-htmx) and the method name is in either
            `self.http_method_names` or `self.htmx_method_names` then try to locate the method
            `htmx_<http_verb>` method and call that or else fall back to the regular `<http_verb>` method.

            If an approrpiate method can't be located, call `self.http_method_bot_allowed` for error handline.

            If the `htmx` request attrobute is not set or is False, then fall back to the original dispatch.


    Args:
        request (object):
            Value supplied for ``request``.
        *args (object):
            Value supplied for ``args``.
    Keyword Parameters:
        **kwargs (object):
            Value supplied for ``kwargs``.

    Returns:
        (object):
            The result of the operation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(dispatch)
            True

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
    if not callable(handler):
        handler = self.http_method_not_allowed
    return handler(request, *args, **kwargs)


class HTMXProcessMixin:
    """Provide versions of the htmx_`<http_verb>` methods that will delegate to trigger specific methods.

            Each http verb DELETE,GET,PATCH,POST,PUT's htmx_<verb> method will look at the request.htmx attriobute
            to see if htmx_<verb>_<trigger_name>, htmx_<verb>_<trigger>, htmx_<verb>_<target> is a method and then pass
            on to the first matching method. If no match is foumd, the `http_method_not_allowed` method is used instead.


    Examples:
        Inspect the public interface in an interactive session::

            >>> HTMXProcessMixin.__name__
            'HTMXProcessMixin'

    """

    def __init__(self, *args, **kwargs):
        """Set up the HTMX call attributes for later use."""
        super().__init__(*args, **kwargs)
        self._htmx_get_context_data = False
        self._htmx_get_context_object_name = False
        self._htmx_get_template_names = False

    def htmx_elements(self):
        """Iterate over possible htmx element sources.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(HTMXProcessMixin.htmx_elements)
                True

        """
        for attr in ["trigger_name", "trigger", "target"]:
            if elem := getattr(self.request.htmx, attr, None):
                elem = re.sub(r"[^A-Za-z0-9_]", "", elem).lower()
                if settings.DEBUG:
                    logger.debug(elem)
                yield elem

    def get_context_data(self, **kwargs):
        """Get context data being aware of htmx views.

        Keyword Parameters:
            **kwargs (object):
                Value supplied for ``kwargs``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(HTMXProcessMixin.get_context_data)
                True

        """
        if not getattr(self.request, "htmx", False) or self._htmx_get_context_data:  # Default behaviour
            return super().get_context_data(**kwargs)

        # Look for a request specific to the element involved.
        handler = self.get_context_data_function(**kwargs)
        if handler is not None:
            with temp_attr(self, "_htmx_get_context_data", True):
                return handler(**kwargs)
        return super().get_context_data(**kwargs)

    def get_context_data_function(self, **kwargs):
        """Return the first callable element-specific context handler.

        Keyword Parameters:
            **kwargs (object):
                Context keyword arguments. They are accepted so subclasses can use them when extending handler
                selection.

        Returns:
            (callable | None):
                The selected handler, or ``None`` when no handler matches.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(HTMXProcessMixin.get_context_data_function)
                True

        """
        del kwargs
        for elem in self.htmx_elements():
            handler = getattr(self, f"get_context_data_{elem}", None)
            if callable(handler):
                return handler
        return None

    def get_context_object_name(self, object_list):
        """Get context object name being aware of htmx elements.

                        If the get_context_name_<element> method needs to call usper, it shopuld set a keyword
                        argument, _default to be True to avoid a recursive loop.


        Args:
            object_list (object):
                Value supplied for ``object_list``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(HTMXProcessMixin.get_context_object_name)
                True

        """
        if not getattr(self.request, "htmx", False) or self._htmx_get_context_object_name:  # Default behaviour
            return super().get_context_object_name(object_list)

        # Look for a request specifc to the element involved.
        for elem in self.htmx_elements():
            for handler_name in (f"get_context_object_name_{elem}", f"get_context_object_name{elem}"):
                if callable(handler := getattr(self, handler_name, None)):
                    with temp_attr(self, "_htmx_get_context_object_name", True):
                        return handler(object_list)
            if sub_name := getattr(self, f"context_object_{elem}", False):
                return sub_name

        logger.debug("Super")

        return super().get_context_object_name(object_list)

    def get_template_names(self):
        """Look for htmx specific templates.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(HTMXProcessMixin.get_template_names)
                True

        """
        if not getattr(self.request, "htmx", False) or self._htmx_get_template_names:  # Default behaviour
            return super().get_template_names()

        # Look for a request specifc to the element involved.
        for elem in self.htmx_elements():
            handler = getattr(self, f"get_template_names_{elem}", None)
            if callable(handler):
                if settings.DEBUG:
                    logger.debug(f"Template_handl;er: {handler.__name__}")
                with temp_attr(self, "_htmx_get_template_names", True):
                    return handler()
            sub_name = getattr(self, f"template_name_{elem}", False)
            if sub_name:
                if settings.DEBUG:
                    logger.debug(f"Template_name: {sub_name}")
                return sub_name
        return super().get_template_names()

    def htmx_delete(self, request, *args, **kwargs):
        """Delegate HTMX DELETE requests.

                        Looks for the element that is related to the request by inspecting the `request.htmx` `trigger_name`, trigger
                        and target attributes in turn. If no matching `htmx_delete_<name>` methods are found, return the
                        `method_not_allowed` result instrad.


        Args:
            request (object):
                Value supplied for ``request``.
            *args (object):
                Value supplied for ``args``.
        Keyword Parameters:
            **kwargs (object):
                Value supplied for ``kwargs``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(HTMXProcessMixin.htmx_delete)
                True

        """
        for elem in self.htmx_elements():
            handler = getattr(self, f"htmx_delete_{elem}", None)
            if callable(handler):
                break
        else:
            handler = getattr(self, "delete", self.http_method_not_allowed)
        if not callable(handler):
            handler = self.http_method_not_allowed
        if settings.DEBUG:
            logger.debug(f"HTMX Method handler: {handler.__name__}")
        return handler(request, *args, **kwargs)

    def htmx_get(self, request, *args, **kwargs):
        """Delegate HTMX GET requests.

                        Looks for the element that is related to the request by inspecting the `request.htmx` `trigger_name`, trigger
                        and target attributes in turn. If no matching `htmx_get_<name>` methods are found, return the
                        `method_not_allowed` result instrad.


        Args:
            request (object):
                Value supplied for ``request``.
            *args (object):
                Value supplied for ``args``.
        Keyword Parameters:
            **kwargs (object):
                Value supplied for ``kwargs``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(HTMXProcessMixin.htmx_get)
                True

        """
        for elem in self.htmx_elements():
            handler = getattr(self, f"htmx_get_{elem}", None)
            if callable(handler):
                break
        else:
            handler = getattr(self, "get", self.http_method_not_allowed)
        if not callable(handler):
            handler = self.http_method_not_allowed
        if settings.DEBUG:
            logger.debug(f"HTMX Method handler: {handler.__name__}")
        return handler(request, *args, **kwargs)

    def htmx_patch(self, request, *args, **kwargs):
        """Delegate HTMX PATCH requests.

                        Looks for the element that is related to the request by inspecting the `request.htmx` `trigger_name`, trigger
                        and target attributes in turn. If no matching `htmx_patch_<name>` methods are found, return the
                        `method_not_allowed` result instrad.


        Args:
            request (object):
                Value supplied for ``request``.
            *args (object):
                Value supplied for ``args``.
        Keyword Parameters:
            **kwargs (object):
                Value supplied for ``kwargs``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(HTMXProcessMixin.htmx_patch)
                True

        """
        for elem in self.htmx_elements():
            handler = getattr(self, f"htmx_patch_{elem}", None)
            if callable(handler):
                break
        else:
            handler = getattr(self, "patch", self.http_method_not_allowed)
        if not callable(handler):
            handler = self.http_method_not_allowed
        if settings.DEBUG:
            logger.debug(f"HTMX Method handler: {handler.__name__}")
        return handler(request, *args, **kwargs)

    def htmx_post(self, request, *args, **kwargs):
        """Delegate HTMX POST requests.

                        Looks for the element that is related to the request by inspecting the `request.htmx` `trigger_name`, trigger
                        and target attributes in turn. If no matching `htmx_post_<name>` methods are found, return the
                        `method_not_allowed` result instrad.


        Args:
            request (object):
                Value supplied for ``request``.
            *args (object):
                Value supplied for ``args``.
        Keyword Parameters:
            **kwargs (object):
                Value supplied for ``kwargs``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(HTMXProcessMixin.htmx_post)
                True

        """
        for elem in self.htmx_elements():
            handler = getattr(self, f"htmx_post_{elem}", None)
            if callable(handler):
                break
        else:
            handler = getattr(self, "post", self.http_method_not_allowed)
        if not callable(handler):
            handler = self.http_method_not_allowed
        if settings.DEBUG:
            logger.debug(f"HTMX Method handler: {handler.__name__}")
        return handler(request, *args, **kwargs)

    def htmx_put(self, request, *args, **kwargs):
        """Delegate HTMX PUT requests.

                        Looks for the element that is related to the request by inspecting the `request.htmx` `trigger_name`, trigger
                        and target attributes in turn. If no matching `htmx_put_<name>` methods are found, return the
                        `method_not_allowed` result instrad.


        Args:
            request (object):
                Value supplied for ``request``.
            *args (object):
                Value supplied for ``args``.
        Keyword Parameters:
            **kwargs (object):
                Value supplied for ``kwargs``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(HTMXProcessMixin.htmx_put)
                True

        """
        for elem in self.htmx_elements():
            handler = getattr(self, f"htmx_put_{elem}", None)
            if callable(handler):
                break
        else:
            handler = getattr(self, "put", self.http_method_not_allowed)
        if not callable(handler):
            handler = self.http_method_not_allowed
        if settings.DEBUG:
            logger.debug(f"HTMX Method handler: {handler.__name__}")
        return handler(request, *args, **kwargs)


class HTMXFormMixin(HTMXProcessMixin):
    """Provide additional methods to adapt FormView and friends for htmx requests as well.

    Examples:
        Inspect the public interface in an interactive session::

            >>> HTMXFormMixin.__name__
            'HTMXFormMixin'

    """

    def __init__(self, *args, **kwargs):
        """Set up the HTMX call attributes for later use."""
        super().__init__(*args, **kwargs)
        self._htmx_form_valid = False
        self._htmx_form_invalid = False

    def form_valid(self, form):
        """Look for HTMX form valid handlers.

                        If request.htmx is not set, then return the parent class form_valid, otherwise look for an element
                        specific htmx_form_valid_<name> method, or failing that just an htmx_form_valid meothd. Fnally,
                        give up and return the parent form_valid.

        Notes:
            htmx_form_valid* methods must not call super().form_valid - otherwise an infinite recursion happens!


        Args:
            form (object):
                Value supplied for ``form``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(HTMXFormMixin.form_valid)
                True

        """
        if not getattr(self.request, "htmx", False) or self._htmx_form_valid:  # Non HTMX requests
            return super().form_valid(form)
        for elem in self.htmx_elements():
            if settings.DEBUG:
                logger.debug(f"Looking for htmx_form_valid_{elem}")
            handler = getattr(self, f"htmx_form_valid_{elem}", None)
            if callable(handler):
                with temp_attr(self, "_htmx_form_valid", True):
                    return handler(form)
        if callable(handler := getattr(self, "htmx_form_valid", None)):
            with temp_attr(self, "_htmx_form_valid", True):
                return handler(form)
        return super().form_valid(form)

    def form_invalid(self, form):
        """Look for HTMX form valid handlers.

                        If request.htmx is not set, then return the parent class form_invalid, otherwise look for an element
                        specific htmx_form_invalid_<name> method, or failing that just an htmx_form_invalid meothd. Fnally,
                        give up and return the parent form_invalid.

        Notes:
            htmx_inform_valid* methods must not call super().form_valid - otherwise an infinite recursion happens!


        Args:
            form (object):
                Value supplied for ``form``.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(HTMXFormMixin.form_invalid)
                True

        """
        if not getattr(self.request, "htmx", False) or self._htmx_form_invalid:  # Non HTMX requests
            return super().form_invalid(form)

        for elem in self.htmx_elements():
            handler = getattr(self, f"htmx_form_invalid_{elem}", None)
            if settings.DEBUG:
                logger.debug(f"Looking for htmx_form_invalid_{elem}")
            if callable(handler):
                with temp_attr(self, "_htmx_form_invalid", True):
                    return handler(form)
        if callable(handler := getattr(self, "htmx_form_invalid", None)):
            with temp_attr(self, "_htmx_form_invalid", True):
                return handler(form)
        return super().form_invalid(form)


class LinkedSelectEndpointView(TemplateView):
    """Return linked-select options from an authorised ``ajax_select`` lookup.

    Attributes:
        template_name (str):
            Template used to render the option list.

    Examples:
        Inspect the public interface in an interactive session::

            >>> LinkedSelectEndpointView.__name__
            'LinkedSelectEndpointView'

    """

    http_method_names = ["get", "head", "options"]
    template_name = "htmx_views/widgets/options.html"

    def dispatch(self, request, *args, **kwargs):
        """Resolve the lookup and enforce its authorisation policy.

        Args:
            request (object):
                The HTTP request.
            *args (object):
                Positional arguments supplied by Django.

        Keyword Parameters:
            **kwargs (object):
                URL keyword arguments supplied by Django.

        Returns:
            (object):
                The rendered response.

        Raises:
            Http404:
                If the requested lookup channel is not registered.
            PermissionDenied:
                If the lookup's authorisation policy rejects the request.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(LinkedSelectEndpointView.dispatch)
                True

        """
        self.lookup_channel = kwargs.get("lookup_channel")
        try:
            self.lookup = registry.get(self.lookup_channel)
        except ImproperlyConfigured as error:
            raise Http404("Unknown linked-select lookup channel.") from error

        self.lookup.check_auth(request)
        self.parent = request.GET.get("_htmx_parent") or getattr(self.lookup, "parameter_name", None)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add the lookup options to the template context.

        Keyword Parameters:
            **kwargs (object):
                Context keyword arguments supplied by Django.

        Returns:
            (dict):
                Template context containing ``options`` as ``(value, label)`` pairs.

        Raises:
            ImproperlyConfigured:
                If neither the request nor the lookup identifies the parent field.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(LinkedSelectEndpointView.get_context_data)
                True

        """
        if self.parent is None:
            raise ImproperlyConfigured(
                f"Creating an htmx_views widget for {self.lookup_channel} without knowing the trigger."
            )

        query = self.request.GET.get(self.parent)
        try:
            query = int(query)
        except (TypeError, ValueError):
            pass

        context = super().get_context_data(**kwargs)
        context["options"] = []
        if query:
            context["options"] = [
                (item.pk, str(item)) for item in self.lookup.get_query(query, self.request).distinct()
            ]
        return context


def _install_htmx_dispatch(view_class=View):
    """Install the HTMX-aware dispatch function idempotently."""
    if not hasattr(view_class, "_non_htmx_dispatch"):
        setattr(view_class, "_non_htmx_dispatch", view_class.dispatch)
    setattr(view_class, "dispatch", dispatch)


_install_htmx_dispatch()
