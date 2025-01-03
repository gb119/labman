# -*- coding: utf-8 -*-
"""View definitions for the bookings app."""
# Python imports
from datetime import datetime as dt, time as Time, timedelta as td

# Django imports
from django import views
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import (
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseNotModified,
)

# external imports
import pytz
from equipment.models import Equipment
from htmx_views.views import HTMXFormMixin
from labman_utils.views import IsAuthenticaedViewMixin
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
        date = self.kwargs.get("date", int(self.request.GET.get("date", dt.today().strftime("%Y%m%d"))))
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


class BookingDialog(IsAuthenticaedViewMixin, HTMXFormMixin, views.generic.UpdateView):
    """Prdoce the html for a booking form in the dialog."""

    model = models.BookingEntry
    template_name = "bookings/booking_form.html"
    form_class = forms.BookinngDialogForm
    context_object_name = "this"

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the booking dialog."""
        context = super().get_context_data(_context=True, **kwargs)
        context["current_url"] = self.request.htmx.current_url
        context["ts"] = self.kwargs.get("ts", None)
        context["equipment"] = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
        context["equipment_id"] = self.kwargs.get("equipment", None)
        context["edit"] = self.get_object() is not None
        print(context)
        return context

    def get_object(self, queryset=None):
        """Either get the BookingEntry or None."""
        equipment = self.kwargs.get("equipment")
        start = dt.fromtimestamp(self.kwargs.get("ts"), DEFAULT_TZ)
        end = start + td(seconds=1)
        slot = DateTimeTZRange(lower=start, upper=end)
        print(f"Test slot = {slot=}")
        try:
            ret = models.BookingEntry.objects.get(equipment__pk=equipment, slot__overlap=slot)
            print(f"Found slot {ret.slot}")
            return ret
        except ObjectDoesNotExist:
            print("no slot found")
            return None

    def get_initial(self):
        """Make initial entry."""
        if (this := self.get_object()) is not None:
            return {
                "equipment": this.equipment,
                "slot": this.slot,
                "user": this.user,
                "booker": this.booker,
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
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshSchedule",
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
        force = self.request.user.is_superuser
        if booking.user != self.request.user:  # Not our booking so make use th Booker
            booking.booker = self.request.user
        try:
            booking.delete(force=force)
        except models.BookingError:
            HttpResponseNotModified("Error allowing delete - no action!")
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshSchedule",
            },
        )
