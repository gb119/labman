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
from sitetree.admin import TreeItemAdmin
from tinymce.widgets import TinyMCE

# Monkey-patch sitetree admin for django-suit v2


def _patchTreeAdmin():
    """Wrap patching code into function to avoid polluting module namespace."""
    tabs = []
    for fieldset in TreeItemAdmin.fieldsets:
        data = fieldset[1]
        name = fieldset[0]
        name_class = name.replace(" ", "").replace(".", "")
        classes = data.get("classes", ())
        classes = ("suit-tab suit-tab", f"suit-tab-{name_class}")
        data["classes"] = classes
        tabs.append((name_class, name))
    TreeItemAdmin.suit_form_tabs = tabs


_patchTreeAdmin()

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
            ret = db_field.formfield(
                widget=TinyMCE(
                    attrs={"cols": 80, "rows": 30},
                    mce_attrs={"external_link_list_url": reverse("tinymce-linklist")},
                )
            )
            return ret
        return super().formfield_for_dbfield(db_field, request, **kwargs)
