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
    """Import-export resource for Location objects.

    Examples:
        Inspect the public interface in an interactive session::

            >>> ShiftReource.__name__
            'ShiftReource'
    """

    class Meta:
        """Configure the Meta class."""

        model = Shift
        import_id_fields = ["name"]


class LocationResource(resources.ModelResource):
    """Import-export resource for Location objects.

            Uses name as the primary import/export identifier. The code field is
            maintained for backwards compatibility during migration.


    Examples:
        Inspect the public interface in an interactive session::

            >>> LocationResource.__name__
            'LocationResource'
    """

    parent = fields.Field(
        column_name="parent",
        attribute="parent",
        widget=widgets.ForeignKeyWidget(Location, "name"),
    )

    class Meta:
        """Configure the Meta class."""

        model = Location
        import_id_fields = ["name"]
        # Exclude MPTT fields - they are auto-managed by django-mptt
        # Note: 'rght' is the correct field name (abbreviation of 'right')
        exclude = ["lft", "rght", "tree_id", "level"]


class DocumentResource(resources.ModelResource):
    """Import-export resource for Document objects.

    Examples:
        Inspect the public interface in an interactive session::

            >>> DocumentResource.__name__
            'DocumentResource'
    """

    class Meta:
        """Configure the Meta class."""

        model = Document
        import_id_fields = ["title"]


class DocumentSignOffResource(resources.ModelResource):
    """Import-export resource for Sign-off objects.

    Examples:
        Inspect the public interface in an interactive session::

            >>> DocumentSignOffResource.__name__
            'DocumentSignOffResource'
    """

    class Meta:
        """Configure the Meta class."""

        model = DocumentSignOff
        import_id_fields = ["user", "document", "version"]


class EquipmentResource(resources.ModelResource):
    """Import-export resource for Equipment objects.

    Examples:
        Inspect the public interface in an interactive session::

            >>> EquipmentResource.__name__
            'EquipmentResource'
    """

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
        """Configure the Meta class."""

        model = Equipment
        import_id_fields = ["name"]


class UserListEntryResource(resources.ModelResource):
    """Import-export resource for UserListEntry objects.

    Examples:
        Inspect the public interface in an interactive session::

            >>> UserListEntryResource.__name__
            'UserListEntryResource'
    """

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
        """Configure the Meta class."""

        model = UserListEntry


class ChargingRateResource(resources.ModelResource):
    """Resource Class for ChargingRate objects.

    Examples:
        Inspect the public interface in an interactive session::

            >>> ChargingRateResource.__name__
            'ChargingRateResource'
    """

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
        """Configure the Meta class."""

        model = ChargingRate
        import_id_fields = ["equipment", "cost_rate"]
