# -*- coding: utf-8 -*-
"""Admin interface for equipment app."""
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
from import_export import resources
from import_export.admin import ImportExportModelAdmin

# app imports
from .models import (
    Document,
    DocumentSignOff,
    Equipment,
    Location,
    UserListEntry,
)


class LocationListFilter(SimpleListFilter):
    """Actually uses the location code field to filter by."""

    title = "Location"
    parameter_name = "location"

    def lookups(self, request, model_admin):
        """Build a lookup table of code:location."""
        qs = Location.objects.all().order_by("code")
        return [(loc.code, loc) for loc in qs.all()]

    def queryset(self, request, queryset):
        """If value is set then filter for lcoations that startwith, but are not equal to value."""
        if not self.value():
            return queryset
        if queryset.model is Location:
            return queryset.filter(code__startswith=self.value()).exclude(code=self.value())
        if queryset.model is Equipment:
            return queryset.filter(location__code__startswith=self.value())
        return queryset


class EquipmentListFilter(SimpleListFilter):
    """Actually uses the location code field to filter by."""

    title = "Equipment"
    parameter_name = "equipment"

    def lookups(self, request, model_admin):
        """Build a lookup table of code:location."""
        qs = Equipment.objects.all().order_by("name")
        return [(loc.pk, loc) for loc in qs.all()]

    def queryset(self, request, queryset):
        """If value is set then filter for lcoations that startwith, but are not equal to value."""
        if not self.value():
            return queryset
        return queryset.filter(equipment__pk=self.value())


class LocationResource(resources.ModelResource):
    """Import-export resource for Location objects."""

    class Meta:
        model = Location
        import_id_fields = ["name"]


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

    class Meta:
        model = Equipment
        import_id_fields = ["name"]


class UserListEntryResource(resources.ModelResource):
    """Import-export resource for UserListEntry objects."""

    class Meta:
        model = UserListEntry


class UserListInlineAdmin(TabularInline):
    """Inline admin interface definition for UserListEntry objects."""

    model = UserListEntry
    suit_classes = "suit-tab suit-tab-userlists"
    extra = 0


class DocumentSignOffInlineAdmin(TabularInline):
    """Inline admin interface definition for SignOff objects."""

    model = DocumentSignOff
    suit_classes = "suit-tab suit-tab-signoffs"
    extra = 0


@register(DocumentSignOff)
class DocumentSignOffAdmin(ImportExportModelAdmin):
    """Admin interface definition for SignOffs."""

    list_display = ("user", "document", "version", "created")
    list_filter = (UserListFilter, "document", "version", "created")
    suit_list_filter_horizontal = ("user", "document", "version", "created")
    search_fields = ["document__title", "user__last_name", "user__first_name", "username"]

    def get_export_resource_class(self):
        """Return import-export admin resource class."""
        return DocumentSignOffResource

    def get_import_resource_class(self):
        """Return import-export admin resource class."""
        return DocumentSignOffResource


@register(Document)
class DocumentAdmin(ImportExportModelAdmin):
    """Admin interface defintion dor Document objects."""

    actions = None
    search_fields = [
        "title",
        "extra_text",
        "catagory",
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
                    ("catagory", "version"),
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
        "catagory",
        "version",
        "file_link",
        "created",
        "updated",
    ]
    list_filter = [
        "title",
        "catagory",
        "version",
        "created",
        "updated",
    ]
    suit_list_filter_horizontal = list_filter

    ordering = [
        "catagory",
        "title",
        "version",
    ]

    inlines = [DocumentSignOffInlineAdmin]

    def get_export_resource_class(self):
        """Return import-export admin resource class."""
        return DocumentResource

    def get_import_resource_class(self):
        """Return import-export admin resource class."""
        return DocumentResource


@register(Location)
class LocationAdmin(ImportExportModelAdmin):
    """Admin interface definition for Location."""

    list_display = ["name", "location", "code"]
    list_filter = ["name", LocationListFilter]
    suit_list_filter_horizontal = ["name", "location"]
    search_fields = (
        "name",
        "description",
        "location__name",
    )
    ordering = ["code"]

    def get_export_resource_class(self):
        """Return import-export admin resource class."""
        return LocationResource

    def get_import_resource_class(self):
        """Return import-export admin resource class."""
        return LocationResource


@register(Equipment)
class EquipmentAdmin(ImportExportModelAdmin):
    """Admin interface definition for Equipment objects."""

    list_display = ["name", "location", "owner"]
    list_filter = ["name", LocationListFilter, "owner"]
    suit_list_filter_horizontal = ["name", "location", "owner"]

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
        ("policies", "Booking Policies"),
    )
    fieldsets = (
        (
            "Details",
            {
                "classes": ("suit-tab", "suit-tab-basic"),
                "fields": [
                    ("name", "location"),
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
            "Booking Polcies",
            {
                "classes": ("suit-tab", "suit-tab-policies"),
                "fields": [
                    "policies",
                ],
            },
        ),
    )
    inlines = [UserListInlineAdmin]

    def get_export_resource_class(self):
        """Return import-export admin resource class."""
        return EquipmentResource

    def get_import_resource_class(self):
        """Return import-export admin resource class."""
        return EquipmentResource


@register(UserListEntry)
class UserListAdmin(ImportExportModelAdmin):
    """Admin interface definition for UserList entries."""

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
        """Return import-export admin resource class."""
        return UserListEntryResource

    def get_import_resource_class(self):
        """Return import-export admin resource class."""
        return UserListEntryResource


# Monkey patch the extra inlines for user lists
AccountrAdmin.inlines.append(UserListInlineAdmin)

# Unregister all the django-simple-file-handler admins
for model in dir(dsfh.models):
    model = getattr(dsfh.models, model)
    if isinstance(model, type) and issubclass(model, Model):
        if model in site._registry:
            site.unregister(model)
