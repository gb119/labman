#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Django admin interface configurations for user accounts, groups, and roles.

This module provides admin interfaces for managing user accounts, research groups,
roles, and authentication groups through the Django admin panel. It includes
custom filters, inline administrators, and import/export functionality for data
management.
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
from .forms import UserAdminForm
from .models import Account, ResearchGroup, Role
from .resource import (
    GroupResource,
    ResearchGroupResource,
    RoleResource,
    UserResource,
)

# Register your models here.


class UserListFilter(SimpleListFilter):
    """Custom admin filter for filtering objects by user account.

    Provides a filter in the admin interface that allows filtering objects based
    on user accounts, displaying users ordered by last name and first name.

    Attributes:
        title (str):
            The human-readable title for the filter displayed in the admin sidebar.
        parameter_name (str):
            The URL parameter name used for this filter.
    """

    title = "user"
    parameter_name = "user"

    def lookups(self, request, model_admin):
        """Build lookup table of username to user display values.

        Args:
            request (HttpRequest):
                The current HTTP request object.
            model_admin (ModelAdmin):
                The model admin instance this filter is being used with.

        Returns:
            (list):
                List of tuples containing (username, user) pairs for all users
                ordered by last name and first name.
        """
        qs = Account.objects.all().order_by("last_name", "first_name")
        return [(user.username, user) for user in qs.all()]

    def queryset(self, request, queryset):
        """Filter queryset based on selected user.

        Args:
            request (HttpRequest):
                The current HTTP request object.
            queryset (QuerySet):
                The queryset to be filtered.

        Returns:
            (QuerySet):
                Filtered queryset containing only objects matching the selected
                user, or unfiltered queryset if no user is selected.
        """
        if not self.value():
            return queryset
        return queryset.filter(user__username=self.value())


site.unregister(Group)


@register(Role)
class RoleAdmin(ImportExportModelAdmin):
    """Admin interface configuration for Role objects.

    Provides list display, filtering, searching, and import/export functionality
    for user roles within the system. Roles represent different permission levels
    and capabilities that can be assigned to users.

    Attributes:
        list_display (tuple):
            Fields displayed in the admin list view.
        list_filter (tuple):
            Fields available for filtering in the admin sidebar.
        search_fields (tuple):
            Fields that can be searched in the admin search box.
    """

    list_display = ("name", "level")
    list_filter = list_display
    search_fields = list_filter

    def get_export_resource_class(self):
        """Return the import-export resource class for data export.

        Returns:
            (type):
                The RoleResource class used for exporting role data.
        """
        return RoleResource

    def get_import_resource_class(self):
        """Return the import-export resource class for data import.

        Returns:
            (type):
                The RoleResource class used for importing role data.
        """
        return RoleResource


@register(ResearchGroup)
class ResearchGroupAdmin(ImportExportModelAdmin):
    """Admin interface configuration for ResearchGroup objects.

    Manages research group administration including display, filtering, and
    import/export capabilities. Research groups organise users into teams or
    departments for project management and resource allocation.

    Attributes:
        list_display (tuple):
            Fields displayed in the admin list view.
        list_filter (tuple):
            Fields available for filtering in the admin sidebar.
        suit_list_filter_horizontal (tuple):
            Fields displayed as horizontal filters in Django Suit theme.
        search_fields (tuple):
            Fields that can be searched in the admin search box.
    """

    list_display = ("name", "code")
    list_filter = list_display
    suit_list_filter_horizontal = list_filter
    search_fields = list_filter

    def get_export_resource_class(self):
        """Return the import-export resource class for data export.

        Returns:
            (type):
                The ResearchGroupResource class used for exporting research group data.
        """
        return ResearchGroupResource

    def get_import_resource_class(self):
        """Return the import-export resource class for data import.

        Returns:
            (type):
                The ResearchGroupResource class used for importing research group data.
        """
        return ResearchGroupResource


class PhotoInlineAdmin(TabularInline):
    """Inline admin interface for Photo objects.

    Provides a tabular inline interface for managing Photo objects within
    another model's admin page, typically used for managing user profile photos.

    Attributes:
        model (Model):
            The Photo model class from photologue.
    """

    model = Photo


