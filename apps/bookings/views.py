# -*- coding: utf-8 -*-
"""
View definitions for the bookings app.
"""
# Python imports
from datetime import (
    date as Date,
    datetime as dt,
    time as Time,
    timedelta as td,
)
from typing import List, Tuple, Union

# Django imports
from django import views
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect

# external imports
import numpy as np
import pytz
from constance import config
from equipment.models import Equipment
from labman_utils.views import IsAuthenticaedViewMixin
from psycopg2.extras import DateTimeTZRange
from simple_html_table import Table

# app imports
from . import forms, models

DEFAULT_TZ = pytz.timezone(settings.TIME_ZONE)


def yyyymmdd_to_date(value: int) -> Date:
    """Convert a datestampt to a datetime.Date"""
    value = str(value).strip()
    return DEFAULT_TZ.localize(dt.strptime(value, "%Y%m%d")).date()


def calendar_date_vector(date: Union[Date, dt]) -> List[Date]:
    """Get the dates for a weekly calendar that includes date."""
    start_day = config.CALENDAR_START_DAY
    if isinstance(date, Date):
        date = dt.combine(date, Time(), tzinfo=DEFAULT_TZ)
    dow = date.weekday()
    date -= td(days=(dow - start_day) % 7)
    return [(date + td(days=ix)).date() for ix in range(7)]


def calendar_time_vector() -> List[Time]:
    """Return an array of times with which to construct a calendar."""
    start = config.CALENDAR_START_TIME
    end = config.CALENDAR_END_TIME
    start = dt.combine(Date(1, 1, 1), start, tzinfo=DEFAULT_TZ)
    end = dt.combine(Date(1, 1, 1), end, tzinfo=DEFAULT_TZ)
    ret = [start.time()]
    while (start := start + td(hours=1)) < end:
        ret.append(start.time())
    return ret


def delta_time(time_1: Time, time_2: Time) -> int:
    """Return the number of seconds betweetn time_1 and time_2."""
    dtime_1 = dt.combine(dt.today(), time_1, tzinfo=DEFAULT_TZ)
    dtime_2 = dt.combine(dt.today(), time_2, tzinfo=DEFAULT_TZ)
    dtt = dtime_2 - dtime_1
    return dtt.total_seconds()


def datetime_to_coord(target: dt, date_vec: List[Date], time_vec: List[Time]) -> Tuple[int, int]:
    """Workout a target datetime's position in time_vec,date_vec."""
    try:
        target_date = dt.combine(target.date(), Time(), tzinfo=DEFAULT_TZ).date()
        col = date_vec.index(target_date) + 1
    except ValueError:
        assert False
        col = None
    if target.tzinfo is None:
        target = DEFAULT_TZ.localize(target)
    if target.tzinfo != DEFAULT_TZ:
        target = target.astimezone(DEFAULT_TZ)
    target = target.time()
    ts_vec = sorted([(abs(delta_time(target, tt)), ix) for ix, tt in enumerate(time_vec, start=1)])
    row = ts_vec[0][1]
    print(f"{target=}\n{ts_vec=}")
    return row, col


class CalTable(Table):
    """Subclass Table to mae something suitable for making a calendar from."""

    def __init__(self, *args, date_vec=None, time_vec=None, **kargs):
        """Set up time and date vectors."""
        if len(args) == 0:
            args = ((len(time_vec) + 1, len(date_vec) + 1),)
        time_vec = time_vec if time_vec is not None else []
        date_vec = date_vec if date_vec is not None else []
        super().__init__(*args, **kargs)
        self.date_vec = date_vec
        self.time_vec = time_vec
        self[0].header = True
        self[:, 0].header = True
        for index_row, date in enumerate(date_vec, start=1):
            self[0, index_row].content = date.strftime("%a %d %b")
            self[0, index_row].attrs_dict.update({"style": "width: 13%; text-align: center;"})
            for index_col, time in enumerate(time_vec, start=1):
                slot_dt = dt.combine(date, time)
                self[index_col, index_row].attrs_dict["data_ts"] = slot_dt.timestamp()
                self[index_col, index_row].attrs_dict["data_dt"] = slot_dt.strftime("%Y-%m-%d %I:%M %p")
        for index_col, time in enumerate(time_vec, start=1):
            self[index_col, 0].content = time.strftime("%I:%M %p")
        self.classes += " col-md-10"


