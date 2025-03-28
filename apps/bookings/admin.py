# -*- coding: utf-8 -*-
"""Admin interface definition for the bookings app."""
# Django imports
from django.contrib.admin import register

# external imports
from import_export.admin import ImportExportModelAdmin

# app imports
from .forms import BookingEntryAdminForm
from .models import BookingEntry, BookingPolicy
from .resource import BookingEntryResource, BookingPolicyResource


@register(BookingEntry)
class BookingtEntryAdmin(ImportExportModelAdmin):
    """Admin interface definition for BookingEntry objects."""

    list_display = ("user", "equipment", "cost_centre", "shifts", "slot_display", "charge", "comment")
    list_filter = ("user", "equipment", "cost_centre", "shifts")
    list_editable = ["shifts", "charge", "comment"]
    suit_list_filter_horizontal = list_filter
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__username",
        "equipment__name",
        "cost_centre__name",
        "cost_centre__short_name",
        "coist_centre__account_code",
    )
    form = BookingEntryAdminForm

    def get_export_resource_class(self):
        """Return the impor-export resource class."""
        return BookingEntryResource

    def get_import_resource_class(self):
        """Return the impor-export resource class."""
        return BookingEntryResource

    def slot_display(self, obj):
        """Produce a custom display of slot value."""
        start, end = obj.slot.lower, obj.slot.upper
        if start is None or end is None:
            return "Bad slot"
        if start.date() == end.date():  # Simplified for start and end on same day
            return start.strftime("%a %b %d %X") + " - " + end.strftime("%X %Y")
        return start.strftime("%c") + " - " + end.strftime("%c")


@register(BookingPolicy)
class BookingPolicyAdmin(ImportExportModelAdmin):
    """Admin interface definition for BookingPolicy Objects."""

    list_display = (
        ["name", "for_role"] + BookingPolicy.weekdays + ["start_time", "end_time", "immutable", "max_forward"]
    )
    list_filter = list_display
    search_fields = (
        "name",
        "description",
        "for_role__name",
        "for_role__description",
        "equipment__name",
    )

    def get_export_resource_class(self):
        """Return the impor-export resource class."""
        return BookingPolicyResource

    def get_import_resource_class(self):
        """Return the impor-export resource class."""
        return BookingPolicyResource
