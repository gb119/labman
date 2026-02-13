# -*- coding: utf-8 -*-
"""View classes and mixins for the labman_utils application.

This module provides a collection of generic view classes, mixins, and utilities for the labman application.
It includes authentication mixins, multi-form handling, HTMX-based dialog views for managing documents, photos,
and flat pages, as well as custom redirect views based on user permissions. These components support common
patterns such as form validation, object linking, and permission-based view routing.
"""
# Python imports
from importlib import import_module

# Django imports
from django import forms
from django.apps import apps
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.flatpages.models import FlatPage
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseNotModified,
    HttpResponseRedirect,
)
from django.urls import reverse
from django.utils.text import slugify
from django.views.generic import DetailView, ListView, UpdateView, View
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.views.generic.edit import FormMixin, ProcessFormView

# external imports
from htmx_views.views import HTMXFormMixin
from photologue.models import Photo

# app imports
from .forms import (
    DocumentLinksForm,
    FlatPageForm,
    FlatPagesLinksForm,
    PhotoLinksForm,
)
from .models import Document

# from sortedm2m.admin import OrderedAutocomplete


Equipment = apps.get_model(app_label="equipment", model_name="equipment")
Location = apps.get_model(app_label="equipment", model_name="location")
Account = apps.get_model(app_label="accounts", model_name="Account")


class IsAuthenticaedViewMixin(UserPassesTestMixin):
    """Mixin class to enforce logged in users only.

    This mixin restricts view access to authenticated users by checking if the user is logged in.
    If the test fails, users are redirected to the login URL.

    Attributes:
        login_url (str):
            The URL to redirect to when authentication fails, defaults to "/login".
    """

    login_url = "/login"

    def test_func(self):
        """Test whether the user is set and logged in.

        Returns:
            (bool):
                True if the request has a user attribute and the user is authenticated, False otherwise.
        """
        return hasattr(self, "request") and not self.request.user.is_anonymous


class IsSuperuserViewMixin(IsAuthenticaedViewMixin):
    """Mixin class to enforce the user is a super user.

    This mixin extends IsAuthenticaedViewMixin and adds an additional check to ensure the user
    has superuser privileges.
    """

    def test_func(self):
        """Check the user is set and is a superuser.

        Returns:
            (bool):
                True if the user is authenticated and is a superuser, False otherwise.
        """
        return super().test_func() and self.request.user.is_superuser


class IsStaffViewMixin(IsSuperuserViewMixin):
    """Mixin to enforce that the user is a staff user.

    This mixin checks whether the user is authenticated and either a staff member or a superuser.
    """

    def test_func(self):
        """Test whether the user account is defined and is a staff or super user.

        Returns:
            (bool):
                True if the user is authenticated and is either staff or superuser, False otherwise.
        """
        return IsAuthenticaedViewMixin.test_func(self) and (self.request.user.is_staff or super().test_func())


class RedirectView(View):
    """Redirects the view to another class depending on the request user's attributes.

    This view provides a flexible routing mechanism that selects the appropriate view class based on
    user authentication status and permissions. The selection process checks conditions in order:
    superuser, staff, authenticated, and group membership.

    The first condition that matches and returns a non-None view class is used to dispatch the request.

    Attributes:
        superuser_view (View, optional):
            View class to use for superusers.
        staff_view (View, optional):
            View class to use for staff users.
        logged_in_view (View, optional):
            View class to use for authenticated users.
        anonymous_view (View, optional):
            View class to use for anonymous users.
        group_map (dict, optional):
            Dictionary mapping group names to view classes for group-based routing.
        as_view_kwargs (dict, optional):
            Keyword arguments to pass to the selected view's as_view method.

    Notes:
        The selection order is: superuser → staff → logged-in/anonymous → group-based.
        Each get_*_view method can be overridden to customise the selection logic.
    """

    def get_superuser_view(self, request):
        """If the request user is a super user return superuser_view attribute or None.

        Args:
            request (HttpRequest):
                The Django HTTP request object.

        Returns:
            (View or None):
                The superuser_view attribute if the user is a superuser, otherwise None.
        """
        if self.request.user.is_authenticated and self.request.user.is_superuser:
            return getattr(self, "superuser_view", None)
        return None

    def get_staff_view(self, request):
        """If the request user is a staff user return staff_view attribute or None.

        Args:
            request (HttpRequest):
                The Django HTTP request object.

        Returns:
            (View or None):
                The staff_view attribute if the user is a staff member, otherwise None.
        """
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return getattr(self, "staff_view", None)
        return None

    def get_logged_in_view(self, request):
        """If the request user is authenticated return logged_in_view attribute, otherwise anonymous_view.

        Args:
            request (HttpRequest):
                The Django HTTP request object.

        Returns:
            (View or None):
                The logged_in_view attribute if authenticated, otherwise the result of get_anonymous_view.
        """
        if self.request.user.is_authenticated:
            return getattr(self, "logged_in_view", None)
        return self.get_anonymous_view(request)

    def get_anonymous_view(self, request):
        """Return the contents of the anonymous_view.

        Args:
            request (HttpRequest):
                The Django HTTP request object.

        Returns:
            (View or None):
                The anonymous_view attribute or None if not set.
        """
        return getattr(self, "anonymous_view", None)

    def get_group_view(self, request):
        """Get the mapping group_map and try to find a match to a group that the logged in user has.

        Args:
            request (HttpRequest):
                The Django HTTP request object.

        Returns:
            (View or None):
                The view class associated with the first matching group, or None if no match is found.
        """
        if not self.request.user.is_authenticated:  # Not logged in, so no groups -> None
            return None
        groups = self.request.user.groups.all()
        for group, view in getattr(self, "group_map", {}).items():  # -> No group map -> no iteration
            if groups.filter(name=group).count() > 0:  # Group name in map -> return view
                return view
        return None  # Fall out of options

    def dispatch(self, request, *args, **kwargs):
        """Attempt to find another view to redirect to before calling super().

        Args:
            request (HttpRequest):
                The Django HTTP request object.
            *args:
                Variable length argument list passed to the view.
            **kwargs:
                Arbitrary keyword arguments passed to the view.

        Returns:
            (HttpResponse):
                The response from the selected view's dispatch method, or the superclass dispatch
                if no matching view is found.
        """
        self.kwargs.update(kwargs)
        kwargs = self.kwargs
        for method in [self.get_superuser_view, self.get_staff_view, self.get_logged_in_view, self.get_group_view]:
            if view := method(request):
                as_view_kwargs = getattr(self, "as_view_kwargs", {})
                return view.as_view(**as_view_kwargs)(request, *self.args, **self.kwargs)
        return super().dispatch(request, *self.args, **self.kwargs)


