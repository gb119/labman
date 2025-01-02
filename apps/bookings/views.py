# -*- coding: utf-8 -*-
"""
View definitions for the bookings app.
"""
# Python imports
import json
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
from django.http import (
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseNotModified,
    HttpResponseRedirect,
)
from django.template.response import TemplateResponse
from django.utils.html import format_html

# external imports
import numpy as np
import pytz
from constance import config
from equipment.models import Equipment
from htmx_views.views import HTMXFormMixin
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


def datetime_to_coord(
    target: dt, date_vec: List[Date], time_vec: List[Time], mode: str = "nearest"
) -> Tuple[int, int]:
    """Workout a target datetime's position in time_vec,date_vec."""
    data = np.zeros(len(date_vec) * len(time_vec))
    for idt, date in enumerate(date_vec):
        for itt, time in enumerate(time_vec):
            data[idt * len(time_vec) + itt] = dt.combine(date, time).timestamp()
    target = target.timestamp()
    delta = target - data
    match mode:
        case "round_down":
            delta[delta <= 0] = np.nan
        case "round_up":
            delta[delta >= 0] = np.nan
        case "nearest":
            delta = np.abs(delta)
        case _:
            raise ValueError(f"Uknown find_coords {mode}")
    ix = np.nanargmin(delta)
    col = ix // len(time_vec) + 1
    row = ix % len(time_vec) + 1
    return row, col


class CalTable(Table):
    """Subclass Table to mae something suitable for making a calendar from."""

    def __init__(self, *args, **kargs):
        """Set up time and date vectors."""
        if equip_qs := kargs.pop("equip_qs", None):  # Multiple equipmet mode
            time_vec = []
            eqip_vec = []
            row_label = []
            rows = 1
            for equipment in equip_qs:
                t_vec = equipment.calendar_time_vector
                eqip_vec.extend([equipment] * len(t_vec))
                row_label.extend([3 if len(t_vec) > 1 else 2] * len(t_vec))

                time_vec.extend(t_vec)
            rows += len(time_vec)
            date_vec = calendar_date_vector(yyyymmdd_to_date(kargs.get("date", dt.today().strftime("%Y%m%d"))))
            args = ((rows, 8),)
        elif equipment := kargs.pop("equipment", None):
            time_vec = equipment.calendar_time_vector
            equip_vec = [equipment] * len(time_vec)
            row_label = [1] * len(time_vec)
            date_vec = calendar_date_vector(yyyymmdd_to_date(kargs.get("date", dt.today().strftime("%Y%m%d"))))
            rows = len(time_vec) + 1
            args = ((rows, 8),)
        if len(args) == 0:
            time_vec = kargs.pop("time_vec", [])
            date_vec = kargs.pop("date_vec ", [])
            equip_vec = kargs.pop("equip_vec", [])
            row_label = kargs.pops("row_label", [])
            args = ((len(time_vec) + 1, len(date_vec) + 1),)
        self.date_vec = date_vec
        self.time_vec = time_vec
        self.equip_vec = equip_vec
        self.row_label = row_label
        self.request = kargs.pop("request", None)
        table_content = kargs.pop("table_contents", "&nbsp;")
        if isinstance(table_content, str):
            table_content = np.array([[table_content] * (len(self.date_vec) + 1)] * (len(self.time_vec) + 1))
        kargs["table_contents"] = table_content
        super().__init__(*args, **kargs)
        self.build_table()

    def build_table(self):
        """Build the equipment table."""
        self[0].header = True
        self[:, 0].header = True
        for index_col, date in enumerate(self.date_vec, start=1):
            self[0, index_col].content = date.strftime("%a %d %b")
            self[0, index_col].attrs_dict.update({"style": "width: 13%; text-align: center;"})
            for idx_row, (time, equipment) in enumerate(zip(self.time_vec, self.equip_vec), start=1):
                slot_dt = dt.combine(date, time)
                data_ts = slot_dt.timestamp()
                data_dt = slot_dt.strftime("%Y-%m-%d %I:%M %p")
                self[idx_row, index_col].attrs_dict["data_ts"] = data_ts
                self[idx_row, index_col].attrs_dict["data_dt"] = data_dt
                self[idx_row, index_col].attrs_dict.update(
                    {
                        "hx-get": f"/bookings/book/{equipment.pk}/{data_ts}/",
                    }
                )

        for idx_row, (time, label, equipment) in enumerate(
            zip(self.time_vec, self.row_label, self.equip_vec), start=1
        ):
            match label:
                case 1:
                    self[idx_row, 0].content = time.strftime("%I:%M %p")
                case 2:
                    self[idx_row, 0].content = equipment.name
                case 3:
                    label = f"{time.strftime("%I:%M %p")}<br/>{equipment.name}"
                    self[idx_row, 0].content = format_html(label)

        self.classes += " col-md-10"

    def fill_entries(self, equipment):
        """Fill in the entries for this item of equipment."""
        # Locate the bit of the table relevant to this equipment
        for ix, equip in enumerate(self.equip_vec):
            if equip.pk == equipment.pk:
                break
        else:
            raise ValueError("Oops")
        for iy, equip in enumerate(self.equip_vec[ix:]):
            if equip.pk != equipment.pk:
                break
        else:
            iy += 1
        iy += ix
        time_vec = self.time_vec[ix:iy]
        date_vec = self.date_vec
        row_base = ix
        target_range = DateTimeTZRange(
            dt.combine(date_vec[0], time_vec[0], tzinfo=DEFAULT_TZ),
            dt.combine(date_vec[-1], time_vec[-1], tzinfo=DEFAULT_TZ),
        )
        entries = equipment.bookings.filter(slot__overlap=target_range)
        for entry in entries:
            row_start, col_start = datetime_to_coord(entry.slot.lower, date_vec, time_vec)
            row_end, col_end = datetime_to_coord(entry.slot.upper, date_vec, time_vec, mode="round_down")
            row_start += row_base
            row_end += row_base
            if col_end < 0:  # Finished before first slot
                continue
            if col_start == col_end:  # single day
                self[row_start, col_start].rowspan = max(row_end - row_start, 1)
                self[row_start, col_start].content = entry.user.display_name
                self[row_start, col_start].classes += " bg-success p-3 text-center"
            else:  # spans day boundaries
                self[row_start, col_start].rowspan = len(time_vec) - row_start + 1
                self[row_start, col_start].content = entry.user.display_name
                self[row_start, col_start].classes += " bg-success p-3 text-center"
                for col in range(col_start + 1, col_end):
                    self[1, col].rowspan = len(time_vec)
                    self[1, col].content = entry.user.display_name
                    self[1, col].classes += " bg-success p-3 text-center"
                self[1, col_end].rowspan = max(1, row_end)
                self[1, col_end].content = entry.user.display_name
                self[1, col_end].classes += " bg-success p-3 text-center"
        return entries


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
        context["form"] = forms.BookinngDialogForm()

        return context


