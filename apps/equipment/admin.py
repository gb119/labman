# -*- coding: utf-8 -*-
"""Django admin interface configurations for laboratory equipment management.

This module provides comprehensive admin interfaces for managing laboratory
equipment, locations, user lists, documents, sign-offs, shifts, and charging rates.
It includes custom filters, inline administrators, and import/export functionality
to support equipment booking and resource management workflows.
"""
# Django imports
from django.contrib.admin import (
    SimpleListFilter,
    TabularInline,
    register,
    site,
)
from django.db.models import Model

# external imports
import django_simple_file_handler as dsfh
from accounts.admin import AccountrAdmin, UserListFilter
from import_export.admin import ImportExportModelAdmin

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
from .resource import (
    ChargingRateResource,
    DocumentResource,
    DocumentSignOffResource,
    EquipmentResource,
    LocationResource,
    ShiftReource,
    UserListEntryResource,
)


class LocationListFilter(SimpleListFilter):
    """Custom admin filter for hierarchical location filtering.

    Filters equipment and location objects by location code, supporting
    hierarchical location structures where child locations can be filtered
    based on parent location codes using a prefix matching approach.

    Attributes:
        title (str):
            The human-readable title displayed in the admin sidebar.
        parameter_name (str):
            The URL parameter name used for this filter.
    """

    title = "Location"
    parameter_name = "location"

    def lookups(self, request, model_admin):
        """Build lookup table of location IDs to location objects.

        Args:
            request (HttpRequest):
                The current HTTP request object.
            model_admin (ModelAdmin):
                The model admin instance this filter is being used with.

        Returns:
            (list):
                List of tuples containing (id, location) pairs for all locations
                ordered by tree structure.
        """
        qs = Location.objects.all().order_by("tree_id", "lft")
        return [(loc.pk, loc) for loc in qs.all()]

    def queryset(self, request, queryset):
        """Filter queryset based on location hierarchy.

        Applies different filtering logic based on the model being filtered:
        - For Location model: returns descendant locations (excluding self)
        - For Equipment model: returns equipment in the selected location and descendants
        - For other models: returns unfiltered queryset

        Args:
            request (HttpRequest):
                The current HTTP request object.
            queryset (QuerySet):
                The queryset to be filtered.

        Returns:
            (QuerySet):
                Filtered queryset based on location hierarchy, or unfiltered
                queryset if no location is selected.
        """
        if not self.value():
            return queryset

        try:
            # Get the location object by ID
            location = Location.objects.get(pk=self.value())
        except (Location.DoesNotExist, ValueError):
            return queryset.none()

        if queryset.model is Location:
            # Return descendants only (exclude self)
            return queryset.filter(pk__in=location.get_descendants(include_self=False))
        if queryset.model is Equipment:
            # Return equipment in this location and all descendants
            descendant_locations = location.get_descendants(include_self=True)
            return queryset.filter(location__in=descendant_locations)
        return queryset


class EquipmentListFilter(SimpleListFilter):
    """Custom admin filter for filtering objects by equipment.

    Provides a filter in the admin interface that allows filtering objects
    based on equipment, displaying all equipment ordered by name.

    Attributes:
        title (str):
            The human-readable title displayed in the admin sidebar.
        parameter_name (str):
            The URL parameter name used for this filter.
    """

    title = "Equipment"
    parameter_name = "equipment"

    def lookups(self, request, model_admin):
        """Build lookup table of equipment primary keys to equipment objects.

        Args:
            request (HttpRequest):
                The current HTTP request object.
            model_admin (ModelAdmin):
                The model admin instance this filter is being used with.

        Returns:
            (list):
                List of tuples containing (pk, equipment) pairs for all equipment
                ordered by name.
        """
        qs = Equipment.objects.all().order_by("name")
        return [(loc.pk, loc) for loc in qs.all()]

    def queryset(self, request, queryset):
        """Filter queryset based on selected equipment.

        Args:
            request (HttpRequest):
                The current HTTP request object.
            queryset (QuerySet):
                The queryset to be filtered.

        Returns:
            (QuerySet):
                Filtered queryset containing only objects associated with the
                selected equipment, or unfiltered queryset if no equipment is selected.
        """
        if not self.value():
            return queryset
        return queryset.filter(equipment__pk=self.value())


class UserListInlineAdmin(TabularInline):
    """Inline admin interface for UserListEntry objects.

    Provides a tabular inline interface for managing user list entries within
    equipment or account admin pages. User list entries define which users have
    access to specific equipment and their associated roles.

    Attributes:
        model (Model):
            The UserListEntry model class.
        suit_classes (str):
            CSS classes for Django Suit theme styling and tab organisation.
        extra (int):
            Number of empty forms to display for adding new entries.
    """

    model = UserListEntry
    suit_classes = "suit-tab suit-tab-userlists"
    extra = 0


