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
from .models import Account, Project, ResearchGroup, Role

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


class StrippedCharWidget(widgets.CharWidget):
    """Hacked to make sure usernames don't have leading or trailing space spaces."""

    def clean(self, value, row=None, **kwargs):
        """Clean the value and then strip the resulting string."""
        return super().clean(value, row, **kwargs).strip()


class ResearchGroupResource(resources.ModelResource):
    """Import export resource for ResearchGroup objects."""

    class Meta:
        model = ResearchGroup
        import_id_fields = ["name"]


class RoleResource(resources.ModelResource):
    """Import-Export resource for Role objects."""

    class Meta:
        model = Role
        import_id_fields = ["name"]


class ProjectResource(resources.ModelResource):
    """Import-export resource for Project code objects."""

    class Meta:
        model = Project
        import_id_fields = ["id"]


class UserResource(resources.ModelResource):
    """Import-export resource objects for User objects."""

    groups = fields.Field(
        column_name="groups",
        attribute="groups",
        widget=widgets.ManyToManyWidget(Group, ";", "name"),
    )

    research_group = fields.Field(
        column_name="research_group",
        attribute="research_group",
        widget=widgets.ForeignKeyWidget(ResearchGroup, "code"),
    )

    username = fields.Field(column_name="username", attribute="username", widget=StrippedCharWidget())

    class Meta:
        model = Account
        fields = (
            "username",
            "title",
            "first_name",
            "last_name",
            "email",
            "project",
            "date_joined",
            "end_date",
            "groups",
            "is_staff",
            "number",
            "research_group",
        )
        import_id_fields = ["username"]

    def import_row(self, row, instance_loader, using_transactions=True, dry_run=False, raise_errors=None, **kwargs):
        """Match up bad fields."""
        if "username" not in row and "Email Address" in row:  # Create username and email columns
            parts = row["Email Address"].split("@")
            row["username"] = parts[0].strip().lower()
            row["email"] = row["Email Address"].strip()
        if "first_name" not in row and "last_name" not in row and "Student Name" in row:  # Sort out name
            parts = row["Student Name"].split(", ")
            row["last_name"] = parts[0].strip()
            row["first_name"] = parts[1].strip()
        if "Student ID" in row and "number" not in row:  # Student ID number
            row["number"] = row["Student ID"]
        if "Class" in row and "groups" not in row:  # Setup a group
            row["groups"] = "Student"
        if "groups" in row and row["groups"] is not None and "Instructor" in row["groups"]:
            row["is_staff"] = 1
        for bad_field in [
            "mark_count",
            "mark",
            "students",
        ]:  # remove calculated fields from import
            if bad_field in row:
                del row[bad_field]

        return super().import_row(row, instance_loader, using_transactions, dry_run, **kwargs)


site.unregister(Group)


class GroupResource(resources.ModelResource):
    """Import-export resource for Group objects."""

    class Meta:
        model = Group
        fields = ("name", "permissions")
        import_id_fields = ["name"]


class UserAdminForm(forms.ModelForm):
    """Model form definition for user accounts."""

    class Meta:
        model = Account
        widgets = {
            "first_name": forms.TextInput(attrs={"size": 20}),
            "last_name": forms.TextInput(attrs={"size": 20}),
        }
        fields = "__all__"


@register(Role)
class RoleAdmin(ImportExportModelAdmin):
    """Admin interface definition for Role objects."""

    list_display = ("name", "level")
    list_filter = list_display
    search_fields = list_filter

    def get_export_resource_class(self):
        """return the import-export resource object."""
        return RoleResource

    def get_import_resource_class(self):
        """return the import-export resource object."""
        return RoleResource


@register(Project)
class ProjectAdmin(ImportExportModelAdmin):
    """Admin interface definition for Project code objects."""

    list_display = ("short_name", "name", "code")
    list_filter = list_display
    search_fields = ("short_name", "name", "code", "description")

    def get_export_resource_class(self):
        """return the import-export resource object."""
        return ProjectResource

    def get_import_resource_class(self):
        """return the import-export resource object."""
        return ProjectResource


@register(ResearchGroup)
class ResearchGroupAdmin(ImportExportModelAdmin):
    """Admin interface definition for Research Group objects."""

    list_display = ("name", "code")
    list_filter = list_display
    suit_list_filter_horizontal = list_filter
    search_fields = list_filter

    def get_export_resource_class(self):
        """return the import-export resource object."""
        return ResearchGroupResource

    def get_import_resource_class(self):
        """return the import-export resource object."""
        return ResearchGroupResource


try:
    site.unregister(Account)
except sites.NotRegistered:
    pass


class PhotoInlineAdmin(TabularInline):
    """Minimal inline admin interface definition for Photo objects."""

    model = Photo


class PageInlineAdmin(TabularInline):
    """Minimal inline admin definition for Page objects."""

    model = FlatPage


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
    search_fields = (
        "username",
        "first_name",
        "last_name",
        "groups__name",
        "research_group__name",
    )
    inlines = []

    def get_export_resource_class(self):
        """return the import-export resource object."""
        return UserResource

    def get_import_resource_class(self):
        """return the import-export resource object."""
        return UserResource

    def photo_tag(self, obj):
        """Provide a phoot in the admin list view."""
        if hasattr(obj, "photos") and obj.photos.all().count() > 0:
            return format_html(
                f"<img src='{obj.photos.first().get_thumbnail_url()}' alt='Picture of {obj.display_name}' />"
            )
        return "&nbsp;"

    photo_tag.short_description = "Image"
    photo_tag.allow_tags = True


@register(Group)
class ImportExportGroupAdmin(ImportExportMixin, GroupAdmin):
    """Admin interface definition for user Group objects."""

    def get_export_resource_class(self):
        """return the import-export resource object."""
        return GroupResource

    def get_import_resource_class(self):
        """return the import-export resource object."""
        return GroupResource
