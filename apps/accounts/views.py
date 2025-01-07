#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Views for the accounts apps."""
# Django imports
from django import views
from django.views.generic import TemplateView

# external imports
from bookings.forms import BookinngDialogForm
from htmx_views.views import HTMXProcessMixin
from labman_utils.views import IsAuthenticaedViewMixin

# app imports
from .models import Account, Project


# Create your views here.
class UserAccountView(IsAuthenticaedViewMixin, HTMXProcessMixin, views.generic.DetailView):
    """A template detail view that gets a specific user."""

    context_object_name = "account"
    template_name = "accounts/user_account.html"
    template_name_projecttab = "accounts/parts/myaccount_projects.html"
    template_name_underlingstab = "accounts/parts/myaccount_underlings.html"
    template_name_userlisttab = "accounts/parts/myaccount_userlist.html"
    slug_field = "username"
    slug_url_kwarg = "username"
    model = Account


class MyAccountView(UserAccountView):
    """A template detail view that gets the current logged in user."""

    context_object_name = "account"
    template_name = "accounts/myaccount.html"
    template_name_projecttab = "accounts/parts/myaccount_projects.html"
    template_name_underlingstab = "accounts/parts/myaccount_underlings.html"
    template_name_userlisttab = "accounts/parts/myaccount_userlist.html"

    def get_object(self, queryset=None):
        """Always return the current logged in user."""
        return self.request.user


class ProjectView(IsAuthenticaedViewMixin, HTMXProcessMixin, TemplateView):
    """Make a list of user projects."""

    template_name_id_project = "accounts/parts/projects_options.html"
    template_name_full_description = "accounts/parts/project_description_full.html"
    template_name_short_description = "accounts/parts/project_description_short.html"

    def get_context_data_id_project(self, **kwargs):
        """Add the projects for this yser."""
        context = super().get_context_data(_context=True, **kwargs)
        form = BookinngDialogForm(self.request.GET)
        if form.is_valid() or getattr(form, "cleaned_data", {}).get("user", None):
            projects = form.cleaned_data["user"].project.all()
            context["selected"] = form.cleaned_data["project"]
        else:
            context["errors"] = form.errors
            projects = Project.objects.none()
        context["projects"] = projects
        return context

    def get_context_data_full_description(self, **kwargs):
        """Add the projects for this yser."""
        context = super().get_context_data(_context=True, **kwargs)
        if project_id := self.request.GET.get("project_id", None):
            try:
                project = Project.objects.get(pk=int(project_id))
                context["project"] = project
            except (ValueError, TypeError, Project.DoesNotExist):
                context["project"] = None

        return context

    get_context_data_short_description = get_context_data_full_description