class DocumentSignOffInlineAdmin(TabularInline):
    """Inline admin interface for DocumentSignOff objects.

    Provides a tabular inline interface for managing document sign-offs within
    document admin pages. Sign-offs track which users have acknowledged or approved
    specific document versions.

    Attributes:
        model (Model):
            The DocumentSignOff model class.
        suit_classes (str):
            CSS classes for Django Suit theme styling and tab organisation.
        extra (int):
            Number of empty forms to display for adding new entries.
    """

    model = DocumentSignOff
    suit_classes = "suit-tab suit-tab-signoffs"
    extra = 0


class ChargingRateInlineAdmin(TabularInline):
    """Inline admin interface for ChargingRate objects.

    Provides a tabular inline interface for managing charging rates within
    equipment admin pages. Charging rates define the cost structure for using
    specific equipment over time.

    Attributes:
        model (Model):
            The ChargingRate model class.
        suit_classes (str):
            CSS classes for Django Suit theme styling and tab organisation.
        extra (int):
            Number of empty forms to display for adding new entries.
    """

    model = ChargingRate
    suit_classes = "suit-tab suit-tab-chargingrates"
    extra = 1


@register(DocumentSignOff)
class DocumentSignOffAdmin(ImportExportModelAdmin):
    """Admin interface configuration for DocumentSignOff objects.

    Manages document sign-off records tracking which users have acknowledged or
    approved specific document versions. Provides filtering by user, document,
    version, and creation date along with import/export capabilities.

    Attributes:
        list_display (tuple):
            Fields displayed in the admin list view.
        list_filter (tuple):
            Fields and custom filters available in the admin sidebar.
        suit_list_filter_horizontal (tuple):
            Fields displayed as horizontal filters in Django Suit theme.
        search_fields (list):
            Fields that can be searched in the admin search box.
    """

    list_display = ("user", "document", "version", "created")
    list_filter = (UserListFilter, "document", "version", "created")
    suit_list_filter_horizontal = ("user", "document", "version", "created")
    search_fields = ["document__title", "user__last_name", "user__first_name", "username"]

    def get_export_resource_class(self):
        """Return the import-export resource class for data export.

        Returns:
            (type):
                The DocumentSignOffResource class used for exporting sign-off data.
        """
        return DocumentSignOffResource

    def get_import_resource_class(self):
        """Return the import-export resource class for data import.

        Returns:
            (type):
                The DocumentSignOffResource class used for importing sign-off data.
        """
        return DocumentSignOffResource


@register(Document)
class DocumentAdmin(ImportExportModelAdmin):
    """Admin interface configuration for Document objects.

    Manages equipment-related documents such as SOPs, safety procedures, and
    training materials. Provides comprehensive document management including
    versioning, categorisation, file attachments, and sign-off tracking.

    Attributes:
        actions (None):
            Admin actions disabled for documents.
        search_fields (list):
            Fields that can be searched in the admin search box.
        readonly_fields (list):
            Fields that cannot be edited in the admin interface.
        suit_form_tabs (tuple):
            Tab definitions for Django Suit theme organisation.
        fieldsets (list):
            Field groupings and layout for the document edit form.
        list_display (list):
            Fields displayed in the admin list view.
        list_filter (list):
            Fields available for filtering in the admin sidebar.
        suit_list_filter_horizontal (tuple):
            Fields displayed as horizontal filters in Django Suit theme.
        ordering (list):
            Default ordering for the document list view.
        inlines (list):
            Inline admin classes to display related sign-off objects.
    """

    actions = None
    search_fields = [
        "title",
        "extra_text",
        "category",
    ]
    readonly_fields = [
        "created",
        "updated",
    ]
    suit_form_tabs = (("basic", "Details"), ("dates", "Dates"), ("signoffs", "Sign-Offs"))

    fieldsets = [
        (
            None,
            {
                "classes": ("suit-tab", "suit-tab-basic"),
                "fields": [
                    "title",
                    ("category", "version"),
                    "extra_text",
                    "saved_file",
                ],
            },
        ),
        (
            "Date and time information",
            {
                "classes": ("suit-tab", "suit-tab-dates"),
                "fields": [
                    "created",
                    "updated",
                ],
            },
        ),
    ]
    list_display = [
        "title",
        "category",
        "version",
        "file_link",
        "created",
        "updated",
    ]
    list_filter = [
        "title",
        "category",
        "version",
        "created",
        "updated",
    ]
    suit_list_filter_horizontal = list_filter

    ordering = [
        "category",
        "title",
        "version",
    ]

    inlines = [DocumentSignOffInlineAdmin]

    def get_export_resource_class(self):
        """Return the import-export resource class for data export.

        Returns:
            (type):
                The DocumentResource class used for exporting document data.
        """
        return DocumentResource

    def get_import_resource_class(self):
        """Return the import-export resource class for data import.

        Returns:
            (type):
                The DocumentResource class used for importing document data.
        """
        return DocumentResource


