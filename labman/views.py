# -*- coding: utf-8 -*-
"""Main site views for error handling and file serving.

This module defines custom error views for HTTP error codes (400, 403, 404, 500)
and a file serving view for streaming file downloads.
"""
# Python imports
import logging
import os
import sys

# Django imports
from django.conf import settings
from django.http import Http404, StreamingHttpResponse
from django.shortcuts import redirect
from django.utils.decorators import classonlymethod
from django.views import View
from django.views.debug import technical_500_response
from django.views.generic import TemplateView

# external imports
from constance import config

logger = logging.getLogger(__file__)


class ErrorView(TemplateView):
    """Base class for custom error views with automatic error code handling.

    This view extracts the HTTP error code from the class name (e.g., E404View -> 404)
    and returns the appropriate status code in the response. It also provides common
    context data for error templates.

    Notes:
        The error code is derived from the class name by extracting characters 1-3
        (e.g., E404View extracts '404').
    """

    def __init__(self, *args, **kargs):
        """Initialise the error view and log the creation.

        Args:
            *args: Variable positional arguments.

        Keyword Parameters:
            **kargs: Variable keyword arguments.
        """
        logger.error(f"Entered Error view as {self.__class__.__name__} with {args} and {kargs}")
        super().__init__(*args, **kargs)

    @classmethod
    def get_error_code(cls):
        """Extract the HTTP error code from the class name.

        Returns:
            (int): The HTTP error code (e.g., 404, 500).

        Notes:
            Extracts characters 1-3 from the class name and converts to integer.
            For example, E404View becomes 404.
        """
        name = cls.__name__
        return int(name[1:4])

    @property
    def error_code(self):
        """Get the error code as a property.

        Returns:
            (int): The HTTP error code.
        """
        return self.get_error_code()

    def get_context_date(self, **kwargs):
        """Get common context data for the error view.

        Keyword Parameters:
            **kwargs: Additional context data.

        Returns:
            (dict): Context dictionary including request, user, and config.
        """
        context = super().get_context_date(**kwargs)
        context["request"] = self.request
        context["user"] = self.request.user
        context["config"] = config
        return context

    def get_template_names(self):
        """Return the template name based on the error code.

        Returns:
            (str): Template path in the format "errors/{code}View.html".
        """
        return f"errors/{self.error_code}View.html"

    def render_to_response(self, context, **response_kwargs):
        """Render the error response with the appropriate status code.

        Args:
            context (dict):
                Template context dictionary.

        Keyword Parameters:
            **response_kwargs: Additional arguments for the response.

        Returns:
            (HttpResponse): Response with the error status code set.
        """
        response = super().render_to_response(context, **response_kwargs)
        response.status_code = self.get_error_code()
        return response


class E400View(ErrorView):
    """Custom view for HTTP 400 Bad Request errors.

    Renders a custom error page using the standard template with error code 400.
    """


class E404View(ErrorView):
    """Custom view for HTTP 404 Not Found errors.

    Renders a custom error page using the standard template with error code 404.
    """


class E403View(ErrorView):
    """Custom view for HTTP 403 Forbidden errors.

    Renders a custom error page using the standard template with error code 403.
    """