class PageInlineAdmin(TabularInline):
    """Inline admin interface for FlatPage objects.

    Provides a tabular inline interface for managing FlatPage objects within
    another model's admin page, allowing management of associated static pages.

    Attributes:
        model (Model):
            The FlatPage model class from django.contrib.flatpages.
    """

    model = FlatPage


try:
    site.unregister(Account)
except sites.NotRegistered:
    pass


@register(Account)
class AccountrAdmin(ImportExportMixin, UserAdmin):
    """Admin interface configuration for user Account objects.

    Provides comprehensive user account management including personal information,
    permissions, resource associations, and import/export functionality. Extends
    Django's UserAdmin with custom fields specific to the laboratory management system.

    Attributes:
        form (Form):
            Custom form class used for account editing.
        suit_form_tabs (tuple):
            Tab definitions for Django Suit theme organisation.
        fieldsets (tuple):
            Field groupings and layout for the account edit form.
        list_display (list):
            Fields displayed in the admin list view.
        list_filter (tuple):
            Fields available for filtering in the admin sidebar.
        suit_list_filter_horizontal (tuple):
            Fields displayed as horizontal filters in Django Suit theme.
        search_fields (tuple):
            Fields that can be searched in the admin search box.
        inlines (list):
            Inline admin classes to display related objects.
    """

    form = UserAdminForm
    suit_form_tabs = (
        ("personal", "Personal"),
        ("perms", "Permissions"),
        ("dates", "Dates"),
        ("userlists", "Userlist Entries"),
        ("resources", "Resources"),
    )
    fieldsets = (
        (
            _("Personal info"),
            {
                "classes": ("suit-tab", "suit-tab-personal"),
                "fields": [
                    ("username", "number"),
                    ("title", "first_name", "last_name"),
                    ("email", "research_group", "manager"),
                    ("project",),
                ],
            },
        ),
        (
            _("Permissions"),
            {
                "classes": ("suit-tab", "suit-tab-perms"),
                "fields": (
                    ("is_active", "is_staff", "is_superuser"),
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "classes": ("suit-tab", "suit-tab-dates"),
                "fields": (("last_login", "date_joined"),),
            },
        ),
        (
            _("Resources"),
            {
                "classes": ("suit-tab", "suit-tab-resources"),
                "fields": ("photos", "pages"),
            },
        ),
    )
    list_display = [
        "username",
        "last_name",
        "first_name",
        "manager",
        "research_group",
        "is_staff",
        "photo_tag",
    ]
    list_filter = (
        "username",
        "groups",
        "manager",
        "is_staff",
        "is_superuser",
        "research_group",
    )
    suit_list_filter_horizontal = list_filter
    search_fields = (
        "username",
        "first_name",
        "last_name",
        "groups__name",
        "research_group__name",
    )
    inlines = []

    def get_export_resource_class(self):
        """Return the import-export resource class for data export.

        Returns:
            (type):
                The UserResource class used for exporting user account data.
        """
        return UserResource

    def get_import_resource_class(self):
        """Return the import-export resource class for data import.

        Returns:
            (type):
                The UserResource class used for importing user account data.
        """
        return UserResource

    def photo_tag(self, obj):
        """Generate HTML thumbnail image tag for user's profile photo.

        Args:
            obj (Account):
                The user account object containing mugshot photo information.

        Returns:
            (SafeString):
                HTML-safe string containing an img tag with the user's thumbnail,
                or a non-breaking space if no mugshot is available.
        """
        if obj.mugshot:
            return format_html(
                f"<img src='{obj.mugshot.get_admin_thumbnail_url()}' alt='Picture of {obj.display_name}' />"
            )
        return format_html("&nbsp;")

    photo_tag.short_description = "Image"
    photo_tag.allow_tags = True


@register(Group)
class ImportExportGroupAdmin(ImportExportMixin, GroupAdmin):
    """Admin interface configuration for Django authentication Group objects.

    Extends Django's built-in GroupAdmin with import/export functionality for
    managing user groups and their permissions. Groups provide a way to categorise
    users and assign permissions collectively.
    """

    def get_export_resource_class(self):
        """Return the import-export resource class for data export.

        Returns:
            (type):
                The GroupResource class used for exporting group data.
        """
        return GroupResource

    def get_import_resource_class(self):
        """Return the import-export resource class for data import.

        Returns:
            (type):
                The GroupResource class used for importing group data.
        """
        return GroupResource
