# -*- coding: utf-8 -*-
"""Tests for the bookings app.

This module tests the BookingPolicy and BookingEntry models including
policy creation, string representations, and exception class hierarchy,
as well as the bookings views.
"""
# Python imports
from datetime import time, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Django imports
from django.urls import reverse

# external imports
import pytest


class TestBookingPolicy:
    """Tests for the BookingPolicy model."""

    @pytest.fixture
    def booking_policy(self, db, role_trainee):
        """Create and return a basic BookingPolicy for testing.

        Args:
            db: pytest-django database fixture.
            role_trainee (Role): The role to use for for_role and booker_role.

        Returns:
            (BookingPolicy): A saved BookingPolicy named 'Test Policy'.

        """
        # external imports
        from bookings.models import BookingPolicy

        return BookingPolicy.objects.create(
            name="Test Policy",
            for_role=role_trainee,
            booker_role=role_trainee,
        )

    @pytest.mark.django_db
    def test_create_booking_policy(self, booking_policy):
        """Creating a BookingPolicy persists it to the database."""
        # external imports
        from bookings.models import BookingPolicy

        assert BookingPolicy.objects.filter(name="Test Policy").exists()

    @pytest.mark.django_db
    def test_default_weekdays_all_true(self, booking_policy):
        """All weekday fields default to True."""
        assert booking_policy.mondays is True
        assert booking_policy.tuesdays is True
        assert booking_policy.wednesdays is True
        assert booking_policy.thursdays is True
        assert booking_policy.fridays is True
        assert booking_policy.saturdays is True
        assert booking_policy.sundays is True

    @pytest.mark.django_db
    def test_default_start_end_times(self, booking_policy):
        """Default start_time is 09:00 and end_time is 18:00."""
        assert booking_policy.start_time == time(9, 0)
        assert booking_policy.end_time == time(18, 0)

    @pytest.mark.django_db
    def test_default_quantisation(self, booking_policy):
        """Default quantisation is 3 hours."""
        assert booking_policy.quantisation == timedelta(hours=3)

    @pytest.mark.django_db
    def test_default_use_shifts_true(self, booking_policy):
        """use_shifts defaults to True."""
        assert booking_policy.use_shifts is True


class TestBookingExceptions:
    """Tests for the booking exception class hierarchy."""

    def test_booking_error_is_validation_error(self):
        """Verify that BookingError inherits from ValidationError."""
        # Django imports
        from django.core.exceptions import ValidationError

        # external imports
        from bookings.models import BookingError

        err = BookingError("test error")
        assert isinstance(err, ValidationError)

    def test_policy_does_not_apply_is_booking_error(self):
        """Verify that PolicyDoesNotApply inherits from BookingError."""
        # external imports
        from bookings.models import BookingError, PolicyDoesNotApply

        err = PolicyDoesNotApply("not applicable")
        assert isinstance(err, BookingError)

    def test_policy_not_found_is_booking_error(self):
        """Verify that PolicyNotFound inherits from BookingError."""
        # external imports
        from bookings.models import BookingError, PolicyNotFound

        err = PolicyNotFound("not found")
        assert isinstance(err, BookingError)

    def test_user_booking_held_is_booking_error(self):
        """Verify that UserBookingHeld inherits from BookingError."""
        # external imports
        from bookings.models import BookingError, UserBookingHeld

        err = UserBookingHeld("user held")
        assert isinstance(err, BookingError)

    def test_admin_booking_held_is_booking_error(self):
        """Verify that AdminBookingHeld inherits from BookingError."""
        # external imports
        from bookings.models import AdminBookingHeld, BookingError

        err = AdminBookingHeld("admin held")
        assert isinstance(err, BookingError)


class TestBookingViews:
    """Integration tests for bookings app views."""

    @pytest.mark.django_db
    def test_calendar_view_requires_login(self, client, equipment):
        """Unauthenticated requests to CalendarView redirect to login."""
        url = reverse("bookings:equipment_calendar", kwargs={"equipment": equipment.pk, "date": 20240101})
        response = client.get(url)
        assert response.status_code in (302, 301)
        assert response["Location"].startswith(f"{reverse('core_login')}?")

    @pytest.mark.django_db
    def test_calendar_view_returns_200(self, client_logged_in, equipment):
        """Verify that CalendarView returns 200 for an authenticated user."""
        url = reverse("bookings:equipment_calendar", kwargs={"equipment": equipment.pk, "date": 20240101})
        response = client_logged_in.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_calendar_view_context_contains_equipment(self, client_logged_in, equipment):
        """Verify that CalendarView places the equipment object into context."""
        url = reverse("bookings:equipment_calendar", kwargs={"equipment": equipment.pk, "date": 20240101})
        response = client_logged_in.get(url)
        assert response.context["equipment"] == equipment

    @pytest.mark.django_db
    def test_all_calendar_view_requires_login(self, client):
        """Unauthenticated requests to AllCalendarView redirect to login."""
        url = reverse("bookings:all_equipment_calendar")
        response = client.get(url)
        assert response.status_code in (302, 301)
        assert response["Location"].startswith(f"{reverse('core_login')}?")

    @pytest.mark.django_db
    def test_all_calendar_view_returns_200(self, client_logged_in, equipment):
        """Verify that AllCalendarView returns 200 for an authenticated user."""
        url = reverse("bookings:all_equipment_calendar")
        response = client_logged_in.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_category_calendar_populates_each_equipment(
        self,
        client_logged_in,
        equipment,
        role_trainee,
        shift,
    ):
        """The category calendar eagerly fills the table for every matching item."""
        # external imports
        from bookings.models import BookingPolicy

        policy = BookingPolicy.objects.create(
            name="Calendar policy",
            for_role=role_trainee,
            booker_role=role_trainee,
        )
        equipment.policies.add(policy)
        equipment.shifts.add(shift)
        url = reverse("bookings:equipment_calendar_cat", kwargs={"cat": equipment.category})

        with patch("bookings.views.CalTable.fill_entries", autospec=True, return_value=[]) as fill_entries:
            response = client_logged_in.get(url)

        assert response.status_code == 200
        fill_entries.assert_called_once()
        assert fill_entries.call_args.args[1] == equipment

    @pytest.mark.django_db
    def test_booking_records_view_requires_login(self, client):
        """Unauthenticated requests to BookingRecordsView redirect to login."""
        url = reverse("bookings:reporting")
        response = client.get(url)
        assert response.status_code in (302, 301)
        assert response["Location"].startswith(f"{reverse('core_login')}?")

    @pytest.mark.django_db
    def test_booking_records_view_returns_200(self, client_logged_in):
        """Verify that BookingRecordsView returns 200 for an authenticated user."""
        url = reverse("bookings:reporting")
        response = client_logged_in.get(url)
        assert response.status_code == 200

    def test_rejected_booking_delete_returns_not_modified(self):
        """A policy-rejected booking deletion is not reported as successful."""
        # external imports
        from bookings.models import BookingError
        from bookings.views import BookingDialog

        user = Mock()
        equipment = Mock(category="characterisation")
        equipment.can_edit.return_value = False
        booking = Mock(user=user, equipment=equipment)
        booking.delete.side_effect = BookingError("Deletion is not permitted")
        view = BookingDialog()
        view.request = SimpleNamespace(GET={"booking": "42"}, user=user)

        with patch("bookings.views.models.BookingEntry.objects.get", return_value=booking):
            response = view.htmx_delete_booking(view.request)

        assert response.status_code == 304
