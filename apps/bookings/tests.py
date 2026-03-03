# -*- coding: utf-8 -*-
"""Tests for the bookings app.

This module tests the BookingPolicy and BookingEntry models including
policy creation, string representations, and exception class hierarchy,
as well as the bookings views.
"""
# Python imports
from datetime import time, timedelta

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
        """BookingError inherits from ValidationError."""
        # Django imports
        from django.core.exceptions import ValidationError

        # external imports
        from bookings.models import BookingError

        err = BookingError("test error")
        assert isinstance(err, ValidationError)

    def test_policy_does_not_apply_is_booking_error(self):
        """PolicyDoesNotApply inherits from BookingError."""
        # external imports
        from bookings.models import BookingError, PolicyDoesNotApply

        err = PolicyDoesNotApply("not applicable")
        assert isinstance(err, BookingError)

    def test_policy_not_found_is_booking_error(self):
        """PolicyNotFound inherits from BookingError."""
        # external imports
        from bookings.models import BookingError, PolicyNotFound

        err = PolicyNotFound("not found")
        assert isinstance(err, BookingError)

    def test_user_booking_held_is_booking_error(self):
        """UserBookingHeld inherits from BookingError."""
        # external imports
        from bookings.models import BookingError, UserBookingHeld

        err = UserBookingHeld("user held")
        assert isinstance(err, BookingError)

    def test_admin_booking_held_is_booking_error(self):
        """AdminBookingHeld inherits from BookingError."""
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
        assert "/login" in response["Location"]

    @pytest.mark.django_db
    def test_calendar_view_returns_200(self, client_logged_in, equipment):
        """CalendarView returns 200 for an authenticated user."""
        url = reverse("bookings:equipment_calendar", kwargs={"equipment": equipment.pk, "date": 20240101})
        response = client_logged_in.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_calendar_view_context_contains_equipment(self, client_logged_in, equipment):
        """CalendarView places the equipment object into context."""
        url = reverse("bookings:equipment_calendar", kwargs={"equipment": equipment.pk, "date": 20240101})
        response = client_logged_in.get(url)
        assert response.context["equipment"] == equipment

    @pytest.mark.django_db
    def test_all_calendar_view_requires_login(self, client):
        """Unauthenticated requests to AllCalendarView redirect to login."""
        url = reverse("bookings:all_equipment_calendar")
        response = client.get(url)
        assert response.status_code in (302, 301)
        assert "/login" in response["Location"]

    @pytest.mark.django_db
    def test_all_calendar_view_returns_200(self, client_logged_in, equipment):
        """AllCalendarView returns 200 for an authenticated user."""
        url = reverse("bookings:all_equipment_calendar")
        response = client_logged_in.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_booking_records_view_requires_login(self, client):
        """Unauthenticated requests to BookingRecordsView redirect to login."""
        url = reverse("bookings:reporting")
        response = client.get(url)
        assert response.status_code in (302, 301)
        assert "/login" in response["Location"]

    @pytest.mark.django_db
    def test_booking_records_view_returns_200(self, client_logged_in):
        """BookingRecordsView returns 200 for an authenticated user."""
        url = reverse("bookings:reporting")
        response = client_logged_in.get(url)
        assert response.status_code == 200
