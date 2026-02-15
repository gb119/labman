# -*- coding: utf-8 -*-
"""Import export Resources for Equipment App."""
# external imports
from accounts.models import Account, Role
from accounts.resource import AccountWidget
from bookings.models import BookingPolicy
from costings.models import CostRate
from import_export import fields, resources, widgets

# app imports
from .models import (
    ChargingRate,
    Document,
    DocumentSignOff,
    Equipment,
    Location,
    Shift,
    UserListEntry,
)


class ShiftReource(resources.ModelResource):
    """Import-export resource for Location objects."""

    class Meta:
        model = Shift
        import_id_fields = ["name"]


class LocationResource(resources.ModelResource):
    """Import-export resource for Location objects.
    
    Uses name as the primary import/export identifier. The code field is
    maintained for backwards compatibility during migration.
    """

    parent = fields.Field(
        column_name="parent",
        attribute="parent",
        widget=widgets.ForeignKeyWidget(Location, "name"),
    )

    class Meta:
        model = Location
        import_id_fields = ["name"]
        exclude = ["lft", "rght", "tree_id", "level"]  # MPTT fields are auto-managed


class DocumentResource(resources.ModelResource):
    """Import-export resource for Document objects."""

    class Meta:
        model = Document
        import_id_fields = ["title"]


class DocumentSignOffResource(resources.ModelResource):
    """Import-export resource for Sign-off objects."""

    class Meta:
        model = DocumentSignOff
        import_id_fields = ["user", "document", "version"]


class EquipmentResource(resources.ModelResource):
    """Import-export resource for Equipment objects."""

    owner = fields.Field(
        column_name="owner",
        attribute="owner",
        widget=AccountWidget(Account, "username"),
    )

    location = fields.Field(
        column_name="location",
        attribute="location",
        widget=widgets.ForeignKeyWidget(Location, "name"),
    )

    shifts = fields.Field(
        column_name="shifts",
        attribute="shifts",
        widget=widgets.ManyToManyWidget(Shift, ";", "name"),
    )

    policies = fields.Field(
        column_name="policies",
        attribute="policies",
        widget=widgets.ManyToManyWidget(BookingPolicy, ";", "name"),
    )

    class Meta:
        model = Equipment
        import_id_fields = ["name"]


class UserListEntryResource(resources.ModelResource):
    """Import-export resource for UserListEntry objects."""

    user = fields.Field(
        column_name="user",
        attribute="user",
        widget=AccountWidget(Account, "username"),
    )

    equipment = fields.Field(
        column_name="equipment",
        attribute="equipment",
        widget=widgets.ForeignKeyWidget(Equipment, "name"),
    )

    role = fields.Field(
        column_name="role",
        attribute="role",
        widget=widgets.ForeignKeyWidget(Role, "level"),
    )

    class Meta:
        model = UserListEntry


class ChargingRateResource(resources.ModelResource):
    """Resource Class for ChargingRate objects."""

    equipment = fields.Field(
        column_name="equipment",
        attribute="equipment",
        widget=widgets.ForeignKeyWidget(Equipment, "name"),
    )
    cost_rate = fields.Field(
        column_name="cost_rate",
        attribute="cost_rate",
        widget=widgets.ForeignKeyWidget(CostRate, "name"),
    )

    class Meta:
        model = ChargingRate
        import_id_fields = ["equipment", "cost_rate"]