class MultiFormMixin(ContextMixin):
    """Mixin class that handles multiple forms within a view.

    This mixin enables a single view to manage multiple forms, each with its own validation,
    initial values, prefixes, and success URLs. Forms can be processed individually or in groups.

    Attributes:
        form_classes (dict):
            Dictionary mapping form names to form classes.
        prefixes (dict):
            Dictionary mapping form names to form prefixes for field name uniqueness.
        success_urls (dict):
            Dictionary mapping form names to their success redirect URLs.
        grouped_forms (dict):
            Dictionary mapping group names to lists of form names for batch processing.
        initial (dict):
            Default initial values for all forms.
        prefix (str or None):
            Default prefix for forms if not specified in prefixes dict.
        success_url (str or None):
            Default success URL if not specified in success_urls dict.
        forms_context_name (str):
            Context variable name for the forms dictionary, defaults to "forms".
        bind_data_methods (list):
            HTTP methods that should bind request data to forms, defaults to ["POST", "PUT"].

    Notes:
        Custom form handling can be implemented by defining methods like:
        - get_{form_name}_initial() for custom initial values
        - create_{form_name}_form(**kwargs) for custom form creation
        - {form_name}_form_valid(form) for custom valid form handling
        - {form_name}_form_invalid(form) for custom invalid form handling
    """

    form_classes = {}
    prefixes = {}
    success_urls = {}
    grouped_forms = {}

    initial = {}
    prefix = None
    success_url = None
    forms_context_name = "forms"
    bind_data_methods = ["POST", "PUT"]
    _forms = {}

    def get_context_data(self, **kwargs):
        """Add the forms dictionary to the context.

        Keyword Parameters:
            **kwargs:
                Additional context variables from parent classes.

        Returns:
            (dict):
                The context dictionary with forms added under the forms_context_name key.
        """
        context = super(MultiFormMixin, self).get_context_data(**kwargs)
        context[self.get_forms_context_name()] = self.get_forms(self.get_form_classes(), bind_all=True)
        return context

    def get_form_classes(self):
        """Return all the form classes when requested.

        Returns:
            (dict):
                Dictionary of form names to form classes from the form_classes attribute.
        """
        return self.form_classes

    def get_forms(self, form_classes, form_names=None, bind_all=False):
        """Return all the forms as a dictionary of forms.

        Args:
            form_classes (dict):
                Dictionary mapping form names to form classes.

        Keyword Parameters:
            form_names (list or None):
                List of form names to bind with data. If None, no forms are bound unless bind_all is True.
            bind_all (bool):
                If True, bind data to all forms. Defaults to False.

        Returns:
            (dict):
                Dictionary mapping form names to instantiated form objects.
        """
        return dict(
            [
                (key, self._create_form(key, klass, (form_names and key in form_names) or bind_all))
                for key, klass in form_classes.items()
            ]
        )

    def get_forms_context_name(self):
        """Return the context object name for the dictionary of forms.

        Returns:
            (str):
                The context variable name for the forms dictionary.
        """
        return self.forms_context_name

    def get_form_kwargs(self, form_name, bind_form=False):
        """Build the form kwargs.

        Args:
            form_name (str):
                The name of the form to build kwargs for.

        Keyword Parameters:
            bind_form (bool):
                Whether to bind request data to the form. Defaults to False.

        Returns:
            (dict):
                Keyword arguments dictionary for form instantiation.
        """
        kwargs = {}
        kwargs.update({"initial": self.get_initial(form_name)})
        kwargs.update({"prefix": self.get_prefix(form_name)})

        if bind_form:
            kwargs.update(self._bind_form_data())

        return kwargs

    def forms_valid(self, forms, form_name):
        """Handle the case for valid forms returning the appropriate redirect.

        Args:
            forms (dict):
                Dictionary of all form instances.
            form_name (str):
                The name of the form that was validated.

        Returns:
            (HttpResponse):
                Response from the custom form_valid method or a redirect to the success URL.
        """
        form_valid_method = "%s_form_valid" % form_name
        self._forms = forms
        if hasattr(self, form_valid_method):
            return getattr(self, form_valid_method)(forms[form_name])
        else:
            return HttpResponseRedirect(self.get_success_url(form_name))

    def forms_invalid(self, forms, form_name):
        """Handle the case for invalid forms returning the appropriate redirect.

        Args:
            forms (dict):
                Dictionary of all form instances.
            form_name (str):
                The name of the form that was invalidated.

        Returns:
            (HttpResponse):
                Response from the custom form_invalid method or a re-render with form errors.
        """
        form_invalid_method = "%s_form_invalid" % form_name
        self._forms = forms
        if hasattr(self, form_invalid_method):
            return getattr(self, form_invalid_method)(forms[form_name])
        else:
            return self.render_to_response(self.get_context_data(forms=forms))

    def get_initial(self, form_name):
        """Return the initial values for the forms.

        Args:
            form_name (str):
                The name of the form to get initial values for.

        Returns:
            (dict):
                Initial values dictionary for the specified form.
        """
        initial_method = f"get_{form_name}_initial"
        if hasattr(self, initial_method):
            return getattr(self, initial_method)()
        else:
            return self.initial.copy()

    def get_prefix(self, form_name):
        """Get a prefix for the elements of a form.

        Args:
            form_name (str):
                The name of the form to get the prefix for.

        Returns:
            (str or None):
                The prefix for the form's fields, or None if not set.
        """
        return self.prefixes.get(form_name, self.prefix)

    def get_success_url(self, form_name=None):
        """Return the url to redirect to on success.

        Keyword Parameters:
            form_name (str or None):
                The name of the form to get the success URL for. Defaults to None.

        Returns:
            (str):
                The success URL for the specified form or the default success URL.
        """
        return self.success_urls.get(form_name, self.success_url)

    def _create_form(self, form_name, klass, bind_form):
        """Generate a specific form.

        Args:
            form_name (str):
                The name of the form to create.
            klass (type):
                The form class to instantiate.
            bind_form (bool):
                Whether to bind request data to the form.

        Returns:
            (Form):
                The instantiated form object.
        """
        form_kwargs = self.get_form_kwargs(form_name, bind_form)
        form_create_method = "create_%s_form" % form_name
        if hasattr(self, form_create_method):
            form = getattr(self, form_create_method)(**form_kwargs)
        else:
            form = klass(**form_kwargs)
        return form

    def _bind_form_data(self):
        """Attach the data to a form.

        Returns:
            (dict):
                Dictionary containing 'data' and 'files' keys if the request method matches
                bind_data_methods, otherwise an empty dictionary.
        """
        if self.request.method in ("POST", "PUT") and self.request.method in self.bind_data_methods:
            return {"data": self.request.POST, "files": self.request.FILES}
        if self.request.method in ("GET") and self.request.method in self.bind_data_methods:
            return {"data": self.request.GET, "files": self.request.FILES}
        return {}


