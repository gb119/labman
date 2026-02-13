# -*- coding: utf-8 -*-
"""Models for the bookings app to handle booking entries and booking policies.

This module provides Django models for managing equipment bookings in the lab management system.
It includes models for booking policies that define rules for who can book equipment and when,
as well as booking entries that represent actual equipment reservations. The module also defines
several exception classes for handling various booking-related error conditions.
"""
# Python imports
from datetime import date as date, datetime as dt, time, timedelta as td

# Django imports
import django.utils.timezone as tz
from django.conf import settings
from django.contrib.postgres.fields import DateTimeRangeField
from django.core.exceptions import ValidationError
from django.db import models

# external imports
import numpy as np
from accounts.models import Account, Role
from costings.models import ChargeableItgem
from equipment.models import Equipment
from labman_utils.models import (
    DEFAULT_TZ,
    NamedObject,
    delta_t,
    ensure_tz,
    replace_time,
)
from numpy import ceil
from psycopg2.extras import DateTimeTZRange
from pytz import timezone


class BookingError(ValidationError):
    """Catchall exception for booking problems.

    This is the base exception class for all booking-related errors in the system.
    It inherits from Django's ValidationError to integrate with Django's validation framework.
    """


class PolicyDoesNotApply(BookingError):
    """Subclass of ValidationError to signal that the booking policy is not applicable here.

    This exception is raised when a booking policy exists but does not apply to the specific
    booking being attempted, for example due to time restrictions, day restrictions, or
    user role restrictions.
    """


class PolicyNotFound(BookingError):
    """Subclass of ValidationError to signal that no booking policy for this user/equipment can be found.

    This exception is raised when no applicable booking policy can be located for a given
    combination of user, equipment, and booking time. This indicates that the booking cannot
    proceed because there are no rules that permit it.
    """


class UserBookingHeld(BookingError):
    """Subclass of ValidationError to signal that bookings are held by a user-clearable status.

    This exception is raised when a user attempts to make a booking but their booking
    privileges are held pending some user action, such as completing training or
    updating their account information.
    """


class AdminBookingHeld(BookingError):
    """Subclass of ValidationError to signal that bookings are held by an admin-clearable status.

    This exception is raised when a user attempts to make a booking but their booking
    privileges are administratively held, requiring admin intervention to resolve.
    """