class CalendarView(IsAuthenticaedViewMixin, views.generic.DetailView):
    """Make a calendar display for an equipment item and date."""

    template_name = "bookings/equipment_calendar.hhtml"
    model = Equipment
    slug_url_kwarg = "equipment"
    slug_field = "pk"
    context_object_name = "this"

    def get_context_data(self, **kwargs):
        """Build the context for the calendar display."""
        context = super().get_context_data(**kwargs)
        date_vec = calendar_date_vector(yyyymmdd_to_date(self.kwargs["date"]))
        time_vec = calendar_time_vector()
        table = CalTable(
            date_vec=date_vec,
            time_vec=time_vec,
            table_contents=np.array([["&nbsp;"] * (len(date_vec) + 1)] * (len(time_vec) + 1)),
        )
        table.classes += " table-bordered"
        target_range = DateTimeTZRange(
            dt.combine(date_vec[0], time_vec[0], tzinfo=DEFAULT_TZ),
            dt.combine(date_vec[-1], time_vec[-1], tzinfo=DEFAULT_TZ),
        )
        eqipment = context["this"]
        for entry in eqipment.bookings.filter(slot__overlap=target_range):
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
        context["entries"] = eqipment.bookings.filter(slot__overlap=target_range)
        context["form"] = forms.BookinngDialogForm()

        return context


class BookingDelete(IsAuthenticaedViewMixin, views.generic.DetailView):
    """Handles deleting a single booking entry by the booking id."""

    model = models.BookingEntry
    template_name = "bookings/booking_form.html"
    slug_field = "pk"
    slug_url_kwarg = "pk"
    context_object_name = "this"

    def render_to_response(self, context, **response_kwargs):
        """Delete the booking entry and redirect to the calendar view."""
        this = context.get("this")
        start = this.slot.lower.strftime("%Y%m%d")
        equip = this.equipment

        this.delete()
        return HttpResponseRedirect(f"/bookings/cal/{equip.pk}/{start}/")


class BookingDialog(IsAuthenticaedViewMixin, views.generic.UpdateView):
    """Prdoce the html for a booking form in the dialog."""

    model = models.BookingEntry
    template_name = "bookings/booking_form.html"
    form_class = forms.BookinngDialogForm
    context_object_name = "this"

    def get_object(self, queryset=None):
        """Either get the BookingEntry or None."""
        equipment = self.kwargs.get("equipment")
        start = dt.fromtimestamp(self.kwargs.get("ts"), DEFAULT_TZ)
        end = start + td(seconds=1)
        slot = DateTimeTZRange(lower=start, upper=end)
        print(f"{slot=}")
        try:
            ret = models.BookingEntry.objects.get(equipment__pk=equipment, slot__overlap=slot)
            print(f"Found slot {ret.slot}")
            return ret
        except ObjectDoesNotExist:
            print("no slot")
            return None

    def get_initial(self):
        """Make initial entry."""
        if this := self.get_object():
            return {"equipment": this.equipment, "slot": this.slot, "user": this.user, "booker": this.booker}
        equipment = Equipment.objects.get(pk=self.kwargs.get("equipment"))
        start = dt.fromtimestamp(self.kwargs.get("ts"), DEFAULT_TZ)
        end = start + td(hours=3)  # TODO implement shifts
        ret = {"equipment": equipment, "slot": DateTimeTZRange(lower=start, upper=end)}
        if not self.request.user.is_superuser:
            ret["user"] = self.request.user
        else:
            ret["booker"] = self.request.user
        return ret

    def get_success_url(self):
        """Work out the booking calendar we came from."""
        equipment = self.kwargs.get("equipment")
        start = dt.fromtimestamp(self.kwargs.get("ts"), DEFAULT_TZ).date().strftime("%Y%m%d")

        return f"/bookings/cal/{equipment}/{start}/"
