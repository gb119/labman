#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""User account and other objects admin interface classes."""
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
from .models import Account, Project, ResearchGroup, Role
from .resource import (
    GroupResource,
    ProjectResource,
    ResearchGroupResource,
    RoleResource,
    UserResource,
)

# Register your models here.


class UserListFilter(SimpleListFilter):
    """Actually uses the location code field to filter by."""

    title = "user"
    parameter_name = "user"

    def lookups(self, request, model_admin):
        """Build a lookup table of code:location."""
        qs = Account.objects.all().order_by("last_name", "first_name")
        return [(user.username, user) for user in qs.all()]

    def queryset(self, request, queryset):
        """If value is set then filter for lcoations that startwith, but are not equal to value."""
        if not self.value():
            return queryset
        return queryset.filter(user__username=self.value())


site.unregister(Group)


@register(Role)
class RoleAdmin(ImportExportModelAdmin):
    """Admin interface definition for Role objects."""

    list_display = ("name", "level")
    list_filter = list_display
    search_fields = list_filter

    def get_export_resource_class(self):
        """Return the import-export resource object."""
        return RoleResource

    def get_import_resource_class(self):
        """Return the import-export resource object."""
        return RoleResource


@register(Project)
class ProjectAdmin(ImportExportModelAdmin):
    """Admin interface definition for Project code objects."""

    list_display = ("short_name", "name", "code")
    list_filter = list_display
    search_fields = ("short_name", "name", "code", "description")

    def get_export_resource_class(self):
        """Return the import-export resource object."""
        return ProjectResource

    def get_import_resource_class(self):
        """Return the import-export resource object."""
        return ProjectResource


@register(ResearchGroup)
class ResearchGroupAdmin(ImportExportModelAdmin):
    """Admin interface definition for Research Group objects."""

    list_display = ("name", "code")
    list_filter = list_display
    suit_list_filter_horizontal = list_filter
    search_fields = list_filter

    def get_export_resource_class(self):
        """Return the import-export resource object."""
        return ResearchGroupResource

    def get_import_resource_class(self):
        """Return the import-export resource object."""
        return ResearchGroupResource


class PhotoInlineAdmin(TabularInline):
    """Minimal inline admin interface definition for Photo objects."""

    model = Photo


class PageInlineAdmin(TabularInline):
    """Minimal inline admin definition for Page objects."""

    model = FlatPage


try:
    site.unregister(Account)
except sites.NotRegistered:
    pass


@register(Account)
class AccountrAdmin(ImportExportMixin, UserAdmin):
    """Admin Interface for user Account Objects."""

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
                    "project",
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
                "fields": (("photos", "pages"),),
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
        """Return the import-export resource object."""
        return UserResource

    def get_import_resource_class(self):
        """Return the import-export resource object."""
        return UserResource

    def photo_tag(self, obj):
        """Provide a phoot in the admin list view."""
        if obj.mugshot:
            return format_html(
                f"<img src='{obj.mugshot.get_admin_thumbnail_url()}' alt='Picture of {obj.display_name}' />"
            )
        return format_html("&nbsp;")

    photo_tag.short_description = "Image"
    photo_tag.allow_tags = True


@register(Group)
class ImportExportGroupAdmin(ImportExportMixin, GroupAdmin):
    """Admin interface definition for user Group objects."""

    def get_export_resource_class(self):
        """Return the import-export resource object."""
        return GroupResource

    def get_import_resource_class(self):
        """Return the import-export resource object."""
        return GroupResource