class FormListView(FormMixin, ListView):
    """Provide a ListView with a form.

    This view combines a list view with form handling, enabling filtering or searching of list results
    through a form. The form is available in both GET and POST requests, with POST requests validating
    the form before rendering the filtered list.

    Attributes:
        success_url (str):
            Default success URL (not actually used as the view always re-renders). Defaults to "/".
        form (Form):
            The instantiated form object, available after get() or post() is called.
    """

    success_url = "/"  # Not actually used since we never redirect here

    @property
    def object_list(self):
        """Shim to make ListView work.

        Returns:
            (QuerySet):
                The queryset from get_queryset().
        """
        return self.get_queryset()

    @object_list.setter
    def object_list(self, valiue):
        """Do nothing since we're actually just an dummy for get_queryset.

        Args:
            valiue:
                The value to set (ignored).
        """

    def get(self, request, *args, **kwargs):
        """Handle GET requests and instantiates a blank version of the form before passing to ListView.get.

        Args:
            request (HttpRequest):
                The Django HTTP request object.
            *args:
                Variable length argument list.
            **kwargs:
                Arbitrary keyword arguments.

        Returns:
            (HttpResponse):
                The rendered list view with an unbound form.
        """
        form_class = self.get_form_class()
        if not getattr(self, "form", None):
            self.form = self.get_form(form_class)

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Handle POST requests.

        Instantiates a form instance with the passed POST variables and then checked for validity.
        Before going to ListView.get for rendering.

        Args:
            request (HttpRequest):
                The Django HTTP request object.
            *args:
                Variable length argument list.
            **kwargs:
                Arbitrary keyword arguments.

        Returns:
            (HttpResponse):
                The rendered list view with the bound form, showing validation errors if invalid.
        """
        form_class = self.get_form_class()
        self.form = self.get_form(form_class)
        if (
            self.form.is_valid()
        ):  # Divert to the main listview get where we will override the context data and get_queryset
            self.form_valid(self.form)  # We call this to record form values but not to return anything.
            return self.get(request, *args, **kwargs)
        else:
            return self.form_invalid(self.form)  # Handle a bad form

    def get_context_data(self, **kwargs):
        """Call the parent get_context_data before adding the current form as context.

        Keyword Parameters:
            **kwargs:
                Additional context variables from parent classes.

        Returns:
            (dict):
                The context dictionary with the form added under the 'form' key.
        """
        context = super().get_context_data(**kwargs)
        context["form"] = self.form
        return context


class ProcessMultipleFormsView(ProcessFormView):
    """Subclass of ProcessFormView to deal with multiple forms on a page.

    This view processes multiple forms that can be submitted individually, in groups, or all together.
    The form to process is determined by the 'action' POST parameter.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET requests.

        Args:
            request (HttpRequest):
                The Django HTTP request object.
            *args:
                Variable length argument list.
            **kwargs:
                Arbitrary keyword arguments.

        Returns:
            (HttpResponse):
                The rendered response with all unbound forms in context.
        """
        form_classes = self.get_form_classes()
        forms = self.get_forms(form_classes)
        return self.render_to_response(self.get_context_data(forms=forms))

    def post(self, request, *args, **kwargs):
        """Handle POST requests.

        Args:
            request (HttpRequest):
                The Django HTTP request object.
            *args:
                Variable length argument list.
            **kwargs:
                Arbitrary keyword arguments.

        Returns:
            (HttpResponse):
                The response after processing the submitted form(s).
        """
        form_classes = self.get_form_classes()
        form_name = request.POST.get("action")
        if self._individual_exists(form_name):
            return self._process_individual_form(form_name, form_classes)
        elif self._group_exists(form_name):
            return self._process_grouped_forms(form_name, form_classes)
        else:
            return self._process_all_forms(form_classes, form_name)

    def _individual_exists(self, form_name):
        """Check whether and individual form exists.

        Args:
            form_name (str):
                The name of the form to check.

        Returns:
            (bool):
                True if the form name exists in form_classes, False otherwise.
        """
        return form_name in self.form_classes

    def _group_exists(self, group_name):
        """Check whether a group of form exists.

        Args:
            group_name (str):
                The name of the group to check.

        Returns:
            (bool):
                True if the group name exists in grouped_forms, False otherwise.
        """
        return group_name in self.grouped_forms

    def _process_individual_form(self, form_name, form_classes):
        """Handle one single form.

        Args:
            form_name (str):
                The name of the form to process.
            form_classes (dict):
                Dictionary of all form classes.

        Returns:
            (HttpResponse):
                HttpResponseForbidden if form not found, otherwise the result of forms_valid or forms_invalid.
        """
        forms = self.get_forms(form_classes, (form_name,))
        form = forms.get(form_name)
        if not form:
            return HttpResponseForbidden()
        elif form.is_valid():
            return self.forms_valid(forms, form_name)
        else:
            return self.forms_invalid(forms, form_name)

    def _process_grouped_forms(self, group_name, form_classes):
        """Process a group of forms.

        Args:
            group_name (str):
                The name of the form group to process.
            form_classes (dict):
                Dictionary of all form classes.

        Returns:
            (HttpResponse):
                The result of forms_valid if all forms in the group are valid, otherwise forms_invalid.
        """
        form_names = self.grouped_forms[group_name]
        forms = self.get_forms(form_classes, form_names)
        if all([forms.get(form_name).is_valid() for form_name in form_names.values()]):
            return self.forms_valid(forms)
        else:
            return self.forms_invalid(forms)

    def _process_all_forms(self, form_classes, form_name=None):
        """Process all forms that were submitted in a request.

        Args:
            form_classes (dict):
                Dictionary of all form classes.

        Keyword Parameters:
            form_name (str or None):
                The name of the primary form being processed. Defaults to None.

        Returns:
            (HttpResponse):
                The result of forms_valid if all forms are valid, otherwise forms_invalid.
        """
        forms = self.get_forms(form_classes, None, True)
        if all([form.is_valid() for form in forms.values()]):
            return self.forms_valid(forms, form_name)
        else:
            return self.forms_invalid(forms, form_name)


class BaseMultipleFormsView(MultiFormMixin, ProcessMultipleFormsView):
    """A base view for displaying several forms.

    This class combines MultiFormMixin and ProcessMultipleFormsView to provide a complete
    view implementation for handling multiple forms without template rendering.
    """


class MultiFormsView(TemplateResponseMixin, BaseMultipleFormsView):
    """A view for displaying several forms, and rendering a template response.

    This class adds template rendering capability to BaseMultipleFormsView, making it
    a complete solution for views that need to display and process multiple forms.
    """


class PhotoDisplay(DetailView):
    """Return just the image tag for an image.

    This view renders a simple template containing only the photo's image tag, useful for
    embedding or displaying photos in isolation.

    Attributes:
        model (Model):
            The Photo model from photologue.
        template_name (str):
            Template path, defaults to "labman_utils/photo_tag.html".
        context_object_name (str):
            Context variable name for the photo object.
    """

    model = Photo
    template_name = "labman_utils/photo_tag.html"
    context_object_name = "photo"


class DocumentDialog(IsAuthenticaedViewMixin, HTMXFormMixin, UpdateView):
    """Produce the HTML for a document form in a dialog.

    This HTMX-enabled view handles creating and editing documents associated with equipment or locations.
    It provides dialog-based forms that can be embedded in other pages without full page reloads.

    Attributes:
        model (Model):
            The Document model.
        template_name (str):
            Template path for the dialog, defaults to "labman_utils/document_form.html".
        context_object_name (str):
            Context variable name for the document object.
    """

    model = Document
    template_name = "labman_utils/document_form.html"
    context_object_name = "this"

    def get_form_class(self):
        """Delay the import of the form class until we need it.

        Returns:
            (Form):
                The DocumentDialogForm class.
        """
        forms = import_module("labman_utils.forms")
        return forms.DocumentDialogForm

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the booking dialog.

        Keyword Parameters:
            **kwargs:
                Additional context variables.

        Returns:
            (dict):
                Context dictionary containing the document, related objects, and URLs for form submission.
        """
        context = super().get_context_data(**kwargs)
        context["current_url"] = self.request.htmx.current_url
        context["this"] = self.get_object()
        subject = "none"
        verb = "edit" if context["this"] else "new"
        if "equipment" in self.kwargs:
            context["equipment"] = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
            context["equipment_id"] = self.kwargs.get("equipment", None)
            subject = "equipment"
        if "location" in self.kwargs:
            context["location"] = Location.objects.get(pk=self.kwargs.get("location", None))
            context["location_id"] = self.kwargs.get("location", None)
            subject = "location"
        if subject == "none":
            args = tuple() if verb == "new" else (context["this"].pk,)
            context["post_url"] = reverse(f"labman_utils:{verb}_document", args=args)
        else:
            args = (
                (self.kwargs.get(subject, None),)
                if verb == "new"
                else (self.kwargs.get(subject, None), context["this"].pk)
            )
            context["post_url"] = reverse(f"labman_utils:{verb}_{subject}_document", args=args)

        context["this_id"] = getattr(context["this"], "pk", None)
        context["edit"] = self.get_object() is not None
        context["subject"] = subject
        return context

    def get_object(self, queryset=None):
        """Either get the Document or None.

        Keyword Parameters:
            queryset (QuerySet or None):
                Optional queryset to use for retrieving the object. Defaults to None.

        Returns:
            (Document or None):
                The document instance if found, otherwise None.
        """
        try:
            return super().get_object(queryset)
        except (Document.DoesNotExist, AttributeError):
            return None

    def get_initial(self):
        """Make initial entry.

        Returns:
            (dict):
                Initial form values with equipment and/or location if specified in URL kwargs.
        """
        if "equipment" in self.kwargs:
            equipment = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
        else:
            equipment = None
        if "location" in self.kwargs:
            location = Location.objects.get(pk=self.kwargs.get("location", None))
        else:
            location = None
        return {"equipment": equipment, "location": location}

    def htmx_form_valid_document(self, form):
        """Handle the HTMX submitted document form if it's all ok.

        Args:
            form (Form):
                The validated form instance.

        Returns:
            (HttpResponse):
                HTTP 204 response with a header to trigger a refresh of the files list.
        """
        self.object = form.save()
        if equipment := form.cleaned_data.get("equipment", None):
            equipment.files.add(self.object)
        if location := form.cleaned_data.get("location", None):
            location.files.add(self.object)
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshFiles",
            },
        )

    def htmx_delete_document(self, request, *args, **kwargs):
        """Handle the HTMX call that deletes a document.

        Args:
            request (HttpRequest):
                The Django HTTP request object.
            *args:
                Variable length argument list.
            **kwargs:
                Arbitrary keyword arguments.

        Returns:
            (HttpResponse):
                HttpResponseNotFound if document not found, HttpResponseForbidden if permission denied,
                otherwise HTTP 204 response with a header to trigger a refresh.
        """
        if not (document := self.get_object()):
            return HttpResponseNotFound("Unable to locate document.")
        self.object = document
        # Now check I actually have permission to do this...
        if not self.request.user.is_superuser:
            return HttpResponseForbidden("You must be a superuser to delete the file.")

        for equipment in self.object.equipment.all():
            equipment.files.remove(self.object)
        for location in self.object.location.all():
            location.files.remove(self.object)

        self.object.delete()

        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshFiles",
            },
        )


