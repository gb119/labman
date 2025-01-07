# -*- coding: utf-8 -*-
"""
Models for the bookings app to handle bokking entries and booking policies.
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
from accounts.models import Account, Project, Role
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
    """Catchall exception for booking problems."""


class PolicyDoesNotApply(BookingError):
    """Subclass of ValidationError to signal that the booking policy is not applicable here."""


class PolicyNotFound(BookingError):
    """Subclass of ValidationError to signal that no booking policy for this user/equipment can be found."""


class UserBookingHeld(BookingError):
    """Subclass of ValidationError to signal that bookings are held by a user-clearanle status."""


class BookingPolicy(NamedObject):
    """Represent a policy about booking equipment."""

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
        """Returns True if booking policy applies for this user/equipment."""
        role = booking.user_role
        if getattr(booking, "booker", None) is None or booking.booker.is_superuser:
            return role and role.level >= self.for_role.level
        booker_role = booking.booker_role
        return (
            role and role.level >= self.for_role.level and booker_role and booker_role.level >= self.booker_role.level
        )

    def rationalise(self, booking):
        """Apply quantisation to the booking."""
        return booking.rationalise(self)

    def quantise(self, booking):
        """Return start and end times that are quantised according to this policy."""
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
        """Return new start and end datetimes that fit shifts or quantise the booking."""
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
        """Returns True is the booking is permitted under the current policy."""
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

        Args:
            booking (BookingEntry):
                The potential bookingentry being considered.

        Keyword Args:
            no_holds (book :True):
                Do not consider user or admin holds - e.g. for deleting bookings.

        Returns:
            (BookingPolicy):
                The effective boooking policy to use.

        Raises:
            UserBookingHeld - raised if either user.hold or admin.hold is set and no_holds is not.
            PolicyNotFoind - if no applicable policy can be found.
        """
        if booking.user_hold and not no_holds:
            raise UserBookingHeld(
                f"Bookings for {booking.user} or {booking.equipment} are blocked - user action required"
            )

        if booking.admin_hold:
            raise UserBookingHeld(f"Bookings for {booking.user} or {booking.equipment} are blocked by the Admin")

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


class BookingEntry(models.Model):
    """Represent a single booking entry for a user against an equipment item."""

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
    project = models.ForeignKey(Project, on_delete=models.PROTECT, blank=True)

    def __str__(self):
        return f"{self.user.display_name} on {self.equipment.name} @ {self.slot}"

    @property
    def duration(self) -> td:
        """Return the time duration of the booking slot."""
        return self.slot.upper - self.slot.lower

    @property
    def booker_role(self):
        """Get the role of the specified user on this equipment - returns None if not on the userlist."""
        if self.equipment.users.filter(user=self.booker).count() == 0:
            return None
        return self.equipment.users.get(user=self.booker).role

    @property
    def user_role(self):
        """Get the role of the specified user on this equipment - returns None if not on the userlist."""
        if self.equipment.users.filter(user=self.user).count() == 0:
            return None
        return self.equipment.users.get(user=self.user).role

    @property
    def calendar_css(self):
        """Get CSS classes to use in the calendar."""
        if self.user_role:
            return self.user_role.css
        return "bg-gradient bg-danger text-white"

    @property
    def user_hold(self):
        """Get the user hold status of the userlist entry."""
        if self.equipment.users.filter(user=self.user).count() == 0:
            return True
        return self.equipment.users.get(user=self.user).hold

    @property
    def admin_hold(self):
        """Get the user hold status of the userlist entry."""
        if self.equipment.users.filter(user=self.user).count() == 0:
            return True
        return self.equipment.users.get(user=self.user).admin_hold

    @property
    def policy(self):
        """Return the effective policy for this booking."""
        try:
            return BookingPolicy.get_policy(self)
        except PolicyNotFound:
            return "Unable to ddetermin effective policy"
        except UserBookingHeld:
            if self.user.username == "service":
                return "System Booked for Service"
            return "User Bookings are currently blocked."

    def rationalise(self, policy):
        """Apply quantisation to the booking."""
        if self.slot.isempty or policy is None:  # Bugout for the empty slot or no policy
            return self
        start, end = policy.fix_times(self)
        self.slot = DateTimeTZRange(start, end)
        return self

    def fix_project(self):
        """Workout a project for this booking."""
        if self.user.project.count() == 0:
            return None
        if not hasattr(self, "project"):
            self.project = self.user.default_project
        if self.project not in self.user.project.all() and not self.user.is_superuser:
            return self.user.default_project

    def clean(self):
        """Rearrange the slot and check for conflicts."""
        self.fix_project()
        # Swap start and end times to ensure positive duration
        if not self.slot.isempty and self.slot.lower > self.slot.upper:
            self.slot = DateTimeTZRange(self.slot.upper, self.slot.lower)
        if not self.slot.isempty and self.user.username != "service":  # Can't do the custom cleaning if slot is blank
            policy = BookingPolicy.get_policy(self)
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
        elif self.user.username == "service":  # Special case, service user always booked!
            pass
        else:
            raise ValidationError("No booking slot defined!")
        return super().clean()

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """Force model.clean to be called."""
        self.clean()
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def delete(self, using=None, keep_parents=False, force=True):
        """Check whether we can delete this object."""
        if force:
            return super().delete(using=using, keep_parents=keep_parents)
        policy = BookingPolicy.get_policy(self, no_holds=True)
        return super().delete(using=using, keep_parents=keep_parents)
