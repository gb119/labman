# -*- coding: utf-8 -*-
"""Django admin interface configurations for laboratory costing management.

This module provides admin interfaces for managing cost centres and cost rates
used in laboratory financial tracking and equipment charging. It includes
import/export functionality for data management and reporting.
"""
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
    """Admin interface configuration for CostRate objects.

    Manages cost rate definitions that specify different charging rates for
    equipment usage. Cost rates can represent internal rates, external rates,
    academic rates, or other pricing structures used in laboratory operations.

    Attributes:
        list_display (tuple):
            Fields displayed in the admin list view.
        list_filter (tuple):
            Fields available for filtering in the admin sidebar.
        search_fields (tuple):
            Fields that can be searched in the admin search box.
    """

    list_display = ("name", "description")
    list_filter = list_display
    search_fields = ("name", "description")

    def get_export_resource_class(self):
        """Return the import-export resource class for data export.

        Returns:
            (type):
                The CostRateResource class used for exporting cost rate data.
        """
        return CostRateResource

    def get_import_resource_class(self):
        """Return the import-export resource class for data import.

        Returns:
            (type):
                The CostRateResource class used for importing cost rate data.
        """
        return CostRateResource


@register(CostCentre)
class CostCentreAdmin(ImportExportModelAdmin):
    """Admin interface configuration for CostCentre objects.

    Manages cost centre codes used for financial tracking and reporting of
    equipment usage charges. Cost centres typically represent departments,
    projects, or grants that are charged for resource utilisation.

    Attributes:
        list_display (tuple):
            Fields displayed in the admin list view.
        list_filter (tuple):
            Fields available for filtering in the admin sidebar.
        search_fields (tuple):
            Fields that can be searched in the admin search box.
    """

    list_display = ("short_name", "name", "parent", "code")
    list_filter = ("short_name", "name")
    search_fields = ("short_name", "name", "code", "description", "parent__name")

    def get_export_resource_class(self):
        """Return the import-export resource class for data export.

        Returns:
            (type):
                The CostCentreResource class used for exporting cost centre data.
        """
        return CostCentreResource

    def get_import_resource_class(self):
        """Return the import-export resource class for data import.

        Returns:
            (type):
                The CostCentreResource class used for importing cost centre data.
        """
        return CostCentreResource
