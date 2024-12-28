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
from .models import DocumentSignOff, Equipment

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


class EquipmentDetailView(HTMXProcessMixin, views.generic.DetailView):
    """Templated view for Equipment detail."""

    template_name = "equipment/equipment_detail.html"
    template_name_resourcestab = "equipment/parts/equipment_detail_resources.html"
    template_name_pagestab = "equipment/parts/equipment_detail_pages.html"
    template_name_userlisttab = "equipment/parts/equipment_detail_userlist.html"
    template_name_scheduletab = "equipment/parts/equipment_detail_schedule.html"
    model = Equipment

    def get_context_data_scheduletab(self, **kwargs):
        """Build the context for the calendar display."""
        context = super().get_context_data(_context=True, **kwargs)
        equipment = context["equipment"]
        date_vec = calendar_date_vector(yyyymmdd_to_date(self.kwargs.get("date", dt.today().strftime("%Y%m%d"))))
        time_vec = calendar_time_vector()
        table = CalTable(
            request=self.request,
            equipment=equipment,
            date_vec=date_vec,
            time_vec=time_vec,
            table_contents=np.array([["&nbsp;"] * (len(date_vec) + 1)] * (len(time_vec) + 1)),
        )
        table.classes += " table-bordered"
        target_range = DateTimeTZRange(
            dt.combine(date_vec[0], time_vec[0], tzinfo=DEFAULT_TZ),
            dt.combine(date_vec[-1], time_vec[-1], tzinfo=DEFAULT_TZ),
        )
        for entry in equipment.bookings.filter(slot__overlap=target_range):
            row_start, col_start = datetime_to_coord(entry.slot.lower, date_vec, time_vec)
            row_end, col_end = datetime_to_coord(entry.slot.upper, date_vec, time_vec)
            if col_start == col_end:  # single day
                table[row_start, col_start].rowspan = max(row_end - row_start, 1)
                table[row_start, col_start].content = entry.user.display_name
                table[row_start, col_start].classes += " bg-success p-3 text-center"
            else:  # spans day boundaries
                table[row_start, col_start].rowspan = len(time_vec) - row_start + 1
                table[row_start, col_start].content = entry.user.display_name
                table[row_start, col_start].classes += " bg-success p-3 text-center"
                for col in range(col_start + 1, col_end):
                    table[1, col].rowspan = len(time_vec)
                    table[1, col].content = entry.user.display_name
                    table[1, col].classes += " bg-success p-3 text-center"
                table[1, col_end].rowspan = max(1, row_end)
                table[1, col_end].content = entry.user.display_name
                table[1, col_end].classes += " bg-success p-3 text-center"

        context["cal"] = table
        context["start"] = date_vec[0]
        context["end"] = date_vec[-1]
        context["entries"] = equipment.bookings.filter(slot__overlap=target_range)

        return context
