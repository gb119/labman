# Django imports
from django import forms
from django.contrib.admin import (
    SimpleListFilter,
    TabularInline,
    register,
    site,
    sites,
)
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group
from django.contrib.flatpages.models import FlatPage
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

# external imports
from import_export import fields, resources, widgets
from import_export.admin import ImportExportMixin, ImportExportModelAdmin
from photologue.models import Photo

# app imports
from .models import CostCentre, CostRate
from .resource import CostCentreResource, CostRateResource

# Register your models here.


@register(CostRate)
class CosRateAdmin(ImportExportModelAdmin):
    """Admin Interface for CostRate objects."""

    list_display = ("name", "description")
    list_filter = list_display
    search_fields = ("name", "description")

    def get_export_resource_class(self):
        """Return the import-export resource object."""
        return CostRateResource

    def get_import_resource_class(self):
        """Return the import-export resource object."""
        return CostRateResource


@register(CostCentre)
class CostCentreAdmin(ImportExportModelAdmin):
    """Admin interface definition for CostCentre code objects."""

    list_display = ("short_name", "name", "code")
    list_filter = list_display
    search_fields = ("short_name", "name", "code", "description")

    def get_export_resource_class(self):
        """Return the import-export resource object."""
        return CostCentreResource

    def get_import_resource_class(self):
        """Return the import-export resource object."""
        return CostCentreResource
