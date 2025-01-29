# -*- coding: utf-8 -*-
"""
Admin interfaces for util modles
"""
# Django imports
from django.contrib import admin
from django.contrib.admin import register
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django.urls import reverse

# external imports
from sitetree.admin import (
    TreeAdmin,
    TreeItemAdmin,
    override_item_admin,
    override_tree_admin,
)
from tinymce.widgets import TinyMCE

# app imports
from .fields import ObfuscatedCharField
from .widgets import AdminObfuscatedTinyMCE

# Monkey-patch sitetree admin for django-suit v2


# Register your models here.


# And our custom tree item admin model.
class CustomTreeItemAdmin(TreeItemAdmin):
    """Custom sitetree item admin to add ability to control display groups."""

    fieldsets = (
        (
            "Basic settings",
            {
                "classes": (
                    "baton-tabs-init",
                    "baton-tab-fs-basic",
                    "baton-tab-fs-access",
                    "baton-tab-fs-display",
                    "baton-tab-fs-extra",
                ),
                "fields": (
                    "parent",
                    "title",
                    "url",
                ),
            },
        ),
        (
            "Access settings",
            {
                "classes": ("tab-fs-access",),
                "fields": (
                    "access_loggedin",
                    "access_guest",
                    "access_restricted",
                    ("access_staff", "access_superuser"),
                    "access_permissions",
                    "access_perm_type",
                    "groups",
                    "not_groups",
                ),
            },
        ),
        (
            "Display settings",
            {"classes": ("tab-fs-display",), "fields": ("hidden", "inmenu", "inbreadcrumbs", "insitetree")},
        ),
        (
            "Additional settings",
            {"classes": ("tab-fs-extra",), "fields": ("hint", "description", "alias", "urlaspattern")},
        ),
    )

    filter_horizontal = ("access_permissions", "groups", "not_groups")


class CustomTreeAdmin(TreeAdmin):
    """Simple duplicate."""


override_tree_admin(CustomTreeAdmin)
override_item_admin(CustomTreeItemAdmin)


admin.site.unregister(FlatPage)


@register(FlatPage)
class TinyMCEFlatPageAdmin(FlatPageAdmin):
    """Admin interface definition for flatpages that adds TinyMCE editor."""

    list_display = ["url", "title", "enable_comments"]
    list_filters = ["url", "title", "enable_comments"]
    suit_list_filter_horizontal = ["url", "title", "enable_comments"]
    suit_form_tabs = (
        ("basic", "Basic"),
        ("advanced", "Advanced"),
    )

    fieldsets = (
        ("Basic Details", {"classes": ("suit-tab", "suit-tab-basic"), "fields": ("url", "title", "content")}),
        (
            "Advanced options",
            {
                "classes": ("suit-tab", "suit-tab-advanced"),
                "fields": ("registration_required", "template_name", "sites"),
            },
        ),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Replace the widget for the content with TinyMCE editor."""
        if db_field.name == "content":
            ret = ObfuscatedCharField(
                widget=AdminObfuscatedTinyMCE(
                    attrs={"cols": 80, "rows": 30},
                    mce_attrs={"external_link_list_url": reverse("tinymce-linklist")},
                )
            )
            return ret
        return super().formfield_for_dbfield(db_field, request, **kwargs)
