# -*- coding: utf-8 -*-
"""
Admin interface definition for the bookings app
"""
# Python imports
import re

# Django imports
from django.contrib.admin import register
from django.core.exceptions import ObjectDoesNotExist

# external imports
from accounts.models import Account as User, Project, Role
from equipment.models import Equipment
from import_export import fields, resources, widgets
from import_export.admin import ImportExportModelAdmin

# app imports
from .forms import BookingEntryAdminForm
from .models import BookingEntry, BookingPolicy


class UsernameFKWidget(widgets.ForeignKeyWidget):
    "Hacked to allow a pre-process callback in clean." ""

    name_pat = re.compile(r"\((.*)\)")

    def __init__(self, *args, **kargs):
        """Add a hook for a function to process each element on import."""
        self.process = kargs.pop("process", self.name2username)
        super().__init__(*args, **kargs)

    def clean(self, value, *args, row=None, **kwargs):
        val = self.name2username(value)
        if val is None:
            return None
        try:
            return User.objects.get(username=val)
        except ObjectDoesNotExist:
            assert False, f"->{val}={value}<-"

    def name2username(self, name):
        """Tries various ways to get a valid username.

        1) Look for some () and assume that contains a username
        2) Look for a comma and assume that that divides first name from last name
        3) Look for words and if more than 1 word, assume that it is first anem last name
        4) If only 1 word, assume it is a user id.
        """
        if not isinstance(name, str) or name in ["", "None"]:
            return None
        match = self.name_pat.search(name)
        if match:
            return match.group(1).lower()
        if "," in name:
            parts = name.split(",")
            firstname = parts[1].strip()
            surname = parts[0].strip()
        else:
            parts = [x for x in name.split(" ") if x != ""]
            if len(parts) < 2:
                return str.lower(name)
            if parts[0] in ["Mr", "Mrs", "Dr", "Prof", "Miss", "Ms"]:
                parts = parts[1:]
            firstname = parts[0]
            surname = parts[-1]
        possible = User.objects.filter(first_name=firstname, last_name__contains=surname)
        if possible.count() >= 1:
            return possible.all()[0].username
        return name

    def render(self, value, obj=None):
        if value is None:
            return ""
        return getattr(value, "display_name", "")


def name2username(name):
    """Tries various ways to get a valid username.

    1) Look for some () and assume that contains a username
    2) Look for a comma and assume that that divides first name from last name
    3) Look for words and if more than 1 word, assume that it is first anem last name
    4) If only 1 word, assume it is a user id.
    """
    if not isinstance(name, str) or name in ["", "None"]:
        return None
    name_pat = re.compile(r"\((.*)\)")
    match = name_pat.search(name)
    if match:
        return match.group(1).lower()
    if "," in name:
        parts = name.split(",")
        firstname = parts[1].strip()
        surname = parts[0].strip()
    else:
        parts = [x for x in name.split(" ") if x != ""]
        if len(parts) < 2:
            return str.lower(name)
        if parts[0] in ["Mr", "Mrs", "Dr", "Prof", "Miss", "Ms"]:
            parts = parts[1:]
        firstname = parts[0]
        surname = parts[-1]
    possible = User.objects.filter(first_name=firstname, last_name__contains=surname)
    if possible.count() >= 1:
        return possible.all()[0].username
    return name


class BookingEntryResource(resources.ModelResource):
    """Import export resource for BookingEntry objects."""

    class Meta:
        model = BookingEntry
        import_id_fields = ["id"]

    user = fields.Field(column_name="user", attribute="user", widget=UsernameFKWidget(User, "username"))
    equipment = fields.Field(
        column_name="equipment", attribute="equipment", widget=widgets.ForeignKeyWidget(Equipment, "name")
    )
    project = fields.Field(
        column_name="project", attribute="project", widget=widgets.ForeignKeyWidget(Project, "short_name")
    )


class BookingPolicyResource(resources.ModelResource):
    """Import-export resource for BookingPolicy objects."""

    class Meta:
        model = BookingPolicy
        import_id_fields = ["id"]

    for_role = fields.Field(
        column_name="for_role", attribute="for_role", widget=widgets.ForeignKeyWidget(Role, "name")
    )


@register(BookingEntry)
class BookingtEntryAdmin(ImportExportModelAdmin):
    """Admin interface definition for BookingEntry objects."""

    list_display = ("user", "equipment", "project", "shifts", "slot_display")
    list_filter = ("user", "equipment", "project", "shifts")
    suit_list_filter_horizontal = list_filter
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__username",
        "equipment__name",
        "project__name",
        "project__short_name",
        "project__code",
    )
    form = BookingEntryAdminForm

    def get_export_resource_class(self):
        """Return the impor-export resource class."""
        return BookingEntryResource

    def get_import_resource_class(self):
        """Return the impor-export resource class."""
        return BookingEntryResource

    def slot_display(self, obj):
        """Custom display of slot value."""
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