class DocumentLinkDialog(IsAuthenticaedViewMixin, HTMXFormMixin, UpdateView):
    """Produce the HTML for linking documents to equipment or locations in a dialog.

    This HTMX-enabled view handles linking existing documents to equipment or locations through
    a dialog interface. It dynamically generates the form based on the object being linked.

    Attributes:
        template_name (str):
            Template path for the dialog, defaults to "labman_utils/link_document_form.html".
        context_object_name (str):
            Context variable name for the object being linked.
    """

    template_name = "labman_utils/link_document_form.html"
    context_object_name = "this"

    def get_form_class(self):
        """Delay the import of the form class until we need it.

        Returns:
            (Form):
                A dynamically created ModelForm for the appropriate model (Equipment, Location, or Document).
        """
        if "equipment" in self.kwargs:
            model = Equipment
            fields = ["files"]
        elif "location" in self.kwargs:
            model = Location
            fields = ["files"]

        else:
            return DocumentLinksForm
        frmcls = forms.modelform_factory(
            model,
            fields=["id"] + fields,
            widgets={
                "id": forms.HiddenInput(),
            },
        )
        return frmcls

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the linking dialog.

        Keyword Parameters:
            **kwargs:
                Additional context variables.

        Returns:
            (dict):
                Context dictionary containing the object, related data, and post URL.
        """
        context = super().get_context_data(**kwargs)
        context["current_url"] = self.request.htmx.current_url
        if "equipment" in self.kwargs:
            context["equipment"] = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
            context["equipment_id"] = self.kwargs.get("equipment", None)
            context["post_url"] = reverse(
                "labman_utils:link_document_equipment", args=(self.kwargs.get("equipment", None),)
            )
        elif "location" in self.kwargs:
            context["location"] = Location.objects.get(pk=self.kwargs.get("location", None))
            context["location_id"] = self.kwargs.get("location", None)
            context["post_url"] = reverse(
                "labman_utils:link_document_location", args=(self.kwargs.get("location", None),)
            )
        else:
            context["post_url"] = reverse("labman_utils:link_document", args=(self.kwargs.get("pk", None),))

        context["this"] = self.get_object()

        context["this_id"] = getattr(context["this"], "pk", None)
        return context

    def get_object(self, queryset=None):
        """Either get the Equipment, Location, or Document object.

        Keyword Parameters:
            queryset (QuerySet or None):
                Optional queryset to use for retrieving the object. Defaults to None.

        Returns:
            (Model):
                The Equipment, Location, or Document instance based on URL kwargs.
        """
        if equipment := self.kwargs.get("equipment", None):
            return Equipment.objects.get(pk=equipment)
        elif location := self.kwargs.get("location", None):
            return Location.objects.get(pk=location)
        return Document.objects.get(pk=self.kwargs.get("pk", None))

    def get_initial(self):
        """Make initial entry.

        Returns:
            (dict):
                Initial form values with linked objects pre-populated.
        """
        if "equipment" in self.kwargs:
            thing = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
        elif "location" in self.kwargs:
            thing = Location.objects.get(pk=self.kwargs.get("location", None))
        else:
            this = self.get_object()
            equipment = [x for x in this.equipment.all()]
            locations = [x for x in this.location.all()]
            return {"id": this.id, "equipment": equipment, "location": locations}
        ret = {}  # {"id": thing.pk, "files": thing.files.all()}
        return ret

    def htmx_form_valid_document(self, form):
        """Handle the HTMX submitted linking form if it's all ok.

        Args:
            form (Form):
                The validated form instance.

        Returns:
            (HttpResponse):
                HTTP 204 response with a header to trigger a refresh of the files list.
        """
        self.object = form.save()
        this = self.object
        if isinstance(this, Document):  # Do the reverse linking.
            for equipment in this.equipment.all():
                if equipment not in form.cleaned_data["equipment"]:
                    this.equipment.remove(equipment)
            for equipment in form.cleaned_data["equipment"]:
                if this not in equipment.files.all():
                    equipment.files.add(this)
            for location in this.location.all():
                if location not in form.cleaned_data["location"]:
                    this.location.remove(location)
            for location in form.cleaned_data["location"]:
                if this not in location.files.all():
                    location.files.add(this)

        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshFiles",
            },
        )


class PhotoDialog(IsAuthenticaedViewMixin, HTMXFormMixin, UpdateView):
    """Produce the HTML for a photo form in a dialog.

    This HTMX-enabled view handles creating and editing photos associated with equipment, locations,
    or user accounts. It provides dialog-based forms for photo management.

    Attributes:
        model (Model):
            The Photo model from photologue.
        template_name (str):
            Template path for the dialog, defaults to "labman_utils/photo_form.html".
        context_object_name (str):
            Context variable name for the photo object.
    """

    model = Photo
    template_name = "labman_utils/photo_form.html"
    context_object_name = "this"

    def get_form_class(self):
        """Delay the import of the form class until we need it.

        Returns:
            (Form):
                The PhotoDialogForm class.
        """
        forms = import_module("labman_utils.forms")
        return forms.PhotoDialogForm

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the photo dialog.

        Keyword Parameters:
            **kwargs:
                Additional context variables.

        Returns:
            (dict):
                Context dictionary containing the photo, related objects (equipment, location, or account),
                and URLs for form submission.
        """
        context = super().get_context_data(**kwargs)
        context["current_url"] = self.request.htmx.current_url
        context["this"] = self.get_object()
        verb = "edit" if context["this"] else "new"
        context["edit"] = verb == "edit"
        context["this_id"] = getattr(context["this"], "pk", None)
        for name, model in {"equipment": Equipment, "location": Location, "account": Account}.items():
            if name in self.kwargs:
                context[name] = model.objects.get(pk=self.kwargs.get(name))
                context[f"{name}_id"] = self.kwargs.get(name)
                subject = name
                args = (
                    (self.kwargs.get(subject, None),)
                    if verb == "new"
                    else (self.kwargs.get(subject, None), context["this"].pk)
                )
                context["post_url"] = reverse(f"labman_utils:{verb}_{subject}_photo", args=args)
                context["subject"] = subject
                break
        else:
            args = tuple() if verb == "new" else (context["this"].pk,)
            context["post_url"] = reverse(f"labman_utils:{verb}_photo", args=args)

        return context

    def get_object(self, queryset=None):
        """Either get the Photo or None.

        Keyword Parameters:
            queryset (QuerySet or None):
                Optional queryset to use for retrieving the object. Defaults to None.

        Returns:
            (Photo or None):
                The photo instance if found, otherwise None.
        """
        try:
            return super().get_object(queryset)
        except (Photo.DoesNotExist, AttributeError):
            return None

    def get_initial(self):
        """Make initial entry.

        Returns:
            (dict):
                Initial form values with equipment, location, or account if specified in URL kwargs.
                Also sets the title to the object's name if available.
        """
        initial = {}
        for arg, model in {"equipment": Equipment, "location": Location, "account": Account}.items():
            if arg in self.kwargs:
                initial[arg] = model.objects.get(pk=self.kwargs.get(arg, None))
                initial["title"] = initial[arg].name
            else:
                initial[arg] = None
        return initial

    def htmx_form_valid_dialog(self, form):
        """Handle the HTMX submitted photo form if it's all ok.

        Args:
            form (Form):
                The validated form instance.

        Returns:
            (HttpResponse):
                HTTP 204 response with a header to trigger a refresh of the photos list.
        """
        self.object = form.save()
        for objname in ["equipment", "location", "account"]:
            if obj := form.cleaned_data.get(objname, None):
                obj.photos.add(self.object)
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshPhotos",
            },
        )

    def htmx_delete_photo(self, request, *args, **kwargs):
        """Handle the HTMX call that deletes a photo.

        Args:
            request (HttpRequest):
                The Django HTTP request object.
            *args:
                Variable length argument list.
            **kwargs:
                Arbitrary keyword arguments.

        Returns:
            (HttpResponse):
                HttpResponseNotFound if photo not found, HttpResponseForbidden if permission denied,
                otherwise HTTP 204 response with a header to trigger a refresh.
        """
        if not (photo := self.get_object()):
            return HttpResponseNotFound("Unable to locate photo.")
        self.object = photo
        # Now check I actually have permission to do this...
        if not self.request.user.is_superuser and not self.object.account.first() != self.request.user:
            return HttpResponseForbidden("You must be a superuser to delete the photo.")
        for attr in ["equipment", "location", "account"]:
            for obj in getattr(self.object, attr).all():
                obj.photos.remove(self.object)

        self.object.delete()

        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshPhotos",
            },
        )


