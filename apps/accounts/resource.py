# -*- coding: utf-8 -*-
"""Resources for the account app."""
# Python imports
import re

# Django imports
from django.contrib.auth.models import Group

# external imports
from import_export import fields, resources, widgets

# app imports
from .models import Account, ResearchGroup, Role


class StrippedCharWidget(widgets.CharWidget):
    """Hacked to make sure usernames don't have leading or trailing space spaces."""

    def clean(self, value, row=None, **kwargs):
        """Clean the value and then strip the resulting string."""
        return super().clean(value, row, **kwargs).strip()


class AccountWidget(widgets.ForeignKeyWidget):
    """Try to match a user account."""

    display_name_pattern = re.compile(r"(?P<last_name>[^\,]+)\,(?P<first_name>[^\(]+)$")
    given_name_pattern = re.compile(r"(?P<last_name>[^\,]+)\,(?P<givenName>[^\(]+)\((?P<first_name>[^)]+)\)")

    def clean(self, value, row=None, *args, **kwargs):
        """Attempt to match to a user account."""
        if not value:
            return None

        # Try matching by number or username
        account = self._match_by_number_or_username(value)
        if account:
            return account

        # Build initials and formal names lookup
        initials, formal_names = self._build_initials_and_formal_names()

        # Try matching by initials or formal names
        account = self._match_by_initials_or_formal_names(value, initials, formal_names)
        if account:
            return account

        # Try matching by display name or given name
        account = self._match_by_name_pattern(value)
        if account:
            return account

        # Try matching by first and last name
        return self._match_by_first_last_name(value)

    def _match_by_number_or_username(self, value):
        """See if value can be interpreted as a SID or usnername."""
        try:
            value = int(value)
            qs = Account.objects.filter(number=value)
        except (TypeError, ValueError):
            qs = Account.objects.filter(username=value)
        return qs.first() if qs.exists() else None

    def _build_initials_and_formal_names(self):
        """Builtables of staff initials and formal names."""
        initials = {}
        formal_names = {}
        for staff in Account.objects.filter(is_staff=True):
            initials[staff.initials] = staff
            formal_names[staff.formal_name] = staff
        return initials, formal_names

    def _match_by_initials_or_formal_names(self, value, initials, formal_names):
        """Lookup tables of initials or formal names for a match."""
        return initials.get(value) or formal_names.get(value)

    def _match_by_name_pattern(self, value):
        """Match user by given name regexp."""
        pattern = self.given_name_pattern if "(" in value else self.display_name_pattern
        match = pattern.match(value)
        if match:
            qs = Account.objects.filter(**match.groupdict())
            return qs.first() if qs.exists() else None
        return None

    def _match_by_first_last_name(self, value):
        """Match by first and las names."""
        if " " in value:
            first_name, last_name = value.split(" ")[0], value.split(" ")[-1]
            qs = Account.objects.filter(first_name=first_name, last_name=last_name)
            return qs.first() if qs.exists() else None
        return None


class AccountsWidget(widgets.ManyToManyWidget):
    """An import-export widget that understands lists of user names."""

    def clean(self, value, row=None, **kwargs):
        """Perform lookups to match lists of user names or IDs."""
        if not value:
            return Account.objects.none()

        ids = self._parse_ids(value)
        accounts = self._get_accounts_by_number(ids) or self._get_accounts_by_username(ids)

        if accounts.exists():
            return accounts
        return self._get_accounts_by_name(ids)

    def _parse_ids(self, value):
        """Parse and clean the input value into a list of IDs."""
        if isinstance(value, (float, int)):
            return [int(value)]
        return filter(None, [i.strip() for i in value.split(self.separator)])

    def _get_accounts_by_number(self, ids):
        """Attempt to retrieve accounts by student number."""
        try:
            return Account.objects.filter(number__in=[int(i) for i in ids])
        except (TypeError, ValueError):
            return None

    def _get_accounts_by_username(self, ids):
        """Attempt to retrieve accounts by username."""
        return Account.objects.filter(username__in=ids)

    def _get_accounts_by_name(self, ids):
        """Retrieve accounts by parsing names."""
        pks = self._match_names_to_pks(ids)
        return Account.objects.filter(pk__in=pks)

    def _match_names_to_pks(self, ids):
        """Match names to primary keys."""
        pks = []
        initials, formal_names = self._build_name_lookup()

        for value in ids:
            if "," in value:  # last_name, first_name
                pks.extend(self._match_last_first_name(value))
            elif value in initials:  # Staff member initials
                pks.append(initials[value])
            elif value in formal_names:  # Staff member formal names
                pks.append(formal_names[value])
            else:  # first_name initials last_name
                pks.extend(self._match_first_last_name(value))
        return pks

    def _build_name_lookup(self):
        """Build lookup dictionaries for initials and formal names."""
        initials = {}
        formal_names = {}
        for staff in Account.objects.filter(is_staff=True):
            initials[staff.initials] = staff.pk
            formal_names[staff.formal_name] = staff.pk
        return initials, formal_names

    def _match_last_first_name(self, value):
        """Match accounts by last name, first name."""
        last_name, first_name = value.split(",")
        return Account.objects.filter(last_name=last_name.strip(), first_name=first_name.strip()).values_list(
            "pk", flat=True
        )

    def _match_first_last_name(self, value):
        """Match accounts by first name, last name."""
        values = [x for x in value.split(" ") if x]
        if values:
            first_name, last_name = values[0], values[-1]
            return Account.objects.filter(last_name=last_name, first_name=first_name).values_list("pk", flat=True)
        return []


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

    manager = fields.Field(
        column_name="manager",
        attribute="manager",
        widget=AccountWidget(Account, "username"),
    )

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
            "is_superuser" "number",
            "research_group",
            "manager",
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