@register(Location)
class LocationAdmin(ImportExportModelAdmin):
    """Admin interface configuration for Location objects.

    Manages hierarchical laboratory locations such as buildings, rooms, and
    specific areas. Supports nested location structures with code-based
    organisation and parent-child relationships.

    Attributes:
        list_display (list):
            Fields displayed in the admin list view.
        list_filter (list):
            Fields and custom filters available in the admin sidebar.
        suit_list_filter_horizontal (list):
            Fields displayed as horizontal filters in Django Suit theme.
        search_fields (tuple):
            Fields that can be searched in the admin search box.
        ordering (list):
            Default ordering for the location list view.
    """

    list_display = ["name", "parent"]
    list_filter = ["name", LocationListFilter]
    suit_list_filter_horizontal = ["name", "parent"]
    search_fields = (
        "name",
        "description",
        "parent__name",
    )
    ordering = ["tree_id", "lft"]

    def get_export_resource_class(self):
        """Return the import-export resource class for data export.

        Returns:
            (type):
                The LocationResource class used for exporting location data.
        """
        return LocationResource

    def get_import_resource_class(self):
        """Return the import-export resource class for data import.

        Returns:
            (type):
                The LocationResource class used for importing location data.
        """
        return LocationResource


@register(Shift)
class ShiftAdmin(ImportExportModelAdmin):
    """Admin interface configuration for Shift objects.

    Manages time shift definitions for equipment booking, including start and
    end times and weighting factors for different time periods (e.g., day shifts,
    night shifts, weekend shifts).

    Attributes:
        list_display (list):
            Fields displayed in the admin list view.
        list_filter (list):
            Fields available for filtering in the admin sidebar.
        suit_list_filter_horizontal (list):
            Fields displayed as horizontal filters in Django Suit theme.
        search_fields (list):
            Fields that can be searched in the admin search box.
    """

    list_display = ["name", "start_time", "end_time", "weighting"]
    list_filter = list_display
    suit_list_filter_horizontal = list_display
    search_fields = ["name", "description"]

    def get_export_resource_class(self):
        """Return the import-export resource class for data export.

        Returns:
            (type):
                The ShiftReource class used for exporting shift data.
        """
        return ShiftReource

    def get_import_resource_class(self):
        """Return the import-export resource class for data import.

        Returns:
            (type):
                The ShiftReource class used for importing shift data.
        """
        return ShiftReource


@register(Equipment)
class EquipmentAdmin(ImportExportModelAdmin):
    """Admin interface configuration for Equipment objects.

    Manages laboratory equipment including details, location, ownership, booking
    policies, charging rates, and user access lists. Provides comprehensive equipment
    administration with tabbed interface for different aspects of equipment management.

    Attributes:
        list_display (list):
            Fields displayed in the admin list view.
        list_filter (list):
            Fields and custom filters available in the admin sidebar.
        list_editable (list):
            Fields that can be edited directly in the list view.
        suit_list_filter_horizontal (list):
            Fields displayed as horizontal filters in Django Suit theme.
        search_fields (tuple):
            Fields that can be searched in the admin search box.
        suit_form_tabs (tuple):
            Tab definitions for Django Suit theme organisation.
        fieldsets (tuple):
            Field groupings and layout for the equipment edit form.
        inlines (list):
            Inline admin classes to display related objects.
    """

    list_display = ["name", "category", "location", "owner", "offline"]
    list_filter = ["name", "category", LocationListFilter, "owner", "offline"]
    list_editable = ["category", "offline"]
    suit_list_filter_horizontal = ["name", "category", "location", "owner", "offline"]

    search_fields = (
        "name",
        "description",
        "location__name",
        "owner__first_name",
        "owner__last_name",
    )
    suit_form_tabs = (
        ("basic", "Details"),
        ("resources", "Resources"),
        ("userlists", "Userlist"),
        ("shifts", "Shifts"),
        ("policies", "Booking Policies"),
        ("chargingrates", "Charging Rates"),
    )
    fieldsets = (
        (
            "Details",
            {
                "classes": ("suit-tab", "suit-tab-basic"),
                "fields": [
                    ("name", "offline"),
                    ("category", "location"),
                    "owner",
                    "description",
                ],
            },
        ),
        (
            "Files and Images",
            {
                "classes": ("suit-tab", "suit-tab-resources"),
                "fields": [
                    "photos",
                    "files",
                    "pages",
                ],
            },
        ),
        (
            "Booking Policies",
            {
                "classes": ("suit-tab", "suit-tab-policies"),
                "fields": [
                    "policies",
                ],
            },
        ),
        (
            "Shifts",
            {
                "classes": ("suit-tab", "suit-tab-shifts"),
                "fields": ["shifts"],
            },
        ),
    )
    inlines = [UserListInlineAdmin, ChargingRateInlineAdmin]

    def get_export_resource_class(self):
        """Return the import-export resource class for data export.

        Returns:
            (type):
                The EquipmentResource class used for exporting equipment data.
        """
        return EquipmentResource

    def get_import_resource_class(self):
        """Return the import-export resource class for data import.

        Returns:
            (type):
                The EquipmentResource class used for importing equipment data.
        """
        return EquipmentResource


