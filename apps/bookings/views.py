# -*- coding: utf-8 -*-
"""View definitions for the bookings app."""
# Python imports
import io
import json
from datetime import datetime as dt, time as Time, timedelta as td
from itertools import chain

# Django imports
from django import views
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.backends.postgresql.psycopg_any import DateTimeTZRange
from django.db.models import Count, Q
from django.http import (
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseNotModified,
    StreamingHttpResponse,
)
from django.utils.text import slugify

# external imports
import numpy as np
import pandas as pd
import pytz
from accounts.models import Account
from costings.models import CostCentre
from easy_pdf.rendering import render_to_pdf_response
from equipment.models import Equipment
from equipment.tables import CalTable
from htmx_views.views import HTMXFormMixin
from labman_utils.views import FormListView, IsAuthenticaedViewMixin
from psycopg2.extras import DateTimeTZRange

# app imports
from . import forms, models

DEFAULT_TZ = pytz.timezone(settings.TIME_ZONE)


def delta_time(time_1: Time, time_2: Time) -> int:
    """Return the number of seconds betweetn time_1 and time_2."""
    if not isinstance(time_1, dt):
        dtime_1 = dt.combine(dt.today(), time_1, tzinfo=DEFAULT_TZ)
    else:
        dtime_1 = time_1
    if not isinstance(time_2, dt):
        dtime_2 = dt.combine(dt.today(), time_2, tzinfo=DEFAULT_TZ)
    else:
        dtime_2 = time_2
    dtt = dtime_2 - dtime_1
    return dtt.total_seconds()


class CalendarView(IsAuthenticaedViewMixin, views.generic.DetailView):
    """Make a calendar display for an equipment item and date."""

    template_name = "bookings/equipment_calendar.html"
    model = Equipment
    slug_url_kwarg = "equipment"
    slug_field = "pk"
    context_object_name = "equipment"

    def get_context_data(self, **kwargs):
        """Build the context for the calendar display."""
        context = super().get_context_data(**kwargs)
        # Build the calendar rows from the shifts.
        date = self.kwargs.get("date", int(self.request.GET.get("date", dt.today().strftime("%Y%m%d"))))
        context["start_date"] = date
        date_obj = dt.strptime(str(date), "%Y%m%d")
        back_date = date_obj - td(days=7)
        forward_date = date_obj + td(days=7)
        context["back_date"] = back_date.strftime("%Y%m%d")
        context["forward_date"] = forward_date.strftime("%Y%m%d")
        context["mode"] = "single"
        context["form"] = forms.BookinngDialogForm()
        return context


class AllCalendarView(IsAuthenticaedViewMixin, views.generic.TemplateView):
    """Make a calendar display for an equipment item and date."""

    template_name = "bookings/equipment_all_calendar.html"

    def get_context_data(self, **kwargs):
        """Build the context for the calendar display."""
        context = super().get_context_data(**kwargs)
        # Build the calendar rows from the shifts.
        try:
            date = self.kwargs.get("date", int(self.request.GET.get("date", dt.today().strftime("%Y%m%d"))))
        except ValueError:
            date = self.request.GET.get("date", dt.today().strftime("%Y-%m-%d"))
            date = dt.strptime(str(date), "%Y-%m-%d")
            date = int(date.strftime("%Y%m%d"))
        context["start_date"] = date
        date_obj = dt.strptime(str(date), "%Y%m%d")
        back_date = date_obj - td(days=7)
        forward_date = date_obj + td(days=7)
        context["back_date"] = back_date.strftime("%Y%m%d")
        context["forward_date"] = forward_date.strftime("%Y%m%d")
        context["mode"] = "all"
        context["form"] = forms.BookinngDialogForm()
        context["equipment"] = Equipment.objects.first()
        return context