class PhotoLinkDialog(IsAuthenticaedViewMixin, HTMXFormMixin, UpdateView):
    """Produce the HTML for linking photos to equipment, locations, or accounts in a dialog.

    This HTMX-enabled view handles linking existing photos to equipment, locations, or user accounts
    through a dialog interface. It dynamically generates the form based on the object being linked.

    Attributes:
        template_name (str):
            Template path for the dialog, defaults to "labman_utils/link_photo_form.html".
        context_object_name (str):
            Context variable name for the object being linked.
    """

    template_name = "labman_utils/link_photo_form.html"
    context_object_name = "this"

    def get_form_class(self):
        """Delay the import of the form class until we need it.

        Returns:
            (Form):
                A dynamically created ModelForm for the appropriate model (Equipment, Location, Account, or Photo).
        """
        for name, model in {"equipment": Equipment, "location": Location, "account": Account}.items():
            if name in self.kwargs:
                fields = ["id", "photos"]
                frmcls = forms.modelform_factory(
                    model,
                    fields=fields,
                    widgets={
                        "id": forms.HiddenInput(),
                    },
                )
                return frmcls
        return PhotoLinksForm

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the photo linking dialog.

        Keyword Parameters:
            **kwargs:
                Additional context variables.

        Returns:
            (dict):
                Context dictionary containing the object, related data, and post URL.
        """
        context = super().get_context_data(**kwargs)
        context["current_url"] = self.request.htmx.current_url
        for name, model in {"equipment": Equipment, "location": Location, "account": Account}.items():
            if name in self.kwargs:
                context[name] = model.objects.get(pk=self.kwargs.get(name))
                context[f"{name}_id"] = self.kwargs.get(name)
                context["post_url"] = reverse(f"labman_utils:link_photo_{name}", args=(self.kwargs.get(name),))
                break
        else:
            context["post_url"] = reverse("labman_utils:link_photo", args=(self.kwargs.get("pk", None),))

        context["this"] = self.get_object()
        context["this_id"] = getattr(context["this"], "pk", None)
        return context

    def get_object(self, queryset=None):
        """Either get the Equipment, Location, Account, or Photo object.

        Keyword Parameters:
            queryset (QuerySet or None):
                Optional queryset to use for retrieving the object. Defaults to None.

        Returns:
            (Model):
                The Equipment, Location, Account, or Photo instance based on URL kwargs.
        """
        if equipment := self.kwargs.get("equipment", None):
            return Equipment.objects.get(pk=equipment)
        elif location := self.kwargs.get("location", None):
            return Location.objects.get(pk=location)
        elif account := self.kwargs.get("account", None):
            return Account.objects.get(pk=account)
        return Photo.objects.get(pk=self.kwargs.get("pk", None))

    def get_initial(self):
        """Make initial entry.

        Returns:
            (dict):
                Initial form values with linked photos pre-populated.
        """
        for name, model in {"equipment": Equipment, "location": Location, "account": Account}.items():
            if name in self.kwargs:
                thing = model.objects.get(pk=self.kwargs.get(name))
                return {"photos": thing.photos.all()}
        this = self.get_object()
        equipment = [x for x in this.equipment.all()]
        location = [x for x in this.location.all()]
        account = [x for x in this.account.all()]
        return {"id": this.id, "equipment": equipment, "location": location, "account": account}

    def htmx_form_valid_photo(self, form):
        """Handle the HTMX submitted photo linking form if it's all ok.

        Args:
            form (Form):
                The validated form instance.

        Returns:
            (HttpResponse):
                HTTP 204 response with a header to trigger a refresh of the photos list.
        """
        self.object = form.save()
        this = self.object
        if isinstance(this, Photo):  # Do the reverse linking.
            for equipment in this.equipment.all():
                if equipment not in form.cleaned_data["equipment"]:
                    this.equipment.remove(equipment)
            for equipment in form.cleaned_data["equipment"]:
                if this not in equipment.photos.all():
                    equipment.photos.add(this)
            for location in this.location.all():
                if location not in form.cleaned_data["location"]:
                    this.location.remove(location)
            for location in form.cleaned_data["location"]:
                if this not in location.photos.all():
                    location.photos.add(this)
            for account in this.accounts.all():
                if account not in form.cleaned_data["account"]:
                    this.accounts.remove(account)
            for account in form.cleaned_data["account"]:
                if this not in account.photos.all():
                    account.photos.add(this)

        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshPhotos",
            },
        )


class FlatPageDialog(IsAuthenticaedViewMixin, HTMXFormMixin, UpdateView):
    """Produce the HTML for a flat page form in a dialog.

    This HTMX-enabled view handles creating and editing flat pages associated with equipment or locations.
    It provides dialog-based forms for content page management.

    Attributes:
        model (Model):
            The FlatPage model from django.contrib.flatpages.
        template_name (str):
            Template path for the dialog, defaults to "labman_utils/flatpage_form.html".
        context_object_name (str):
            Context variable name for the flat page object.
        form_class (Form):
            The form class to use, defaults to FlatPageForm.
    """

    model = FlatPage
    template_name = "labman_utils/flatpage_form.html"
    context_object_name = "this"
    form_class = FlatPageForm

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the flat page dialog.

        Keyword Parameters:
            **kwargs:
                Additional context variables.

        Returns:
            (dict):
                Context dictionary containing the flat page, related objects (equipment or location),
                and URLs for form submission.
        """
        context = super().get_context_data(**kwargs)
        context["current_url"] = self.request.htmx.current_url
        context["this"] = self.get_object()
        verb = "edit" if context["this"] else "new"
        context["edit"] = verb == "edit"
        context["this_id"] = getattr(context["this"], "pk", None)
        for name, model in {"equipment": Equipment, "location": Location}.items():
            if name in self.kwargs:
                context[name] = model.objects.get(pk=self.kwargs.get(name))
                context[f"{name}_id"] = self.kwargs.get(name)
                subject = name
                args = (
                    (self.kwargs.get(subject, None),)
                    if verb == "new"
                    else (self.kwargs.get(subject, None), context["this"].pk)
                )
                context["post_url"] = reverse(f"labman_utils:{verb}_{subject}_flatpage", args=args)
                context["subject"] = subject
                break
        else:
            args = tuple() if verb == "new" else (context["this"].pk,)
            context["post_url"] = reverse(f"labman_utils:{verb}_flatpage", args=args)

        return context

    def get_object(self, queryset=None):
        """Either get the FlatPage or None.

        Keyword Parameters:
            queryset (QuerySet or None):
                Optional queryset to use for retrieving the object. Defaults to None.

        Returns:
            (FlatPage or None):
                The flat page instance if found, otherwise None.
        """
        try:
            return super().get_object(queryset)
        except (FlatPage.DoesNotExist, AttributeError):
            return None

    def get_initial(self):
        """Make initial entry.

        Returns:
            (dict):
                Initial form values with equipment or location if specified in URL kwargs.
        """
        initial = {}
        for arg, model in {"equipment": Equipment, "location": Location}.items():
            if arg in self.kwargs:
                initial[arg] = model.objects.get(pk=self.kwargs.get(arg, None))
            else:
                initial[arg] = None
        return initial

    def htmx_form_valid_dialog(self, form):
        """Handle the HTMX submitted flat page form if it's all ok.

        Args:
            form (Form):
                The validated form instance.

        Returns:
            (HttpResponse):
                HTTP 204 response with a header to trigger a refresh of the pages list.
        """
        self.object = form.save()
        for objname in ["equipment", "location"]:
            if obj := form.cleaned_data.get(objname, None):
                obj.pages.add(self.object)
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshPages",
            },
        )

    def htmx_delete_flatpage(self, request, *args, **kwargs):
        """Handle the HTMX call that deletes a flat page.

        Args:
            request (HttpRequest):
                The Django HTTP request object.
            *args:
                Variable length argument list.
            **kwargs:
                Arbitrary keyword arguments.

        Returns:
            (HttpResponse):
                HttpResponseNotFound if flat page not found, HttpResponseForbidden if permission denied,
                otherwise HTTP 204 response with a header to trigger a refresh.
        """
        if not (flatpage := self.get_object()):
            return HttpResponseNotFound("Unable to locate flatpage.")
        self.object = flatpage
        # Now check I actually have permission to do this...
        if not self.request.user.is_superuser and not self.object.account.first() != self.request.user:
            return HttpResponseForbidden("You must be a superuser to delete the flatpage.")
        for attr in ["equipment", "location"]:
            for obj in getattr(self.object, attr).all():
                obj.pages.remove(self.object)

        self.object.delete()

        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshPages",
            },
        )


