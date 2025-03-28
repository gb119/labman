# -*- coding: utf-8 -*-
"""Import Export Resources for bookings."""
# external imports
from accounts.models import Account, Role
from accounts.resource import AccountWidget
from costings.models import CostCentre
from equipment.models import Equipment
from import_export import fields, resources, widgets

# app imports
from .models import BookingEntry, BookingPolicy


class BookingEntryResource(resources.ModelResource):
    """Import export resource for BookingEntry objects."""

    class Meta:
        model = BookingEntry
        import_id_fields = ["id"]

    user = fields.Field(column_name="user", attribute="user", widget=AccountWidget(Account, "username"))
    equipment = fields.Field(
        column_name="equipment", attribute="equipment", widget=widgets.ForeignKeyWidget(Equipment, "name")
    )
    cost_centre = fields.Field(
        column_name="cost_centre", attribute="cost_Centre", widget=widgets.ForeignKeyWidget(CostCentre, "short_name")
    )


class BookingPolicyResource(resources.ModelResource):
    """Import-export resource for BookingPolicy objects."""

    class Meta:
        model = BookingPolicy
        import_id_fields = ["id"]

    for_role = fields.Field(
        column_name="for_role", attribute="for_role", widget=widgets.ForeignKeyWidget(Role, "name")
    )
