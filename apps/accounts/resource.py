# -*- coding: utf-8 -*-
"""Resources for the account app."""
# Django imports
from django.contrib.auth.models import Group

# external imports
from import_export import fields, resources, widgets

# app imports
from .models import Account, Project, ResearchGroup, Role


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

    def import_row(self, row, instance_loader, using_transactions=True, dry_run=False, **kwargs):
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

        return super().import_row(
            row, instance_loader, using_transactions=using_transactions, dry_run=dry_run, **kwargs
        )


class GroupResource(resources.ModelResource):
    """Import-export resource for Group objects."""

    class Meta:
        model = Group
        fields = ("name", "permissions")
        import_id_fields = ["name"]