class BookingPolicy(NamedObject):
    """Represent a policy about booking equipment.

    A BookingPolicy defines the rules and constraints for booking equipment. This includes
    which days and times bookings are allowed, time quantisation, booking quotas, and
    role-based permissions. Policies are applied based on both the user's role and the
    person making the booking (which may differ in proxy booking scenarios).

    Attributes:
        for_role (Role):
            The role that the equipment user must have for this policy to apply.
        booker_role (Role):
            The role that the person making the booking must have for this policy to apply.
        mondays (bool):
            Whether bookings are allowed on Mondays.
        tuesdays (bool):
            Whether bookings are allowed on Tuesdays.
        wednesdays (bool):
            Whether bookings are allowed on Wednesdays.
        thursdays (bool):
            Whether bookings are allowed on Thursdays.
        fridays (bool):
            Whether bookings are allowed on Fridays.
        saturdays (bool):
            Whether bookings are allowed on Saturdays.
        sundays (bool):
            Whether bookings are allowed on Sundays.
        start_time (time):
            The earliest time of day that bookings can start.
        end_time (time):
            The latest time of day that bookings can end.
        quantisation (timedelta):
            The time quantum to which bookings are rounded.
        immutable (timedelta):
            How far in advance a booking becomes immutable (cannot be changed).
        max_forward (timedelta):
            The maximum time in advance that bookings can be made.
        quota (timedelta):
            The maximum total booking time a user can have pending.
        use_shifts (bool):
            Whether to use shift-based booking or time-based quantisation.
    """

    class Meta:
        ordering = ["for_role"]
        verbose_name = "Booking Policy"
        verbose_name_plural = "Booking Policies"

    weekdays = ["mondays", "tuesdays", "wednesdays", "thursdays", "fridays", "saturdays", "sundays"]

    for_role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="booking_policies")
    booker_role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="booker_booking_policies")
    mondays = models.BooleanField(default=True)
    tuesdays = models.BooleanField(default=True)
    wednesdays = models.BooleanField(default=True)
    thursdays = models.BooleanField(default=True)
    fridays = models.BooleanField(default=True)
    saturdays = models.BooleanField(default=True)
    sundays = models.BooleanField(default=True)
    start_time = models.TimeField(default=time(9, 0))
    end_time = models.TimeField(default=time(18, 0))
    quantisation = models.DurationField(default=td(hours=3))
    immutable = models.DurationField(default=td(seconds=0), null=True, blank=True)
    max_forward = models.DurationField(default=td(hours=24 * 7), null=True, blank=True)
    quota = models.DurationField(default=td(hours=48), null=True, blank=True)
    use_shifts = models.BooleanField(default=True)

    def applies(self, booking):
        """Returns True if booking policy applies for this user/equipment.

        Args:
            booking (BookingEntry):
                The booking entry to check.

        Returns:
            (bool):
                True if this policy applies to the given booking based on user and booker roles.
        """
        role = booking.user_role
        if getattr(booking, "booker", None) is None or booking.booker.is_superuser:
            return role and role.level >= self.for_role.level
        booker_role = booking.booker_role
        return (
            role and role.level >= self.for_role.level and booker_role and booker_role.level >= self.booker_role.level
        )

    def rationalise(self, booking):
        """Apply quantisation to the booking.

        Args:
            booking (BookingEntry):
                The booking entry to rationalise.

        Returns:
            (BookingEntry):
                The rationalised booking entry with adjusted time slots.
        """
        return booking.rationalise(self)

    def quantise(self, booking):
        """Return start and end times that are quantised according to this policy.

        Applies time quantisation to round the booking start and end times to the nearest
        quantum as defined by the policy's quantisation field. Start times are rounded down
        and end times are rounded up to ensure the booking covers the requested period.

        Args:
            booking (BookingEntry):
                The booking entry whose times should be quantised.

        Returns:
            (tuple):
                A tuple of (start, end) datetime objects representing the quantised booking times.

        Notes:
            Times are quantised relative to the policy's start_time. For example, with a
            start_time of 09:00 and quantisation of 3 hours, valid times would be 09:00,
            12:00, 15:00, etc.
        """
        start, end = booking.slot.lower, booking.slot.upper
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone("Europe/London"))
            end = end.replace(tzinfo=timezone("Europe/London"))
        start = min(start, end)
        end = max(start, end)
        start_t = delta_t(start.time(), self.start_time).total_seconds()
        end_t = delta_t(end.time(), self.start_time).total_seconds()
        quanta = self.quantisation.total_seconds()
        self_start_secs = self.start_time.hour * 3600 + self.start_time.minute * 60 + self.start_time.second
        start_t = quanta * (start_t // quanta) + self_start_secs
        end_t = quanta * ceil(end_t / quanta) + self_start_secs
        start = replace_time(start, start_t)
        end = replace_time(end, end_t)
        return start, end

    def fix_times(self, booking):
        """Return new start and end datetimes that fit shifts or quantise the booking.

        If the policy uses shifts and the equipment has shift definitions, aligns the
        booking times to shift boundaries. Otherwise, applies time quantisation based
        on the policy's quantisation field.

        Args:
            booking (BookingEntry):
                The booking entry whose times should be fixed.

        Returns:
            (tuple):
                A tuple of (start, end) timezone-aware datetime objects representing the adjusted booking times.

        Notes:
            When using shifts, the start time is aligned to the start of the shift containing
            the requested start time, and the end time is aligned to the end of the shift
            containing the requested end time. Day boundaries are crossed if necessary.
        """
        start = booking.slot.lower + td(seconds=0.1)
        end = booking.slot.upper - td(seconds=0.1)

        if start_shift := booking.equipment.get_shift(start):
            if delta_t(start, start_shift.start_time).total_seconds() < 0:
                start -= td(days=1)
            start = dt.combine(start.date(), start_shift.start_time)

        if end_shift := booking.equipment.get_shift(end):
            if delta_t(end, end_shift.end_time).total_seconds() > 0:
                end += td(days=1)
            end = dt.combine(end.date(), end_shift.end_time)

        if start_shift is None or end_shift is None:  # quantise the times
            start, end = self.quantise(booking)
        return ensure_tz(start), ensure_tz(end)

    def permitted(self, booking):
        """Returns True if the booking is permitted under the current policy.

        Validates that the booking satisfies all policy constraints including time ranges,
        allowed days, immutability restrictions, forward booking limits, and quota limits.
        Superusers can bypass most restrictions.

        Args:
            booking (BookingEntry):
                The booking entry to validate.

        Returns:
            (bool):
                True if the booking is permitted under this policy.

        Raises:
            PolicyDoesNotApply:
                If the policy applies to the user/equipment but the specific booking
                violates one of the policy's constraints.

        Notes:
            This method fixes the booking times before validation and checks various
            conditions in sequence. The first violation encountered will raise an exception.
        """
        superuser = booking.booker.is_superuser
        if not self.applies(booking):  # Role doesn't apply
            raise PolicyDoesNotApply(f"This policy does not apply for {booking.user} or {booking.equipment}")

        # We need to fix the start and end times according to the policy before rationalising it
        start, end = self.fix_times(booking)

        if (
            not start.time() >= self.start_time and start.time() <= self.end_time
        ):  # Start time outside policy time range
            raise PolicyDoesNotApply(f"The start time {start.time()} does not fall within this policies range")

        start_day = self.weekdays[start.date().weekday()]
        if not getattr(self, start_day, False):  # Day outside policy day ranges
            raise PolicyDoesNotApply(f"The start day {start.date().strftime('%A')} is not covered by this policy")

        if not superuser and self.immutable and tz.now() - self.immutable > start:  # Booking outside immutable time
            raise PolicyDoesNotApply("Start time is blocked by booking immutable time")

        if not superuser and self.max_forward and tz.now() + self.max_forward < end:  # Booking  to far in advance
            raise PolicyDoesNotApply("End time is blocked by booking max_forward time")

        entries = BookingEntry.objects.filter(
            user=booking.user, equipment=booking.equipment, slot__fully_gt=DateTimeTZRange(tz.now(), tz.now())
        ).values_list("slot")
        total = np.sum([(x[0].upper - x[0].lower).total_seconds() for x in entries])

        if not superuser and self.quota and total > self.quota.total_seconds():  # Too much time booked already
            raise PolicyDoesNotApply("Too much time {total[0]['total']} already booked.")

        return True

    @classmethod
    def get_policy(cls, booking, no_holds=False):
        """Try to locate the relevant booking policy for this booking.

        Iterates through all policies associated with the equipment and returns the first
        policy that both applies to and permits the booking. Checks user and admin hold
        statuses unless explicitly bypassed.

        Args:
            booking (BookingEntry):
                The potential booking entry being considered.

        Keyword Parameters:
            no_holds (bool):
                Do not consider user or admin holds, e.g. for deleting bookings. Default is False.

        Returns:
            (BookingPolicy):
                The effective booking policy to use, or None if the booker is a superuser
                and no policy applies.

        Raises:
            UserBookingHeld:
                If the user's booking privileges are held pending user action and no_holds is False.
            AdminBookingHeld:
                If the user's booking privileges are administratively held and no_holds is False.
            PolicyNotFound:
                If no applicable policy can be found for this booking.

        Notes:
            Superusers are allowed to make bookings even when no policy applies, in which
            case this method returns None.
        """
        if booking.user_hold and not no_holds:
            raise UserBookingHeld(
                f"Bookings for {booking.user} or {booking.equipment} are blocked - user action required"
            )

        if booking.admin_hold and not no_holds:
            raise AdminBookingHeld(f"Bookings for {booking.user} or {booking.equipment} are blocked by the Admin")

        for policy in booking.equipment.policies.all():
            try:
                if policy.permitted(booking):
                    return policy
            except (PolicyDoesNotApply, PolicyNotFound):
                continue
        if booking.booker.is_superuser:  # Allow superusers to override policies
            return None
        raise PolicyNotFound(
            f"No policy permits booking of {booking.equipment} by {booking.user} at {booking.slot.lower}"
        )


class BookingEntry(ChargeableItgem):
    """Represent a single booking entry for a user against an equipment item.

    A BookingEntry records a reservation of equipment by a user for a specific time slot.
    Bookings are validated against booking policies and checked for conflicts with existing
    bookings. The system supports proxy bookings where one user makes a booking on behalf
    of another.

    Attributes:
        user (Account):
            The user for whom the equipment is booked.
        booker (Account):
            The user who made the booking (may differ from user in proxy bookings).
        equipment (Equipment):
            The equipment being booked.
        slot (DateTimeTZRange):
            The time range for the booking, stored as a PostgreSQL range type.
        shifts (float):
            The number of shifts covered by this booking, used for charging calculations.
    """

    class Meta:
        ordering = ["equipment", "slot"]
        verbose_name = "Booking Slot"
        verbose_name_plural = "Booking Slots"

    user = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="bookings")
    booker = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.SET_NULL, related_name="proxy_bookings"
    )
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name="bookings")
    slot = DateTimeRangeField(default_bounds="[)")
    shifts = models.FloatField(
        default=1.0,
    )

    def __str__(self):
        return f"{self.user.display_name} on {self.equipment.name} @ {self.slot}"

    @property
    def duration(self) -> td:
        """Return the time duration of the booking slot.

        Returns:
            (timedelta):
                The duration of the booking as a timedelta object.
        """
        return self.slot.upper - self.slot.lower

    @property
    def booker_role(self):
        """Get the role of the person making the booking on this equipment.

        Returns:
            (Role):
                The role of the booker on this equipment's userlist, or None if they are not on the userlist.
        """
        if self.equipment.userlist.filter(user=self.booker).count() == 0:
            return None
        return self.equipment.userlist.get(user=self.booker).role

    @property
    def user_role(self):
        """Get the role of the user for whom the booking is made on this equipment.

        Returns:
            (Role):
                The role of the user on this equipment's userlist, or None if they are not on the userlist.
        """
        if self.equipment.userlist.filter(user=self.user).count() == 0:
            return None
        return self.equipment.userlist.get(user=self.user).role

    @property
    def calendar_css(self):
        """Get CSS classes to use in the calendar display.

        Returns:
            (str):
                CSS class string for styling this booking in calendar views, based on the user's role
                or a default danger style if the user has no role.
        """
        if self.user_role:
            return self.user_role.css
        return "bg-gradient bg-danger text-white"

    @property
    def user_hold(self):
        """Get the user hold status of the userlist entry.

        Returns:
            (bool):
                True if the user's bookings are held pending user action, or if the user is not
                on the equipment's userlist.
        """
        if self.equipment.userlist.filter(user=self.user).count() == 0:
            return True
        return self.equipment.userlist.get(user=self.user).hold

    @property
    def admin_hold(self):
        """Get the admin hold status of the userlist entry.

        Returns:
            (bool):
                True if the user's bookings are administratively held, or if the user is not
                on the equipment's userlist.
        """
        if self.equipment.userlist.filter(user=self.user).count() == 0:
            return True
        return self.equipment.userlist.get(user=self.user).admin_hold

    @property
    def policy(self):
        """Return the effective policy for this booking.

        Returns:
            (BookingPolicy):
                The booking policy that applies to this booking, or a string error message
                if no policy can be determined.
        """
        return self.get_policy()

    def calculate_charge(self):
        """Calculate the charge for this booking.

        Calculates the cost based on the number of shifts and the equipment's charge rate
        for the user. Updates the comment field with charge details.

        Returns:
            (float):
                The calculated charge for this booking in pounds sterling.

        Notes:
            The charge is calculated as shifts × charge_rate, where the charge rate depends
            on the user's cost rate category for this equipment.
        """
        charge_rate = self.equipment.get_charge_rate(self)
        self.comment = (
            f"{self.shifts} shifts @ £{charge_rate.charge_rate:.2f}/shift ({charge_rate.cost_rate.name} rate)"
        )
        return self.shifts * charge_rate.charge_rate
        return 0.0

    def get_default_cost_centre(self):
        """Get a default cost centre for this booking.

        Returns:
            (CostCentre):
                The default cost centre, currently always None.

        Notes:
            This is a placeholder for future implementation of automatic cost centre assignment.
        """
        return None

    def get_policy(self, no_holds=False):
        """Get the effective booking policy for this booking entry.

        Args:
            no_holds (bool):
                If True, ignore user and admin hold statuses. Default is False.

        Returns:
            (BookingPolicy):
                The applicable booking policy, or a string message describing why no policy
                could be determined.

        Notes:
            This method wraps BookingPolicy.get_policy() and provides user-friendly error
            messages when exceptions occur.
        """
        try:
            return BookingPolicy.get_policy(self, no_holds)
        except PolicyNotFound:
            return "Unable to ddetermin effective policy"
        except UserBookingHeld:
            if self.user.username == "service":
                return "System Booked for Service"
            return "User Bookings are currently blocked."

    def rationalise(self, policy):
        """Apply quantisation to the booking.

        Adjusts the booking's time slot according to the policy's time-fixing rules,
        either aligning to shifts or applying time quantisation.

        Args:
            policy (BookingPolicy):
                The policy to use for rationalising the booking times.

        Returns:
            (BookingEntry):
                This booking entry with adjusted slot times.

        Notes:
            If the slot is empty or no policy is provided, returns the booking unchanged.
        """
        if self.slot.isempty or policy is None:  # Bugout for the empty slot or no policy
            return self
        start, end = policy.fix_times(self)
        self.slot = DateTimeTZRange(start, end)
        return self

    def fix_project(self):
        """Work out a cost centre for this booking.

        Ensures the booking has a valid cost centre assigned from the user's available
        projects. If no cost centre is set, uses the user's default project. If the
        current cost centre is not in the user's project list, reverts to the default.

        Returns:
            (CostCentre):
                The cost centre to use for this booking, or None if the user has no projects.
        """
        if self.user.project.count() == 0:
            return None
        if not hasattr(self, "cost_centre") or self.cost_centre is None:
            self.cost_centre = self.user.default_project
        if self.cost_centre not in self.user.project.all() and not self.user.is_superuser:
            return self.user.default_project

    def count_shifts(self):
        """Return a weighted sum of the number of shifts for this booking.

        Calculates the total weighted shift count by iterating through the equipment's
        shift schedule and summing the weightings of all shifts covered by the booking.

        Returns:
            (float):
                The weighted sum of shifts, or None if no policy can be determined.

        Notes:
            Each shift has a weighting factor that accounts for different shift durations
            or desirability. The total is used for calculating booking charges and quotas.
        """
        if not (policy := self.get_policy(no_holds=True)):
            return None
        start, end = policy.fix_times(self)
        end = end - td(seconds=0.1)  # knock the end back inside a shift
        start_shift = self.equipment.get_shift(start)
        shifts = [x for x in self.equipment.shifts.all()]
        ix = shifts.index(start_shift)
        current = start
        total = 0
        while (end - current).total_seconds() >= 0:
            current = current + shifts[ix].duration
            total += shifts[ix].weighting
            ix = (ix + 1) % len(shifts)
        return total

    def clean(self, no_holds=False):
        """Rearrange the slot and check for conflicts.

        Performs comprehensive validation of the booking including fixing the cost centre,
        ensuring positive duration, applying policy-based time adjustments, checking for
        scheduling conflicts, and calculating shift counts.

        Keyword Parameters:
            no_holds (bool):
                If True, ignore user and admin hold statuses during validation. Default is False.

        Raises:
            ValidationError:
                If the booking violates policy constraints, conflicts with existing bookings,
                or has no time slot defined.

        Notes:
            This method is automatically called by Django during model validation. It ensures
            that all booking constraints are satisfied before the booking is saved to the database.
            Service user bookings bypass most validation checks.
        """
        self.fix_project()
        # Swap start and end times to ensure positive duration
        if self.slot and not self.slot.isempty and self.slot.lower > self.slot.upper:
            self.slot = DateTimeTZRange(self.slot.upper, self.slot.lower)
        if (
            self.slot and not self.slot.isempty and self.user.username != "service"
        ):  # Can't do the custom cleaning if slot is blank
            policy = BookingPolicy.get_policy(self, no_holds=no_holds)
            self.rationalise(policy)
            if not self.booker.is_superuser and not policy.permitted(self):
                raise ValidationError("Booking is unable to be made after quantising the booking period")
            conflicts = BookingEntry.objects.filter(slot__overlap=self.slot, equipment=self.equipment).exclude(
                pk=self.pk
            )
            if conflicts.count() > 0:
                raise ValidationError(
                    "Unable to save the booking entry due to overlapping entry for the same equipment"
                )
            if policy:
                self.shifts = self.count_shifts()
        elif self.user and self.user.username == "service":  # Special case, service user always booked!
            pass
        else:
            raise ValidationError("No booking slot defined!")
        return super().clean()

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, force_clean=False):
        """Force model.clean to be called before saving.

        Keyword Parameters:
            force_insert (bool):
                Force an SQL INSERT operation. Default is False.
            force_update (bool):
                Force an SQL UPDATE operation. Default is False.
            using (str):
                Database alias to use for saving. Default is None (use default database).
            update_fields (list):
                List of field names to update. Default is None (update all fields).
            force_clean (bool):
                If not None, passed as no_holds parameter to clean(). Controls whether to
                bypass user and admin hold checks during validation.

        Notes:
            Django models do not automatically call clean() during save, so this override
            ensures validation always occurs.
        """
        if force_clean is not None:
            self.clean(no_holds=force_clean)
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def delete(self, using=None, keep_parents=False, force=True):
        """Check whether we can delete this object.

        Validates that the booking can be deleted according to policy rules before
        performing the deletion.

        Keyword Parameters:
            using (str):
                Database alias to use for deletion. Default is None (use default database).
            keep_parents (bool):
                Keep parent model instances when deleting. Default is False.
            force (bool):
                If False, check policy before deleting. If True, delete without policy checks.
                Default is True.

        Returns:
            (tuple):
                Django's standard deletion result tuple (number_deleted, deletion_details_dict).

        Notes:
            When force is False, retrieves the booking policy with no_holds=True to verify
            the deletion is permitted, though the current implementation always proceeds
            with deletion after policy retrieval.
        """
        if force:
            return super().delete(using=using, keep_parents=keep_parents)
        policy = BookingPolicy.get_policy(self, no_holds=True)
        return super().delete(using=using, keep_parents=keep_parents)
