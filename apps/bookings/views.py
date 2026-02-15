# -*- coding: utf-8 -*-
"""View definitions for the bookings app.

This module provides Django class-based views for managing equipment bookings,
including calendar displays, booking creation/editing dialogs, and comprehensive
reporting functionality. It handles both single equipment and multi-equipment
booking views with HTMX support.
"""
# Python imports
import io
import json
from datetime import datetime as dt, time as Time, timedelta as td
from functools import reduce
from itertools import chain
import operator

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

# Constants for handling missing/orphaned foreign key references
UNKNOWN_EQUIPMENT = "[Unknown Equipment]"
UNKNOWN_USER = "[Unknown User]"
UNKNOWN_COST_CENTRE = "[Unknown Cost Centre]"


def delta_time(time_1: Time, time_2: Time) -> int:
    """Return the number of seconds between time_1 and time_2.

    Converts time objects to datetime objects on today's date and calculates
    the difference in seconds. If datetime objects are provided, uses them directly.

    Args:
        time_1 (Time or datetime): The first time point.
        time_2 (Time or datetime): The second time point.

    Returns:
        (int): The number of seconds between the two times.
    """
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
    """Calendar display view for a single equipment item.

    Displays a weekly calendar view for booking a specific equipment item,
    showing existing bookings and allowing users to create new bookings.

    Attributes:
        template_name (str): Template for the calendar display.
        model: Equipment model class.
        slug_url_kwarg (str): URL keyword argument for equipment lookup.
        slug_field (str): Model field for equipment lookup.
        context_object_name (str): Name for equipment object in context.
    """

    template_name = "bookings/equipment_calendar.html"
    model = Equipment
    slug_url_kwarg = "equipment"
    slug_field = "pk"
    context_object_name = "equipment"

    def get_context_data(self, **kwargs):
        """Build the context for the calendar display.

        Sets up date range for weekly calendar view with navigation dates.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary containing start_date, back_date, forward_date,
                mode, and booking form.
        """
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
    """Calendar display view for all equipment items.

    Displays a consolidated calendar view showing bookings across all equipment
    items, grouped by category, for a given date range.

    Attributes:
        template_name (str): Template for the all-equipment calendar display.
    """

    template_name = "bookings/equipment_all_calendar.html"

    def get_context_data(self, **kwargs):
        """Build the context for the all-equipment calendar display.

        Sets up date range for weekly calendar view with navigation dates.
        Handles multiple date formats for flexibility.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary containing start_date, back_date, forward_date,
                mode, booking form, and first equipment object.
        """
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
    """Calendar display view for equipment within a specific category.

    Displays a calendar view filtered to show only equipment within a specified
    category, useful for viewing related equipment bookings together.

    Attributes:
        template_name (str): Template for category-specific calendar display.
    """

    template_name = "bookings/parts/equipment_calendar_category.html"

    def get_context_data(self, **kwargs):
        """Build the context for the category calendar display.

        Creates a calendar table for all equipment in the specified category
        that has booking policies and is not offline.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary containing calendar table for the category.
        """
        context = super().get_context_data(**kwargs)
        # Build the calendar rows from the shifts.
        date = self.kwargs.get("date", int(self.request.GET.get("date", dt.today().strftime("%Y%m%d"))))
        cat = self.kwargs.get("cat", self.request.GET.get("cat", ""))
        equip_vec = (
            Equipment.objects.filter(category=cat)
            .annotate(policy_count=Count("policies"))
            .filter(policy_count__gt=0, offline=False)
            .prefetch_related("shifts")
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
    """HTMX dialog for creating and editing booking entries.

    Provides an HTMX-powered dialog interface for booking equipment. Supports
    both creating new bookings and editing existing ones with appropriate
    permission checks.

    Attributes:
        model: BookingEntry model class.
        template_name (str): Template for the booking form dialog.
        form_class: Form class for booking entries.
        context_object_name (str): Name for the booking object in context.
    """

    model = models.BookingEntry
    template_name = "bookings/booking_form.html"
    form_class = forms.BookinngDialogForm
    context_object_name = "this"

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the booking dialog.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary containing current URL, timestamp, equipment,
                equipment ID, and edit flag.
        """
        context = super().get_context_data(**kwargs)
        context["current_url"] = self.request.htmx.current_url
        context["ts"] = self.kwargs.get("ts", None)
        context["equipment"] = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
        context["equipment_id"] = self.kwargs.get("equipment", None)
        context["edit"] = self.get_object() is not None
        return context

    def get_object(self, queryset=None):
        """Get the BookingEntry for the specified equipment and time slot.

        Searches for an existing booking that overlaps with the specified timestamp.

        Keyword Parameters:
            queryset (QuerySet or None): Optional queryset to use for lookup.

        Returns:
            (BookingEntry or None): The booking entry if found, otherwise None.
        """
        equipment = self.kwargs.get("equipment")
        start = dt.fromtimestamp(self.kwargs.get("ts"), DEFAULT_TZ)
        end = start + td(seconds=1)
        slot = DateTimeTZRange(lower=start, upper=end)
        try:
            ret = models.BookingEntry.objects.select_related("equipment").get(
                equipment__pk=equipment, slot__overlap=slot
            )
            return ret
        except ObjectDoesNotExist:
            return None

    def get_initial(self):
        """Make initial entry.

        Creates initial form data for a new booking or populates data from an
        existing booking. Automatically sets time slot based on equipment shifts
        or defaults to 3 hours. Non-superusers are set as both user and booker.

        Returns:
            (dict): Initial form data containing equipment, slot, user, booker,
                and cost_centre.
        """
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
        """Handle the HTMX submitted booking form if valid.

        Saves the booking entry and triggers a schedule refresh.

        Args:
            form: The validated form containing booking data.

        Returns:
            (HttpResponse): Empty response with HTMX trigger to refresh schedule.
        """
        self.object = form.save()
        equipment = self.object.equipment
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps({"refreshSchedule": slugify(equipment.category)}),
            },
        )

    def htmx_delete_booking(self, request, *args, **kwargs):
        """Handle the HTMX call that deletes a booking.

        Deletes a booking entry with appropriate permission checks. Users can delete
        their own bookings, while equipment managers can force delete any booking.

        Args:
            request: The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            (HttpResponse): Empty response with HTMX trigger to refresh schedule.

        Raises:
            HttpResponseNotFound: If the booking cannot be found or no valid ID provided.
            HttpResponseNotModified: If deletion is not allowed.
        """
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
    """View for filtering and reporting on booking records.

    Provides a comprehensive reporting interface for booking records with filtering
    by date, equipment, user, and cost centre. Supports multiple output formats
    including HTML, CSV, Excel, and PDF.

    Attributes:
        form_class: Form class for filtering booking records.
        template_name (str): Template for the reporting view.
        model: BookingEntry model class.
        context_object_name (str): Name for entries list in context.
    """

    form_class = forms.BookingEntryFilterForm
    template_name = "bookings/reporting.html"
    model = models.BookingEntry
    context_object_name = "entries"

    def get(self, request, *args, **kwargs):
        """Handle GET requests and instantiate form before passing to ListView.get.

        Handles both initial page load and export requests. Export format is determined
        by the form's output field and can be CSV, Excel, PDF, or raw data.

        Args:
            request: The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            (HttpResponse): Either the rendered template or a file download response.
        """
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
        """Get a queryset after filtering the data.

        Applies filters from the validated form including date range, equipment,
        user, user_group, and cost centre filters.

        Returns:
            (QuerySet): Filtered queryset of booking entries.
        """
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
        if data.get("user_group"):
            qs = qs.filter(user__groups__in=data["user_group"]).distinct()
        if data["cost_centre"]:
            # Build Q objects using MPTT tree fields for efficient filtering
            cost_centre_queries = []
            for sqs in data["cost_centre"].all():
                # Use MPTT indexed fields to find all descendants (including self)
                # A node is a descendant if: tree_id matches AND lft is between parent's lft and rght
                cost_centre_queries.append(
                    Q(
                        cost_centre__tree_id=sqs.tree_id,
                        cost_centre__lft__gte=sqs.lft,
                        cost_centre__lft__lte=sqs.rght,
                    )
                )
            
            # Combine with OR
            if cost_centre_queries:
                qs = qs.filter(reduce(operator.or_, cost_centre_queries))
        return qs

    def get_context_data(self, **kwargs):
        """Build context data including processed booking records.

        Converts booking entries to a pandas DataFrame, applies data transformations,
        and creates aggregated summaries based on grouping parameters. Stores both
        aggregated and raw data for export purposes.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary with entries, processed data, and form.
        """
        context = super().get_context_data(**kwargs)
        entries = context["entries"]
        df = pd.DataFrame(entries.values("user", "cost_centre", "equipment", "shifts", "slot", "charge", "comment"))
        if len(df) == 0:
            self.df = df
            return context
        bad = df["slot"]

        # Bulk load all related objects to avoid N+1 queries
        equipment_ids = df["equipment"].unique()
        user_ids = df["user"].unique()
        cost_centre_ids = df["cost_centre"].unique()

        equipment_map = {e.pk: str(e) for e in Equipment.objects.filter(pk__in=equipment_ids)}
        user_map = {u.pk: str(u.display_name) for u in Account.objects.filter(pk__in=user_ids)}
        cost_centre_map = {cc.pk: str(cc.short_name) for cc in CostCentre.objects.filter(pk__in=cost_centre_ids)}
        
        # Build user group map - get group names for each user or "No Group"
        user_group_map = {}
        for user in Account.objects.filter(pk__in=user_ids).prefetch_related("groups"):
            groups = user.groups.all()
            if groups:
                user_group_map[user.pk] = ", ".join([g.name for g in groups])
            else:
                user_group_map[user.pk] = "No Group"

        # Map foreign keys to strings using dictionary lookups
        # fillna handles any orphaned foreign keys gracefully
        df["user_group"] = df["user"].map(user_group_map).fillna("No Group")
        df["equipment"] = df["equipment"].map(equipment_map).fillna(UNKNOWN_EQUIPMENT)
        df["user"] = df["user"].map(user_map).fillna(UNKNOWN_USER)
        df["cost_centre"] = df["cost_centre"].map(cost_centre_map).fillna(UNKNOWN_COST_CENTRE)
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
                # Build aggregation dictionary
                agg_dict = {"Shifts": "sum", "Charge": "sum"}
                # Include User_Group when User is in groupby but User_Group is not
                # We can use 'first' because when grouping by User, each group has only
                # one user and thus one consistent User_Group value (which may contain
                # multiple group names as a comma-separated string)
                if "User" in grp and "User_Group" not in grp and "User_Group" in df.columns:
                    agg_dict["User_Group"] = "first"
                grouped = df.groupby(grp).agg(agg_dict).reset_index()
                data.append(grouped)
            self.data = pd.concat(data, ignore_index=True).sort_values(groupby)
            self.data.replace(np.nan, "Subtotal", inplace=True)
            self.data.set_index(groupby, inplace=True)
        else:
            self.data = df[["User", "User_Group", "Cost_Centre", "Equipment", "Start", "End", "Shifts", "Charge", "Comment"]]
        self.df = df[["User", "User_Group", "Cost_Centre", "Equipment", "Start", "End", "Shifts", "Charge", "Comment"]]
        context["data"] = self.data.to_html(classes="table table-striped table-hover tabel-responsive")
        return context
