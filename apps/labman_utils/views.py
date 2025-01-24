# -*- coding: utf-8 -*-
"""
Created on Tue Jul 18 14:56:26 2023

@author: phygbu
"""
# Python imports
from importlib import import_module

# Django imports
from django import forms
from django.apps import apps
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseNotModified,
)
from django.urls import reverse
from django.views.generic import DetailView, UpdateView

# external imports
from htmx_views.views import HTMXFormMixin
from photologue.models import Photo

# app imports
from .models import Document

# from sortedm2m.admin import OrderedAutocomplete


Equipment = apps.get_model(app_label="equipment", model_name="equipment")
Location = apps.get_model(app_label="equipment", model_name="location")


class IsAuthenticaedViewMixin(UserPassesTestMixin):
    login_url = "/login"

    def test_func(self):
        return hasattr(self, "request") and not self.request.user.is_anonymous


class IsSuperuserViewMixin(IsAuthenticaedViewMixin):
    def test_func(self):
        return super().test_finc() and self.request.user.is_superuser


class IsStaffViewMixin(IsSuperuserViewMixin):
    def test_func(self):
        return IsAuthenticaedViewMixin.test_func(self) and (self.request.user.is_staff or super().test_finc())


class PhotoDisplay(DetailView):
    """Return just the image tag for an image."""

    model = Photo
    template_name = "labman_utils/photo_tag.html"
    context_obkect_name = "photo"


class DocumentDIalog(IsAuthenticaedViewMixin, HTMXFormMixin, UpdateView):
    """Prdoce the html for a booking form in the dialog."""

    model = Document
    template_name = "labman_utils/document_form.html"
    context_object_name = "this"

    def get_form_class(self):
        """Delay the import of the form class until we need it."""
        forms = import_module("labman_utils.forms")
        return forms.DocumentDialogForm

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the booking dialog."""
        context = super().get_context_data(_context=True, **kwargs)
        context["current_url"] = self.request.htmx.current_url
        context["this"] = self.get_object()
        verb = "edit" if context["this"] else "new"
        if "equipment" in self.kwargs:
            context["equipment"] = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
            context["equipment_id"] = self.kwargs.get("equipment", None)
            subject = "equipment"
        if "location" in self.kwargs:
            context["location"] = Location.objects.get(pk=self.kwargs.get("location", None))
            context["location_id"] = self.kwargs.get("location", None)
            subject = "location"
        args = (
            (self.kwargs.get(subject, None),)
            if verb == "new"
            else (self.kwargs.get(subject, None), context["this"].pk)
        )
        context["post_url"] = reverse(f"labman_utils:{verb}_{subject}_document", args=args)

        context["this_id"] = getattr(context["this"], "pk", None)
        context["edit"] = self.get_object() is not None
        return context

    def get_object(self, queryset=None):
        """Either get the BookingEntry or None."""
        try:
            return super().get_object(queryset)
        except (Document.DoesNotExist, AttributeError):
            return None

    def get_initial(self):
        """Make initial entry."""
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
        """Handle the HTMX submitted booking form if it's all ok."""
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
        """Handle the HTMX call that deletes a booking."""
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


class DocumentLinkDIalog(IsAuthenticaedViewMixin, HTMXFormMixin, UpdateView):
    """Prdoce the html for a booking form in the dialog."""

    template_name = "labman_utils/link_document_form.html"
    context_object_name = "this"

    def get_form_class(self):
        """Delay the import of the form class until we need it."""
        if "equipment" in self.kwargs:
            model = Equipment
        elif "location" in self.kwargs:
            model = Location
        else:
            model = None
        frmcls = forms.modelform_factory(
            model,
            fields=["id", "files"],
            widgets={
                "id": forms.HiddenInput(),
            },
        )
        output = frmcls().as_div()
        return frmcls

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the booking dialog."""
        context = super().get_context_data(_context=True, **kwargs)
        context["current_url"] = self.request.htmx.current_url
        if "equipment" in self.kwargs:
            context["equipment"] = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
            context["equipment_id"] = self.kwargs.get("equipment", None)
            context["post_url"] = reverse(
                "labman_utils:link_document_equipment", args=(self.kwargs.get("equipment", None),)
            )
        if "location" in self.kwargs:
            context["location"] = Location.objects.get(pk=self.kwargs.get("location", None))
            context["location_id"] = self.kwargs.get("location", None)
            context["post_url"] = reverse(
                "labman_utils:link_document_location", args=(self.kwargs.get("location", None),)
            )

        context["this"] = self.get_object()

        context["this_id"] = getattr(context["this"], "pk", None)
        return context

    def get_object(self, queryset=None):
        """Either get the BookingEntry or None."""
        if equipment := self.kwargs.get("equipment", None):
            return Equipment.objects.get(pk=equipment)
        if location := self.kwargs.get("location", None):
            return Location.objects.get(pk=location)
        return None

    def get_initial(self):
        """Make initial entry."""
        if "equipment" in self.kwargs:
            thing = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
        elif "location" in self.kwargs:
            thing = Location.objects.get(pk=self.kwargs.get("location", None))
        else:
            return {}
        ret = {}  # {"id": thing.pk, "files": thing.files.all()}
        return ret

    def htmx_form_valid_document(self, form):
        """Handle the HTMX submitted booking form if it's all ok."""
        self.object = form.save()
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshFiles",
            },
        )