@register(UserListEntry)
class UserListAdmin(ImportExportModelAdmin):
    """Admin interface configuration for UserListEntry objects.

    Manages user access lists for equipment, defining which users have permission
    to use specific equipment, their roles, and any access restrictions or holds.
    Supports bulk editing of roles and administrative holds.

    Attributes:
        list_display (list):
            Fields displayed in the admin list view.
        list_filter (list):
            Fields and custom filters available in the admin sidebar.
        list_editable (list):
            Fields that can be edited directly in the list view.
        suit_list_filter_horizontal (list):
            Fields displayed as horizontal filters in Django Suit theme.
        search_fields (tuple):
            Fields that can be searched in the admin search box.
    """

    list_display = ["user", "equipment", "role", "hold", "admin_hold"]
    list_filter = [UserListFilter, EquipmentListFilter, "role", "hold", "admin_hold"]
    list_editable = ["role", "admin_hold"]
    suit_list_filter_horizontal = ["user", "equipment", "role", "hold", "admin_hold"]
    search_fields = (
        "user__first_name",
        "user__last_name",
        "equipment__name",
        "equipment__description",
        "role__name",
        "role__description",
    )

    def get_export_resource_class(self):
        """Return the import-export resource class for data export.

        Returns:
            (type):
                The UserListEntryResource class used for exporting user list data.
        """
        return UserListEntryResource

    def get_import_resource_class(self):
        """Return the import-export resource class for data import.

        Returns:
            (type):
                The UserListEntryResource class used for importing user list data.
        """
        return UserListEntryResource


@register(ChargingRate)
class ChargingRateAdmin(ImportExportModelAdmin):
    """Admin interface configuration for ChargingRate objects.

    Manages equipment charging rates that define costs for equipment usage.
    Associates cost rates with equipment and tracks rate validity periods.
    Supports bulk editing of charge rates directly in the list view.

    Attributes:
        list_display (list):
            Fields displayed in the admin list view.
        list_filter (list):
            Fields available for filtering in the admin sidebar.
        list_editable (list):
            Fields that can be edited directly in the list view.
        suit_list_filter_horizontal (list):
            Fields displayed as horizontal filters in Django Suit theme.
        search_fields (list):
            Fields that can be searched in the admin search box.
    """

    list_display = ["equipment", "cost_rate", "charge_rate", "dates", "comment"]
    list_filter = list_display
    list_editable = ["charge_rate"]
    suit_list_filter_horizontal = list_display
    search_fields = ["equipment__name", "cost_rate_name", "comment"]

    def get_export_resource_class(self):
        """Return the import-export resource class for data export.

        Returns:
            (type):
                The ChargingRateResource class used for exporting charging rate data.
        """
        return ChargingRateResource

    def get_import_resource_class(self):
        """Return the import-export resource class for data import.

        Returns:
            (type):
                The ChargingRateResource class used for importing charging rate data.
        """
        return ChargingRateResource


# Monkey patch the extra inlines for user lists
AccountrAdmin.inlines.append(UserListInlineAdmin)

# Unregister all the django-simple-file-handler admins
for model in dir(dsfh.models):
    model = getattr(dsfh.models, model)
    if isinstance(model, type) and issubclass(model, Model):
        if model in site._registry:
            site.unregister(model)
