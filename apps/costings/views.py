#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Views for the accounts apps."""
# Django imports
from django.views.generic import TemplateView

# external imports
from bookings.forms import BookinngDialogForm
from htmx_views.views import HTMXProcessMixin
from labman_utils.views import IsAuthenticaedViewMixin

# app imports
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
