# -*- coding: utf-8 -*-
"""Tests for the equipment app.

This module tests the Location, Shift, and Equipment models, including
hierarchical location structure, shift duration calculations, and equipment
properties such as bookability and URL generation.
"""
# Python imports
from datetime import time, timedelta

# Django imports
import pytest


class TestLocation:
    """Tests for the Location model."""

    @pytest.mark.django_db
    def test_create_top_level_location(self, location):
        """Creating a top-level Location persists it without a parent."""
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
        from equipment.models import Location
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            Location.objects.create(name="Test Lab")


class TestShift:
    """Tests for the Shift model."""

    @pytest.mark.django_db
    def test_create_shift(self, shift):
        """Creating a Shift persists it to the database."""
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
        from equipment.models import Shift

        night_shift = Shift.objects.create(name="Night Shift", start_time=time(22, 0), end_time=time(6, 0))
        assert night_shift.duration == timedelta(hours=8)


class TestEquipment:
    """Tests for the Equipment model."""

    @pytest.mark.django_db
    def test_create_equipment(self, equipment):
        """Creating Equipment persists it to the database."""
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
        from bookings.models import BookingPolicy
        from accounts.models import Role

        role, _ = Role.objects.get_or_create(name="Trainee", defaults={"level": 0})
        policy = BookingPolicy.objects.create(name="Test Policy", for_role=role, booker_role=role)
        equipment.policies.add(policy)
        equipment.offline = True
        equipment.save()
        assert equipment.bookable is False

    @pytest.mark.django_db
    def test_bookable_with_policy_and_online(self, equipment, db):
        """bookable returns True when policies exist and equipment is online."""
        from bookings.models import BookingPolicy
        from accounts.models import Role

        role, _ = Role.objects.get_or_create(name="Trainee", defaults={"level": 0})
        policy = BookingPolicy.objects.create(name="Test Policy 2", for_role=role, booker_role=role)
        equipment.policies.add(policy)
        assert equipment.bookable is True

    @pytest.mark.django_db
    def test_schedule_url(self, equipment):
        """schedule property returns a URL containing the equipment pk."""
        assert str(equipment.pk) in equipment.schedule
        assert "/bookings/cal/" in equipment.schedule