class BookingDialog(IsAuthenticaedViewMixin, HTMXFormMixin, views.generic.UpdateView):
    """Prdoce the html for a booking form in the dialog."""

    model = models.BookingEntry
    template_name = "bookings/booking_form.html"
    form_class = forms.BookinngDialogForm
    context_object_name = "this"

    def get_context_data_dialog(self, **kwargs):
        context = super().get_context_data(_context=True, **kwargs)
        context["current_url"] = self.request.htmx.current_url
        context["ts"] = self.kwargs.get("ts", None)
        context["equipment"] = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
        context["equipment_id"] = self.kwargs.get("equipment", None)
        context["edit"] = self.get_object() is not None
        print(context)
        return context

    def form_invalid(self, form):
        err = form.errors
        return super().form_invalid(form)

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
        self.object = form.save()
        context = self.get_context_data()
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshSchedule",
            },
        )

    def htmx_delete_booking(self, request, *args, **kwargs):
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
        except models.BookingError as e:
            HttpResponseNotModified("Error allowing delete - no action!")
        context = self.get_context_data()
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": "refreshSchedule",
            },
        )

    # def get_success_url(self):
    #     """Work out the booking calendar we came from."""
    #     equipment = self.kwargs.get("equipment")
    #     start = dt.fromtimestamp(self.kwargs.get("ts"), DEFAULT_TZ).date().strftime("%Y%m%d")

    #     return f"/bookings/cal/{equipment}/{start}/"
