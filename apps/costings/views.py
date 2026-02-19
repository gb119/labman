#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Views for the accounts apps."""

# Python imports
import json

# Django imports
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
)
from django.urls import reverse
from django.views.generic import TemplateView, UpdateView

# external imports
from bookings.forms import BookinngDialogForm
from htmx_views.views import HTMXFormMixin, HTMXProcessMixin
from labman_utils.views import IsAuthenticaedViewMixin, IsSuperuserViewMixin

# app imports
from .forms import CostCentreDialogForm
from .models import CostCentre


class Cost_CentreView(IsAuthenticaedViewMixin, HTMXProcessMixin, TemplateView):
    """Make a list of user CostCentre."""

    template_name_id_cost_centre = "costings/parts/cost_centres_options.html"
    template_name_full_description = "costings/parts/cost_cntre_description_full.html"
    template_name_short_description = "costings/parts/cost_cntre_description_short.html"

    def get_context_data_id_cost_centre(self, **kwargs):
        """Add the cost_centres for this user."""
        context = super().get_context_data(**kwargs)
        form = BookinngDialogForm(self.request.GET)
        if form.is_valid() or getattr(form, "cleaned_data", {}).get("user", None):
            cost_centres = form.cleaned_data["user"].project.all()
            context["selected"] = form.cleaned_data["cost_centre"]
        else:
            context["errors"] = form.errors
            cost_centres = CostCentre.objects.none()
        context["cost_centres"] = cost_centres
        return context

    def get_context_data_full_description(self, **kwargs):
        """Add the cost_centres for this yser."""
        context = super().get_context_data(**kwargs)
        if cost_centre_id := self.request.GET.get("cost_centre_id", self.request.GET.get("cost_centre_id", None)):
            try:
                cost_centre = CostCentre.objects.get(pk=int(cost_centre_id))
                context["cost_centre"] = cost_centre
            except (ValueError, TypeError, CostCentre.DoesNotExist):
                context["cost_centre"] = None

        return context

    get_context_data_short_description = get_context_data_full_description


class CostCentreDialog(IsSuperuserViewMixin, HTMXFormMixin, UpdateView):
    """HTMX dialog for creating and editing cost centres.

    Provides an HTMX-powered dialog interface for managing cost centres
    (projects). Supports both creating new cost centres and editing existing ones.
    Only accessible to superusers.

    Attributes:
        model: CostCentre model class.
        template_name (str): Template for the cost centre form dialog.
        context_object_name (str): Name for the object in template context.
        form_class: Form class for cost centre entries.
    """

    model = CostCentre
    template_name = "costings/cost_centre_form.html"
    context_object_name = "this"
    form_class = CostCentreDialogForm

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the cost centre dialog.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary with URLs and edit state information.
        """
        context = super().get_context_data(**kwargs)
        context["current_url"] = self.request.htmx.current_url
        context["this"] = self.get_object()
        verb = "edit" if context["this"] else "new"
        args = (context["this"].pk,) if verb == "edit" else tuple()
        context["post_url"] = reverse(f"costings:{verb}_cost_centre", args=args)
        context["edit"] = self.get_object() is not None
        return context

    def get_object(self, queryset=None):
        """Either get the CostCentre entry or None.

        Keyword Parameters:
            queryset: Optional queryset to filter the object lookup.

        Returns:
            (CostCentre or None): The cost centre if found, otherwise None.
        """
        try:
            return super().get_object(queryset)
        except (CostCentre.DoesNotExist, AttributeError, KeyError):
            return None

    def get_initial(self):
        """Get initial form data for editing.

        Returns:
            (dict): Initial form data with accounts if editing an existing cost centre.
        """
        initial = super().get_initial()
        if obj := self.get_object():
            initial["accounts"] = list(obj.accounts.all())
        return initial

    def htmx_form_valid_costcentre(self, form):
        """Handle the HTMX submitted cost centre form if valid.

        Args:
            form: The validated form containing cost centre data.

        Returns:
            (HttpResponse): Empty response with HTMX trigger to refresh projects list.
        """
        self.object = form.save()

        # Handle the accounts many-to-many relationship
        if "accounts" in form.cleaned_data:
            # Clear existing relationships and set new ones
            self.object.accounts.set(form.cleaned_data["accounts"])

        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshProjects",
            },
        )

    def htmx_delete_costcentre(self, request, *args, **kwargs):
        """Handle the HTMX call that deletes a cost centre.

        Args:
            request: The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            (HttpResponse): Empty response with HTMX trigger to refresh projects list.

        Raises:
            HttpResponseNotFound: If the cost centre cannot be found.
            HttpResponseForbidden: If user lacks permission to delete the entry.
        """
        if not (cost_centre := self.get_object()):
            return HttpResponseNotFound("Unable to locate cost centre.")
        self.object = cost_centre

        if not self.request.user.is_superuser:
            return HttpResponseForbidden("You must be a superuser to delete the cost centre.")

        self.object.delete()

        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshProjects",
            },
        )
