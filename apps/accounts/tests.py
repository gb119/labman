#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the accounts app.

This module tests the Account, ResearchGroup, and Role models, including
string representations, computed properties, and manager behaviour.
"""
# Django imports
import pytest
from django.contrib.auth.models import Group


class TestResearchGroup:
    """Tests for the ResearchGroup model."""

    @pytest.mark.django_db
    def test_create_research_group(self, research_group):
        """Creating a ResearchGroup persists it to the database."""
        from accounts.models import ResearchGroup

        assert ResearchGroup.objects.filter(code="TEST").exists()

    @pytest.mark.django_db
    def test_str_returns_name(self, research_group):
        """__str__ returns the group name."""
        assert str(research_group) == "Test Group"

    @pytest.mark.django_db
    def test_code_saved_uppercase(self):
        """ResearchGroup code is converted to uppercase on save."""
        from accounts.models import ResearchGroup

        group = ResearchGroup.objects.create(code="lower", name="Lowercase Code Group")
        assert group.code == "LOWER"

    @pytest.mark.django_db
    def test_unique_name_constraint(self, research_group):
        """Creating a second ResearchGroup with the same name raises an error."""
        from accounts.models import ResearchGroup
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            ResearchGroup.objects.create(code="TST2", name="Test Group")


class TestAccount:
    """Tests for the Account model."""

    @pytest.mark.django_db
    def test_create_regular_user(self, regular_user):
        """Creating a regular user persists it to the database."""
        from accounts.models import Account

        assert Account.objects.filter(username="testuser").exists()

    @pytest.mark.django_db
    def test_str_representation(self, regular_user):
        """__str__ returns 'LastName, FirstName (username)'."""
        assert str(regular_user) == "User, Test (testuser)"

    @pytest.mark.django_db
    def test_display_name(self, regular_user):
        """display_name returns 'FirstName LastName'."""
        assert regular_user.display_name == "Test User"

    @pytest.mark.django_db
    def test_initials_from_email_with_dots(self):
        """initials are derived from dot-separated email username."""
        from accounts.models import Account

        user = Account.objects.create_user(
            username="j.smith",
            email="j.smith@example.com",
            password="pw",
            first_name="John",
            last_name="Smith",
        )
        assert user.initials == "JS"

    @pytest.mark.django_db
    def test_initials_from_name_without_dots(self):
        """initials fall back to first/last name when email has no dots."""
        from accounts.models import Account

        user = Account.objects.create_user(
            username="jsmith",
            email="jsmith@example.com",
            password="pw",
            first_name="John",
            last_name="Smith",
        )
        assert user.initials == "JS"

    @pytest.mark.django_db
    def test_is_supervisor_false_when_no_managed_accounts(self, regular_user):
        """is_supervisor returns False when the account manages no other accounts."""
        assert regular_user.is_supervisor is False

    @pytest.mark.django_db
    def test_is_supervisor_true_when_managing(self, regular_user, superuser):
        """is_supervisor returns True when the account manages at least one other."""
        from accounts.models import Account

        Account.objects.filter(pk=regular_user.pk).update(manager=superuser)
        superuser.refresh_from_db()
        assert superuser.is_supervisor is True

    @pytest.mark.django_db
    def test_is_member_with_group_name(self, regular_user):
        """is_member returns True when user belongs to the named group."""
        group = Group.objects.create(name="Testers")
        regular_user.groups.add(group)
        assert regular_user.is_member("Testers") is True

    @pytest.mark.django_db
    def test_is_member_false_when_not_in_group(self, regular_user):
        """is_member returns False when user does not belong to the named group."""
        assert regular_user.is_member("NonExistent") is False

    @pytest.mark.django_db
    def test_active_manager_returns_only_active(self, regular_user):
        """ActiveUsersManager returns only active users."""
        from accounts.models import Account

        inactive = Account.objects.create_user(
            username="inactive",
            email="inactive@example.com",
            password="pw",
            first_name="Inactive",
            last_name="User",
            is_active=False,
        )
        active_users = Account.active.all()
        assert regular_user in active_users
        assert inactive not in active_users

    @pytest.mark.django_db
    def test_default_project_none_when_no_projects(self, regular_user):
        """default_project returns None when no projects are assigned."""
        assert regular_user.default_project is None

    @pytest.mark.django_db
    def test_primary_project_returns_first(self, regular_user, cost_centre):
        """primary_project returns the first assigned cost centre."""
        regular_user.project.add(cost_centre)
        assert regular_user.primary_project == cost_centre


class TestRole:
    """Tests for the Role model."""

    @pytest.mark.django_db
    def test_create_role(self, role_trainee):
        """Creating a Role persists it to the database."""
        from accounts.models import Role

        assert Role.objects.filter(name="Trainee").exists()

    @pytest.mark.django_db
    def test_str_returns_name(self, role_trainee):
        """__str__ returns the role name."""
        assert str(role_trainee) == "Trainee"

    @pytest.mark.django_db
    def test_trainee_classproperty(self, role_trainee):
        """Role.trainee classproperty returns the level-0 role."""
        from accounts.models import Role

        assert Role.trainee == role_trainee

    @pytest.mark.django_db
    def test_user_classproperty(self, role_user):
        """Role.user classproperty returns the level-100 role."""
        from accounts.models import Role

        assert Role.user == role_user
