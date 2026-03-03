# -*- coding: utf-8 -*-
"""Tests for the equipment app.

This module tests the Location, Shift, and Equipment models including
hierarchical location structure, shift duration calculations, and equipment
properties such as bookability and URL generation, as well as the equipment views.
"""
# Python imports
from datetime import time, timedelta

# Django imports
from django.urls import reverse

# external imports
import pytest


class TestLocation:
    """Tests for the Location model."""

    @pytest.mark.django_db
    def test_create_top_level_location(self, location):
        """Creating a top-level Location persists it without a parent."""
        # external imports
        from equipment.models import Location

        loc = Location.objects.get(name="Test Lab")
        assert loc.parent is None

    @pytest.mark.django_db
    def test_create_child_location(self, child_location, location):
        """Creating a child Location correctly links to its parent."""
        assert child_location.parent == location

    @pytest.mark.django_db
    def test_str_returns_name(self, location):
        """__str__ returns the location name."""
        assert str(location) == "Test Lab"

    @pytest.mark.django_db
    def test_url_property(self, location):
        """url property returns the correct detail URL."""
        expected = f"/equipment/location_detail/{location.pk}/"
        assert location.url == expected

    @pytest.mark.django_db
    def test_children_includes_descendants(self, location, child_location):
        """children property returns descendants including self."""
        children = list(location.children)
        assert child_location in children

    @pytest.mark.django_db
    def test_all_parents_includes_self_and_parent(self, child_location, location):
        """all_parents includes self and all ancestors."""
        parents = list(child_location.all_parents)
        assert location in parents
        assert child_location in parents

    @pytest.mark.django_db
    def test_unique_name_constraint(self, location):
        """Creating a second Location with the same name raises an error."""
        # Django imports
        from django.db import IntegrityError

        # external imports
        from equipment.models import Location

        with pytest.raises(IntegrityError):
            Location.objects.create(name="Test Lab")


class TestShift:
    """Tests for the Shift model."""

    @pytest.mark.django_db
    def test_create_shift(self, shift):
        """Creating a Shift persists it to the database."""
        # external imports
        from equipment.models import Shift

        assert Shift.objects.filter(name="Day Shift").exists()

    @pytest.mark.django_db
    def test_str_representation(self, shift):
        """__str__ returns name with start and end times."""
        assert "Day Shift" in str(shift)
        assert "09:00:00" in str(shift)
        assert "17:00:00" in str(shift)

    @pytest.mark.django_db
    def test_duration_standard_shift(self, shift):
        """duration returns 8 hours for a 09:00–17:00 shift."""
        assert shift.duration == timedelta(hours=8)

    @pytest.mark.django_db
    def test_duration_midnight_crossing_shift(self, db):
        """duration handles shifts that cross midnight correctly."""
        # external imports
        from equipment.models import Shift

        night_shift = Shift.objects.create(name="Night Shift", start_time=time(22, 0), end_time=time(6, 0))
        assert night_shift.duration == timedelta(hours=8)


class TestEquipment:
    """Tests for the Equipment model."""

    @pytest.mark.django_db
    def test_create_equipment(self, equipment):
        """Creating Equipment persists it to the database."""
        # external imports
        from equipment.models import Equipment

        assert Equipment.objects.filter(name="Test Instrument").exists()

    @pytest.mark.django_db
    def test_str_returns_name(self, equipment):
        """__str__ returns the equipment name."""
        assert str(equipment) == "Test Instrument"

    @pytest.mark.django_db
    def test_url_property(self, equipment):
        """url property returns the correct detail URL."""
        expected = f"/equipment/equipment_detail/{equipment.pk}/"
        assert equipment.url == expected

    @pytest.mark.django_db
    def test_not_bookable_without_policies(self, equipment):
        """bookable returns False when no booking policies are defined."""
        assert equipment.bookable is False

    @pytest.mark.django_db
    def test_not_bookable_when_offline(self, equipment, db):
        """bookable returns False when equipment is marked offline."""
        # external imports
        from accounts.models import Role
        from bookings.models import BookingPolicy

        role, _ = Role.objects.get_or_create(name="Trainee", defaults={"level": 0})
        policy = BookingPolicy.objects.create(name="Test Policy", for_role=role, booker_role=role)
        equipment.policies.add(policy)
        equipment.offline = True
        equipment.save()
        assert equipment.bookable is False

    @pytest.mark.django_db
    def test_bookable_with_policy_and_online(self, equipment, db):
        """bookable returns True when policies exist and equipment is online."""
        # external imports
        from accounts.models import Role
        from bookings.models import BookingPolicy

        role, _ = Role.objects.get_or_create(name="Trainee", defaults={"level": 0})
        policy = BookingPolicy.objects.create(name="Test Policy 2", for_role=role, booker_role=role)
        equipment.policies.add(policy)
        assert equipment.bookable is True

    @pytest.mark.django_db
    def test_schedule_url(self, equipment):
        """schedule property returns a URL containing the equipment pk."""
        assert str(equipment.pk) in equipment.schedule
        assert "/bookings/cal/" in equipment.schedule