class FlatPageLinkDialog(IsAuthenticaedViewMixin, HTMXFormMixin, UpdateView):
    """Link pages to objects.

    This HTMX-enabled view handles linking existing flat pages to equipment or locations through
    a dialog interface. It dynamically generates the form based on the object being linked.

    Attributes:
        template_name (str):
            Template path for the dialog, defaults to "labman_utils/link_flatpage_form.html".
        context_object_name (str):
            Context variable name for the object being linked.
        linked_objects (dict):
            Dictionary mapping object type names to their model classes (equipment and location).
    """

    template_name = "labman_utils/link_flatpage_form.html"
    context_object_name = "this"
    linked_objects = {"equipment": Equipment, "location": Location}

    def get_form_class(self):
        """Delay the import of the form class until we need it.

        Returns:
            (Form):
                A dynamically created ModelForm for the appropriate model (Equipment, Location, or FlatPage).
        """
        for name, model in self.linked_objects.items():
            if name in self.kwargs:
                fields = ["id", "pages"]
                frmcls = forms.modelform_factory(
                    model,
                    fields=fields,
                    widgets={
                        "id": forms.HiddenInput(),
                    },
                )
                return frmcls
        return FlatPagesLinksForm

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the flat page linking dialog.

        Keyword Parameters:
            **kwargs:
                Additional context variables.

        Returns:
            (dict):
                Context dictionary containing the object, related data, and post URL.
        """
        context = super().get_context_data(**kwargs)
        context["current_url"] = self.request.htmx.current_url
        for name, model in self.linked_objects.items():
            if name in self.kwargs:
                context[name] = model.objects.get(pk=self.kwargs.get(name))
                context[f"{name}_id"] = self.kwargs.get(name)
                context["post_url"] = reverse(f"labman_utils:link_flatpage_{name}", args=(self.kwargs.get(name),))
                break
        else:
            context["post_url"] = reverse("labman_utils:link_flatpage", args=(self.kwargs.get("pk", None),))

        context["this"] = self.get_object()
        context["this_id"] = getattr(context["this"], "pk", None)
        return context

    def get_object(self, queryset=None):
        """Either get the Equipment, Location, or FlatPage object.

        Keyword Parameters:
            queryset (QuerySet or None):
                Optional queryset to use for retrieving the object. Defaults to None.

        Returns:
            (Model):
                The Equipment, Location, or FlatPage instance based on URL kwargs.
        """
        for name, model in self.linked_objects.items():
            if thing := self.kwargs.get(name, None):
                return model.objects.get(pk=thing)
        return FlatPage.objects.get(pk=self.kwargs.get("pk", None))

    def get_initial(self):
        """Make initial entry.

        Returns:
            (dict):
                Initial form values with linked flat pages pre-populated.
        """
        for name, model in self.linked_objects.items():
            if name in self.kwargs:
                thing = model.objects.get(pk=self.kwargs.get(name))
                return {"flatpages": thing.pages.all()}
        this = self.get_object()
        equipment = [x for x in this.equipment.all()]
        location = [x for x in this.location.all()]
        account = [x for x in this.account.all()]
        return {"id": this.id, "equipment": equipment, "location": location, "account": account}

    def htmx_form_valid_flatpage(self, form):
        """Handle the HTMX submitted flat page linking form if it's all ok.

        Args:
            form (Form):
                The validated form instance.

        Returns:
            (HttpResponse):
                HTTP 204 response with a header to trigger a refresh of the pages list.
        """
        self.object = form.save()
        this = self.object
        if isinstance(this, FlatPage):  # Do the reverse linking.
            for field in self.linked_objects:
                for thing in getattr(this, field).all():
                    if thing not in form.cleaned_data[field]:
                        getattr(this, field).remove(thing)
                for thing in form.cleaned_data[field]:
                    if this not in thing.pages.all():
                        thing.pages.add(this)

        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshPagess",
            },
        )