class CategoryCalendarView(IsAuthenticaedViewMixin, views.generic.TemplateView):
    """Make a calendar display for an equipment category and date."""

    template_name = "bookings/parts/equipment_calendar_category.html"

    def get_context_data(self, **kwargs):
        """Build the context for the calendar display."""
        context = super().get_context_data(**kwargs)
        # Build the calendar rows from the shifts.
        date = self.kwargs.get("date", int(self.request.GET.get("date", dt.today().strftime("%Y%m%d"))))
        cat = self.kwargs.get("cat", self.request.GET.get("cat", ""))
        equip_vec = (
            Equipment.objects.filter(category=cat)
            .annotate(policy_count=Count("policies"))
            .filter(policy_count__gt=0, offline=False)
            .order_by("name")
        )
        equipment = Equipment.objects.filter(category=cat).first()
        if equip_vec.count() == 0:
            return context
        table = CalTable(
            date=self.kwargs.get("date", date),
            request=self.request,
            equipment=equipment,
            equip_vec=equip_vec,
            table_contents="&nbsp;",
        )
        table.classes += " table-bordered"
        entries = chain(*(table.fill_entries(equipment) for equipment in equip_vec))
        context["cal"] = table
        return context


class BookingDialog(IsAuthenticaedViewMixin, HTMXFormMixin, views.generic.UpdateView):
    """Prdoce the html for a booking form in the dialog."""

    model = models.BookingEntry
    template_name = "bookings/booking_form.html"
    form_class = forms.BookinngDialogForm
    context_object_name = "this"

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the booking dialog."""
        context = super().get_context_data(**kwargs)
        context["current_url"] = self.request.htmx.current_url
        context["ts"] = self.kwargs.get("ts", None)
        context["equipment"] = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
        context["equipment_id"] = self.kwargs.get("equipment", None)
        context["edit"] = self.get_object() is not None
        return context

    def get_object(self, queryset=None):
        """Either get the BookingEntry or None."""
        equipment = self.kwargs.get("equipment")
        start = dt.fromtimestamp(self.kwargs.get("ts"), DEFAULT_TZ)
        end = start + td(seconds=1)
        slot = DateTimeTZRange(lower=start, upper=end)
        try:
            ret = models.BookingEntry.objects.get(equipment__pk=equipment, slot__overlap=slot)
            return ret
        except ObjectDoesNotExist:
            return None

    def get_initial(self):
        """Make initial entry."""
        if (this := self.get_object()) is not None:
            return {
                "equipment": this.equipment,
                "slot": this.slot,
                "user": this.user,
                "booker": this.booker,
                "cost_centre": this.cost_centre,
            }
        equipment = Equipment.objects.get(pk=self.kwargs.get("equipment"))
        start = dt.fromtimestamp(self.kwargs.get("ts"), DEFAULT_TZ)
        if shift := equipment.get_shift(start):
            start = dt.combine(start.date(), shift.start_time)
            end = start + shift.duration
        else:
            end = start + td(hours=3)  # TODO implement shifts
        ret = {"equipment": equipment, "slot": DateTimeTZRange(lower=start, upper=end)}
        if not self.request.user.is_superuser:
            ret["user"] = self.request.user
        ret["booker"] = self.request.user
        return ret

    def htmx_form_valid_booking(self, form):
        """Handle the HTMX submitted booking form if it's all ok."""
        self.object = form.save()
        equipment = self.object.equipment
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps({"refreshSchedule": slugify(equipment.category)}),
            },
        )

    def htmx_delete_booking(self, request, *args, **kwargs):
        """Handle the HTMX call that deletes a booking."""
        pk = self.request.GET.get("booking", None)
        if not pk or not pk.isnumeric():
            return HttpResponseNotFound("No booking primary key found!")

        try:
            booking = models.BookingEntry.objects.get(pk=int(pk))
            self.object = booking
        except models.BookingEntry.DoesNotExist:
            return HttpResponseNotFound("No booking found!")
        equipment = booking.equipment
        force = booking.equipment.can_edit(self.request.user)
        if booking.user != self.request.user:  # Not our booking so make use th Booker
            booking.booker = self.request.user
        try:
            booking.delete(force=force)
        except models.BookingError:
            HttpResponseNotModified("Error allowing delete - no action!")
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps({"refreshSchedule": slugify(equipment.category)}),
            },
        )