class TestEquipmentViews:
    """Integration tests for equipment app views."""

    @pytest.mark.django_db
    def test_equipment_detail_view_requires_login(self, client, equipment):
        """Unauthenticated requests to EquipmentDetailView redirect to login."""
        url = reverse("equipment:equipment_detail", kwargs={"pk": equipment.pk})
        response = client.get(url)
        assert response.status_code in (302, 301)
        assert "/login" in response["Location"]

    @pytest.mark.django_db
    def test_equipment_detail_view_returns_200(self, client_logged_in, equipment):
        """EquipmentDetailView returns 200 for an authenticated user."""
        url = reverse("equipment:equipment_detail", kwargs={"pk": equipment.pk})
        response = client_logged_in.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_equipment_detail_view_context_contains_equipment(self, client_logged_in, equipment):
        """EquipmentDetailView places the equipment object into context."""
        url = reverse("equipment:equipment_detail", kwargs={"pk": equipment.pk})
        response = client_logged_in.get(url)
        assert response.context["equipment"] == equipment

    @pytest.mark.django_db
    def test_location_detail_view_requires_login(self, client, location):
        """Unauthenticated requests to LocationDetailView redirect to login."""
        url = reverse("equipment:location_detail", kwargs={"pk": location.pk})
        response = client.get(url)
        assert response.status_code in (302, 301)
        assert "/login" in response["Location"]

    @pytest.mark.django_db
    def test_location_detail_view_returns_200(self, client_logged_in, location):
        """LocationDetailView returns 200 for an authenticated user."""
        url = reverse("equipment:location_detail", kwargs={"pk": location.pk})
        response = client_logged_in.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_model_list_view_requires_login(self, client):
        """Unauthenticated requests to ModelListView redirect to login."""
        url = reverse("equipment:lists")
        response = client.get(url)
        assert response.status_code in (302, 301)
        assert "/login" in response["Location"]

    @pytest.mark.django_db
    def test_model_list_view_returns_200(self, client_logged_in):
        """ModelListView returns 200 for an authenticated user."""
        url = reverse("equipment:lists")
        response = client_logged_in.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_toggle_account_active_requires_superuser(self, client_logged_in, regular_user):
        """ToggleAccountActiveView redirects non-superusers."""
        url = reverse("equipment:toggle_account_active", kwargs={"pk": regular_user.pk})
        response = client_logged_in.post(url)
        assert response.status_code in (302, 301, 403)

    @pytest.mark.django_db
    def test_toggle_account_active_toggles_flag(self, client_superuser, regular_user):
        """ToggleAccountActiveView toggles the is_active flag for superusers."""
        url = reverse("equipment:toggle_account_active", kwargs={"pk": regular_user.pk})
        original_active = regular_user.is_active
        client_superuser.post(url)
        regular_user.refresh_from_db()
        assert regular_user.is_active is not original_active

    @pytest.mark.django_db
    def test_sign_off_view_requires_login(self, client, equipment):
        """SignOffFormSetView redirects unauthenticated users to login."""
        url = reverse("equipment:sign-off", kwargs={"equipment": equipment.pk})
        response = client.get(url)
        assert response.status_code in (302, 301)
        assert "/login" in response["Location"]

    @pytest.mark.django_db
    def test_sign_off_view_returns_200_for_authenticated_user(self, client_logged_in, equipment):
        """SignOffFormSetView returns 200 for an authenticated user."""
        url = reverse("equipment:sign-off", kwargs={"equipment": equipment.pk})
        response = client_logged_in.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_userlist_new_view_requires_login(self, client, equipment):
        """UserlisttDialog (new) redirects unauthenticated users to login."""
        url = reverse("equipment:userlist_new", kwargs={"equipment": equipment.pk})
        response = client.get(url)
        assert response.status_code in (302, 301)
        assert "/login" in response["Location"]

    @pytest.mark.django_db
    def test_userlist_new_view_returns_200_for_authenticated_user(self, client_logged_in, equipment):
        """UserlisttDialog (new) returns 200 for an authenticated user."""
        url = reverse("equipment:userlist_new", kwargs={"equipment": equipment.pk})
        response = client_logged_in.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_equipment_edit_view_requires_login(self, client, equipment):
        """EquipmentDialog (edit) redirects unauthenticated users to login."""
        url = reverse("equipment:edit_equipment", kwargs={"pk": equipment.pk})
        response = client.get(url)
        assert response.status_code in (302, 301)
        assert "/login" in response["Location"]

    @pytest.mark.django_db
    def test_equipment_edit_view_returns_200_for_authenticated_user(self, client_logged_in, equipment):
        """EquipmentDialog (edit) returns 200 for an authenticated user."""
        url = reverse("equipment:edit_equipment", kwargs={"pk": equipment.pk})
        response = client_logged_in.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_location_detail_view_context_contains_location(self, client_logged_in, location):
        """LocationDetailView places the location object into the template context."""
        url = reverse("equipment:location_detail", kwargs={"pk": location.pk})
        response = client_logged_in.get(url)
        assert response.status_code == 200
        assert response.context["location"] == location

    @pytest.mark.django_db
    def test_equipment_detail_htmx_tab_returns_200(self, client_logged_in, equipment):
        """EquipmentDetailView returns 200 for an HTMX request with a tab trigger."""
        url = reverse("equipment:equipment_detail", kwargs={"pk": equipment.pk})
        response = client_logged_in.get(
            url,
            HTTP_HX_REQUEST="true",
            HTTP_HX_TRIGGER_NAME="signofftab",
        )
        assert response.status_code == 200
