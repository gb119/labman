# -*- coding: utf-8 -*-
"""Table classes for LabMAN."""
# Python imports
from datetime import (
    date as Date,
    datetime as dt,
    time as Time,
    timedelta as td,
)
from typing import List, Tuple, Union

# Django imports
from django.conf import settings
from django.utils.html import format_html

# external imports
import numpy as np
import pytz
from constance import config
from psycopg2.extras import DateTimeTZRange
from simple_html_table import Table

DEFAULT_TZ = pytz.timezone(settings.TIME_ZONE)


def calendar_date_vector(date: Union[Date, dt]) -> List[Date]:
    """Get the dates for a weekly calendar that includes date."""
    start_day = int(config.CALENDAR_START_DAY)
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


def yyyymmdd_to_date(value: int) -> Date:
    """Convert a datestampt to a datetime.Date."""
    value = str(value).strip()
    return DEFAULT_TZ.localize(dt.strptime(value, "%Y%m%d")).date()


def datetime_to_coord(
    target: dt, date_vec: List[Date], time_vec: List[Time], mode: str = "nearest"
) -> Tuple[int, int]:
    """Workout a target datetime's position in time_vec,date_vec."""
    data = np.zeros(len(date_vec) * len(time_vec))
    for idt, date in enumerate(date_vec):
        for itt, time in enumerate(time_vec):
            data[idt * len(time_vec) + itt] = dt.combine(date, time).timestamp()
    target = target.timestamp()
    delta = data - target
    match mode:
        case "start":  # Looking for a ts that is == or < target
            delta[delta > 0] = np.nan
            try:
                ix = np.nanargmax(delta)
            except ValueError:
                ix = 0
        case "end":  # looking for a ts that is == to > target and then back of 1 on the ix
            delta[delta < 0] = np.nan
            try:
                ix = np.nanargmin(delta) - 1
            except ValueError:
                ix = len(delta) - 1
        case "nearest":  # Looking for the ts that is closest in any direction.
            delta = np.abs(delta)
            ix = np.nanargmin(delta)
        case _:
            raise ValueError(f"Uknown find_coords {mode}")
    col = ix // len(time_vec) + 1
    row = ix % len(time_vec) + 1
    return row, col


class CalTable(Table):
    """Subclass Table to mae something suitable for making a calendar from."""

    def __init__(self, *args, **kargs):
        """Set up time and date vectors."""
        if equip_qs := kargs.pop("equip_vec", None):  # Multiple equipmet mode
            time_vec = []
            equip_vec = []
            row_label = []
            rows = 1
            for equipment in equip_qs:
                t_vec = equipment.calendar_time_vector
                equip_vec.extend([equipment] * len(t_vec))
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
            row_label = kargs.pop("row_label", [])
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
            self[0, index_col].classes_list.append("table-dark")
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
                        "hx-target": "#dialog",
                        "hx-swap": "innerHTML",
                    }
                )
                if index_col in [1, 2]:
                    self[idx_row, index_col].classes += " table-secondary"

        for idx_row, (time, label, equipment) in enumerate(
            zip(self.time_vec, self.row_label, self.equip_vec), start=1
        ):
            match label:
                case 1:
                    self[idx_row, 0].content = time.strftime("%I:%M %p")
                case 2:
                    self[idx_row, 0].content = f"<a href='{equipment.url}'>{equipment.name}</a>"
                case 3:
                    label = (
                        f"<a href='{equipment.url}'>{equipment.name}</a><br/>"
                        + f"<span style='font-size:smaller;'>{time.strftime("%I:%M %p")}</span>"
                    )
                    self[idx_row, 0].content = format_html(label)
            self[idx_row, 0].classes += " table-dark"

        self.classes += " table col-md-10 table-hover"

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
            row_start, col_start = datetime_to_coord(entry.slot.lower, date_vec, time_vec, mode="start")
            row_end, col_end = datetime_to_coord(entry.slot.upper, date_vec, time_vec, mode="end")
            row_start += row_base
            row_end += row_base
            if col_end < 0:  # Finished before first slot
                continue
            if col_start == col_end:  # single day
                if max(row_end - row_start + 1, 1) > 1:
                    self[row_start, col_start].rowspan = max(row_end - row_start + 1, 1)
                self[row_start, col_start].content = entry.user.display_name
                self[row_start, col_start].classes += f" {entry.calendar_css}"
            else:  # spans day boundaries
                if len(time_vec) - row_start + 1 > 1:
                    self[row_start, col_start].rowspan = len(time_vec) - row_start + 1
                self[row_start, col_start].content = entry.user.display_name
                self[row_start, col_start].classes += f" {entry.calendar_css}"
                for col in range(col_start + 1, col_end):
                    if len(time_vec) > 1:
                        self[1 + row_base, col].rowspan = len(time_vec)
                    self[1 + row_base, col].content = entry.user.display_name
                    self[1 + row_base, col].classes += f" {entry.calendar_css}"
                if max(1, row_end - row_base) > 1:
                    self[1 + row_base, col_end].rowspan = max(1, row_end - row_base)
                self[1 + row_base, col_end].content = entry.user.display_name
                self[1 + row_base, col_end].classes += f" {entry.calendar_css}"
        return entries