class BookingRecordsView(IsAuthenticaedViewMixin, FormListView):
    """Filter the list of records by the form data."""

    form_class = forms.BookingEntryFilterForm
    template_name = "bookings/reporting.html"
    model = models.BookingEntry
    context_object_name = "entries"

    def get(self, request, *args, **kwargs):
        """Handle GET requests and instantiates a blank version of the form before passing to ListView.get."""
        form_class = self.get_form_class()
        if not getattr(self, "form", None):
            self.form = self.get_form(form_class)
            return super().get(request, *args, **kwargs)
        # form is defined, so we're here via POST
        context = self.get_context_data()
        fmt = getattr(self.form, "cleaned_data", {}).get("output", "html").lower()
        match fmt:
            case "csv":
                response = HttpResponse(content_type="text/csv")
                response["Content-Disposition"] = 'attachment; filename="report.csv"'
                self.data.to_csv(response)
            case "xlsx":
                response = HttpResponse(
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                response["Content-Disposition"] = 'attachment; filename="report.xlsx"'
                self.data.to_excel(response)
            case "pdf":
                response = render_to_pdf_response(
                    request, "bookings/reporting_pdf.html", context, filename="report.pdf", encoding="utf-8"
                )
            case "raw":
                response = HttpResponse(
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                response["Content-Disposition"] = 'attachment; filename="records.xlsx"'
                self.df.to_excel(response)
            case _:
                return super().get(request, *args, **kwargs)
        return response

    def get_queryset(self):
        """Get a queryset after we've filtered the data."""
        if not self.form.is_valid():
            return self.model.objects.none()
        data = self.form.cleaned_data
        qs = super().get_queryset()

        start = DEFAULT_TZ.localize(dt.combine(data["from_date"], dt.min.time()))
        end = DEFAULT_TZ.localize(dt.combine(data["to_date"], dt.max.time()))
        qs = qs.filter(slot__overlap=DateTimeTZRange(start, end))

        if data["equipment"]:
            qs = qs.filter(equipment__in=data["equipment"])
        if data["user"]:
            qs = qs.filter(user__in=data["user"])
        if data["cost_centre"]:
            for ix, sqs in enumerate(data["cost_centre"].all()):
                if ix == 0:
                    query = Q(cost_centre__in=sqs.children)
                else:
                    query |= Q(cost_centre__in=sqs.children)
            qs = qs.filter(query)
        return qs

    def map_row(self, row):
        """Data renamer to undo FK ids."""
        row.equipment = str(Equipment.objects.get(pk=row.equipment))
        row.user = str(Account.objects.get(pk=row.user).display_name)
        row.cost_centre = str(CostCentre.objects.get(pk=row.cost_centre).short_name)
        return row

    def get_context_data(self, **kwargs):
        """Call the parent get_context_data before adding the current form as context."""
        context = super().get_context_data(**kwargs)
        entries = context["entries"]
        df = pd.DataFrame(entries.values("user", "cost_centre", "equipment", "shifts", "slot", "charge", "comment"))
        if len(df) == 0:
            return context
        bad = df["slot"]
        df = df.apply(self.map_row, axis=1)
        df["start"] = (df["slot"].apply(lambda x: x.lower)).dt.tz_localize(None)
        df["end"] = (df["slot"].apply(lambda x: x.upper)).dt.tz_localize(None)

        df = df.drop(columns="slot")
        df.rename(columns={x: x.title() for x in df.columns}, inplace=True)
        data = getattr(self.form, "cleaned_data", {})
        groupby = [
            x.title()
            for x in getattr(self.form, "cleaned_data", {}).get("order", "user,equipment,cost_Centre").split(",")
        ]
        if getattr(self.form, "cleaned_data", {}).get("reverse", False):
            groupby.reverse()
        if groupby and len(df):
            data = []
            for ix, _ in enumerate(groupby):
                grp = groupby[:-ix] if ix > 0 else groupby
                data.append(df.groupby(grp)[["Shifts", "Charge"]].sum().reset_index())
            self.data = pd.concat(data, ignore_index=True).sort_values(groupby)
            self.data.replace(np.nan, "Subtotal", inplace=True)
            self.data.set_index(groupby, inplace=True)
        else:
            self.data = df[["User", "Cost_Centre", "Equipment", "Start", "End", "Shifts", "Charge", "Comment"]]
        self.df = df[["User", "Cost_Centre", "Equipment", "Start", "End", "Shifts", "Charge", "Comment"]]
        context["data"] = self.data.to_html(classes="table table-striped table-hover tabel-responsive")
        return context