class E500View(ErrorView):
    """Custom view for HTTP 500 Internal Server Error.

    Renders a custom error page using the standard template with error code 500.
    For superusers, displays the technical debug page with full traceback.
    """

    @classonlymethod
    def as_view(cls, **initkwargs):
        """Create a view callable from the class.

        Keyword Parameters:
            **initkwargs: Initial keyword arguments for the view.

        Returns:
            (callable): View function that handles requests.

        Raises:
            TypeError: If invalid keyword arguments are provided.
        """
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError(
                    "The method name %s is not accepted as a keyword argument " "to %s()." % (key, cls.__name__)
                )
            if not hasattr(cls, key):
                raise TypeError(
                    f"{cls.__name__}() received an invalid keyword {key}. as_view only accepts arguments that are"
                    " already attributes of the class."
                )

        def view(request, *args, **kwargs):
            """Handle the actual view request.

            Args:
                request (HttpRequest):
                    The HTTP request object.
                *args: Variable positional arguments.

            Keyword Parameters:
                **kwargs: Variable keyword arguments.

            Returns:
                (HttpResponse): The HTTP response.

            Raises:
                AttributeError: If the view instance has no request attribute.
            """
            self = cls(**initkwargs)
            self.setup(request, *args, **kwargs)
            if not hasattr(self, "request"):
                raise AttributeError(
                    "%s instance has no 'request' attribute. Did you override "
                    "setup() and forget to call super()?" % cls.__name__
                )
            return self.dispatch(request, *args, **kwargs)

        view.view_class = cls
        view.view_initkwargs = initkwargs
        # take name and docstring from class
        view.__doc__ = cls.__doc__
        view.__module__ = cls.__module__
        view.__annotations__ = cls.dispatch.__annotations__
        # Copy possible attributes set by decorators, e.g. @csrf_exempt, from
        # the dispatch method.
        view.__dict__.update(cls.dispatch.__dict__)
        return view

    def get(self, request, *args, **kwargs):
        """Respond to GET requests.

        Args:
            request (HttpRequest):
                The HTTP request object.
            *args: Variable positional arguments.

        Keyword Parameters:
            **kwargs: Variable keyword arguments.

        Returns:
            (HttpResponse): Technical debug page for superusers, or standard
                           error page for other users.
        """
        if request.user.is_superuser:
            return technical_500_response(request, *sys.exc_info())
        else:
            return super().get(request, *args, **kwargs)


class FileServeView(View):
    """View for streaming file downloads from the media directory.

    Provides a streaming response for serving files from the MEDIA_ROOT directory.
    Files are sent in chunks to efficiently handle large files without loading
    them entirely into memory.

    Notes:
        Raises Http404 if the requested file does not exist.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET requests to serve a file.

        Args:
            request (HttpRequest):
                The HTTP request object.
            *args: Variable positional arguments.

        Keyword Parameters:
            path (str):
                Relative path to the file within MEDIA_ROOT.
            **kwargs: Additional keyword arguments.

        Returns:
            (StreamingHttpResponse): Streaming response with the file content.

        Raises:
            Http404: If the file does not exist.

        Notes:
            Files are read in 8192-byte chunks for efficient streaming.
        """
        # Define the file path
        if file_path := kwargs.get("path"):
            file_path = os.path.join(settings.MEDIA_ROOT, file_path)
            if not os.path.exists(file_path):
                raise Http404(f"File {kwargs.get('path')} not found")

            # Define a generator to read the file in chunks
            def file_iterator(file_name, chunk_size=8192):
                """Generate file chunks for streaming.

                Args:
                    file_name (str):
                        Path to the file to read.
                    chunk_size (int):
                        Size of each chunk in bytes (default: 8192).

                Yields:
                    (bytes): Chunks of the file content.
                """
                with open(file_name, "rb") as f:
                    while chunk := f.read(chunk_size):
                        yield chunk

            # Create a streaming response
            response = StreamingHttpResponse(file_iterator(file_path))
            response["Content-Disposition"] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response


class RedirectLoginView(View):
    """SAimple view to redirect requests to /login/?next=<url> if logged in."""

    def get(self, request, *args, **kwargs):
        """Handle GET requests to serve a file.

        Args:
            request (HttpRequest):
                The HTTP request object.
            *args: Variable positional arguments.

        Keyword Parameters:
            path (str):
                Relative path to the file within MEDIA_ROOT.
            **kwargs: Additional keyword arguments.

        Returns:
            Redirection to the requestd URL.
        """
        if next_url := request.GET.get("next", None):
            return redirect(next_url)
        return super().get(request, *args, **kwargs)
