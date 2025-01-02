# -*- coding: utf-8 -*-
"""
Created on Sun Jun 25 18:16:19 2023

@author: phygbu
"""
# Python imports
from datetime import (
    date as Date,
    datetime as dt,
    time as Time,
    timedelta as td,
)

# Django imports
from django import views
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.template import Template

# external imports
import numpy as np
import pytz
from accounts.models import Account, Project
from bookings.forms import BookinngDialogForm
from bookings.models import BookingEntry
from bookings.views import (
    CalTable,
    calendar_date_vector,
    calendar_time_vector,
    datetime_to_coord,
    yyyymmdd_to_date,
)
from extra_views import FormSetView
from htmx_views.views import HTMXProcessMixin
from labman_utils.views import IsAuthenticaedViewMixin
from psycopg2.extras import DateTimeTZRange

# app imports
from .forms import SignOffForm
from .models import DocumentSignOff, Equipment, Location

DEFAULT_TZ = pytz.timezone(settings.TIME_ZONE)

# Create your views here.


class SignOffFormSetView(IsAuthenticaedViewMixin, FormSetView):
    """Provides the view for signing off risk assessments and SOPs to be allowed to book equipment."""

    template_name = "equipment/sign-off.html"
    form_class = SignOffForm
    success_url = "/accounts/me/"
    factory_kwargs = {"extra": 0, "max_num": None, "can_order": False, "can_delete": False}

    def get_initial(self):
        equipment_id = int(self.kwargs["equipment"])
        equipment = Equipment.objects.get(pk=equipment_id)
        docs = equipment.files.filter(category__in=["ra", "sop"])
        dataset = []
        for doc in docs:
            try:
                dso = DocumentSignOff.objects.get(user=self.request.user, document=doc, version=doc.version)
            except ObjectDoesNotExist:
                dso = DocumentSignOff(user=self.request.user, document=doc, version=doc.version)
            row = {"document": doc, "user": self.request.user, "version": doc.version, "signed": dso.pk is not None}
            if dso.pk:
                row["id"] = dso.id
            dataset.append(row)
        return dataset

    def formset_valid(self, formset):
        equipment_id = int(self.kwargs["equipment"])
        equipment = Equipment.objects.get(pk=equipment_id)
        data = None
        for form in formset.forms:
            data = form.cleaned_data
            if data["signed"]:
                dso, _ = DocumentSignOff.objects.get_or_create(
                    user=self.request.user, document=data["document"], version=data["document"].version
                )
                dso.save()
        if data is None:  # Force userlist save if no docs to sign!
            equipment.users.get(user=self.request.user).save()

        return super().formset_valid(formset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docs = [x.initial["document"] for x in context["formset"].forms]
        context["docs"] = docs
        return context


class EquipmentDetailView(HTMXProcessMixin, IsAuthenticaedViewMixin, views.generic.DetailView):
    """Templated view for Equipment detail."""

    template_name = "equipment/equipment_detail.html"
    template_name_resourcestab = "equipment/parts/equipment_detail_resources.html"
    template_name_pagestab = "equipment/parts/equipment_detail_pages.html"
    template_name_userlisttab = "equipment/parts/equipment_detail_userlist.html"
    template_name_scheduletab = "equipment/parts/equipment_detail_schedule.html"
    template_name_schedule_container = "equipment/parts/equipment_detail_schedule.html"
    model = Equipment

    def get_context_data_scheduletab(self, **kwargs):
        """Build the context for the calendar display."""
        context = super().get_context_data(_context=True, **kwargs)
        equipment = context["equipment"]
        # Build the calendar rows from the shifts.
        time_vec = equipment.calendar_time_vector
        time_vec = calendar_time_vector() if time_vec is None else time_vec
        table = CalTable(
            date=self.kwargs.get("date", int(self.request.GET.get("date", dt.today().strftime("%Y%m%d")))),
            request=self.request,
            equipment=equipment,
            table_contents="&nbsp;",
        )
        table.classes += " table-bordered"
        entries = table.fill_entries(equipment)

        context["cal"] = table
        context["start"] = table.date_vec[0]
        context["end"] = table.date_vec[-1]
        context["start_date"] = table.date_vec[0].strftime("%Y%m%d")
        context["entries"] = entries
        context["form"] = BookinngDialogForm()

        return context

        return context

    get_context_data_schedule_container = get_context_data_scheduletab


class ModelListView(HTMXProcessMixin, IsAuthenticaedViewMixin, views.generic.ListView):
    """Setup a tabbed view of lists of various things."""

    template_name = "equipment/lists.html"
    template_name_equipmenttab = "equipment/parts/equipment_list.html"
    template_name_locationstab = "equipment/parts/locations_list.html"
    template_name_projectstab = "equipment/parts/projects_list.html"
    template_name_accountstab = "equipment/parts/accounts_list.html"

    context_object_equipmenttab = "equipment"
    context_object_locationstab = "locations"
    context_object_projectstab = "project"
    context_object_accountstab = "accounts"

    def get_queryset(self):
        """Get different querysets for each htmx query."""
        if not getattr(self.request, "htmx", False):
            return Account.objects.all()
        match getattr(self.request.htmx, "trigger", ""):
            case "equipment-tab":
                qs = Equipment.objects.all().order_by("name")
            case "locations-tab":
                qs = Location.objects.all().order_by("code", "name")
            case "projects-tab":
                qs = Project.objects.all().order_by("name")
            case _:
                qs = Account.objects.all().order_by("last_name", "first_name")
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
