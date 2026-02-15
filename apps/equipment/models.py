# -*- coding: utf-8 -*-
"""Equipment management models for laboratory resources.

This module provides Django models for managing laboratory equipment, including:
- Location: Physical locations and rooms with hierarchical organisation
- Equipment: Equipment items with booking capabilities and user management
- Shift: Time periods for equipment booking schedules
- UserListEntry: User permissions and roles for equipment access
- DocumentSignOff: User acknowledgements of safety and operational documents
- ChargingRate: Cost rates for equipment usage based on different cost centres

The models support complex workflows including equipment booking, user authorisation,
document management, and cost tracking for laboratory resources.
"""
# Python imports
from collections import defaultdict
from datetime import (
    date as Date,
    datetime as dt,
    time as Time,
    timedelta as td,
)

# Django imports
import django.utils.timezone as tz
from django.apps import apps
from django.contrib.flatpages.models import FlatPage
from django.contrib.postgres.fields import DateRangeField
from django.db import models
from django.db.models.constraints import CheckConstraint
from django.utils.text import slugify

# external imports
import numpy as np
import pytz
from accounts.models import Account
from costings.models import CostCentre, CostRate
from labman_utils.models import (
    DEFAULT_TZ,
    Document,
    NamedObject,
    ResourceedObject,
    delta_t,
    patch_model,
)
from mptt.models import MPTTModel, TreeForeignKey
from psycopg2.extras import DateRange
from sortedm2m.fields import SortedManyToManyField


class Location(MPTTModel, ResourceedObject):
    """Represents a physical location or room in a hierarchical structure.

    Locations can be nested to represent building/room/sub-location hierarchies.
    Uses django-mptt for efficient hierarchical queries and tree management.

    Attributes:
        parent (Location or None):
            Parent location containing this location, or None for top-level locations.
    """

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name"], name="Unique Location Name"),
        ]
        ordering = ["tree_id", "lft"]

    class MPTTMeta:
        order_insertion_by = ["name"]

    parent = TreeForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="direct_children"
    )

    @property
    def all_parents(self):
        """Retrieve all parent locations containing this location.

        Returns the location hierarchy from the top-level location down to
        this location, including self.

        Returns:
            (QuerySet):
                QuerySet of Location objects representing this location and all parents.
        """
        # Use MPTT get_ancestors with include_self=True
        return self.get_ancestors(include_self=True)

    @property
    def children(self):
        """Retrieve all sub-locations contained within this location.

        Returns this location and all descendant locations at any depth in the
        hierarchy. This property returns a QuerySet that can be iterated directly
        in templates without calling .all().

        Returns:
            (QuerySet):
                QuerySet of Location objects representing this location and all descendants.
                Can be used directly in templates: {% for loc in location.children %}
        
        Notes:
            This returns all descendants including self via MPTT's get_descendants().
            For direct children only, access the reverse relation via
            `self.direct_children.all()`.
        """
        # Use MPTT get_descendants with include_self=True
        return self.get_descendants(include_self=True)

    @property
    def all_files(self):
        """Retrieve all files attached to this location and its parents.

        Returns:
            (QuerySet):
                QuerySet of Document objects associated with this location or any parent.
        """
        Document = apps.get_model("labman_utils", "document")
        return Document.objects.filter(location__in=self.all_parents)

    @property
    def all_photos(self):
        """Retrieve all photos attached to this location and its parents.

        Returns:
            (QuerySet):
                QuerySet of photo Document objects associated with this location or any parent.
        """
        Photo = apps.get_model("photologue", "photo")
        return Photo.objects.filter(location__in=self.all_parents)

    @property
    def all_pages(self):
        """Retrieve all pages attached to this location and its parents.

        Returns:
            (QuerySet):
                QuerySet of page Document objects associated with this location or any parent.
        """
        FlatPage = apps.get_model("flatpages", "flatpage")
        return FlatPage.objects.filter(location__in=self.all_parents)

    @property
    def url(self):
        """Generate the URL for the location detail page.

        Returns:
            (str):
                URL path to the location detail view.
        """
        return f"/equipment/location_detail/{self.pk}/"


class Shift(NamedObject):
    """Represents a time period for equipment booking slots.

    Shifts define time windows during which equipment can be booked, with configurable
    start and end times. They can span midnight and include a weighting factor for
    cost calculations.

    Attributes:
        start_time (time):
            Time when the shift begins. Default is 09:00.
        end_time (time):
            Time when the shift ends. Default is 18:00. May be before start_time for
            shifts spanning midnight.
        weighting (float):
            Multiplier for cost calculations. Default is 1.0.
    """

    class Meta:
        verbose_name_plural = "Booking Shifts"
        verbose_name = "Booking Shift"
        ordering = ["start_time"]

    start_time = models.TimeField(default=Time(9, 0))
    end_time = models.TimeField(default=Time(18, 0))
    weighting = models.FloatField(default=1.0)

    def __str__(self):
        return f"{self.name} {self.start_time}-{self.end_time}"

    @property
    def duration(self):
        """Calculate the duration of the shift, handling midnight crossover.

        If the end time is before the start time, the shift is assumed to span
        midnight and the duration includes the next day.

        Returns:
            (timedelta):
                The duration of the shift.
        """
        if (dt.combine(dt.today(), self.end_time) - dt.combine(dt.today(), self.start_time)).total_seconds() > 0:
            return dt.combine(dt.today(), self.end_time) - dt.combine(dt.today(), self.start_time)
        else:
            return dt.combine(dt.today(), self.end_time) - dt.combine(dt.today(), self.start_time) + td(days=1)


class Equipment(ResourceedObject):
    """Class for representing an Equipment item."""

    CATEGORIES = {
        "deposition": "Thin film growth",
        "characterisation": "Material Characterisation",
        "magnetometer": "Magnetic Characterisation",
        "cryostat": "Cryostat",
        "transport": "Electrical Transport",
        "furnace": "Furnace",
        "other": "Other",
    }

    class Meta:
        verbose_name_plural = "Equipment Items"
        verbose_name = "Equipment Item"
        constraints = [models.UniqueConstraint(fields=["name"], name="Unique Equipment Name")]

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="equipment")
    owner = models.ForeignKey("accounts.Account", on_delete=models.CASCADE, related_name="equipment")
    shifts = SortedManyToManyField(Shift, related_name="equipment", blank=True)
    policies = SortedManyToManyField("bookings.BookingPolicy", related_name="equipment", blank=True)
    offline = models.BooleanField(default=False)
    category = models.CharField(max_length=20, null=True, blank=True, choices=list(CATEGORIES.items()))
    users = models.ManyToManyField("accounts.Account", related_name="user_of", through="equipment.UserListEntry")

    def __str__(self):
        return f"{self.name}"

    @property
    def bookable(self):
        """Determine whether the equipment is currently available for booking.

        Equipment is bookable if it has at least one policy defined and is not
        marked as offline.

        Returns:
            (bool):
                True if the equipment can be booked, False otherwise.
        """
        return self.policies.count() > 0 and not self.offline

    @property
    def url(self):
        """Generate the URL for the equipment detail page.

        Returns:
            (str):
                URL path to the equipment detail view.
        """
        return f"/equipment/equipment_detail/{self.pk}/"

    @property
    def schedule(self):
        """Generate the URL for the equipment booking calendar.

        Returns:
            (str):
                URL path to the booking calendar view for today's date.
        """
        date = tz.now().strftime("%Y%m%d")

        return f"/bookings/cal/{self.id}/{date}/"

    @property
    def calendar_time_vector(self):
        """Generate a list of shift start times for calendar construction.

        Returns:
            (list or None):
                List of time objects representing shift start times, or None if no shifts defined.
        """
        if self.shifts.all().count() == 0:
            return None
        # Got some shifts
        ret = []
        for shift in self.shifts.all():
            ret.append(shift.start_time)
        return ret

    @property
    def userlist_dict(self):
        """Retrieve the equipment user list organised by role.

        Returns:
            (dict):
                Dictionary mapping role names (str) to lists of UserListEntry objects.
                Roles are ordered by level (highest first). Users without assigned roles
                are excluded from the results.

        Notes:
            This method groups users in Python rather than using database filtering
            to avoid N+1 queries. The return type changed from QuerySets to lists
            in optimization efforts.

            The queryset is evaluated to a list to ensure prefetch_related works
            correctly and to enable grouping. For equipment with very large userlists
            (1000+ entries), consider implementing pagination or lazy loading.
        """
        # Fetch all users once with role prefetched to avoid N+1 queries
        # Order by role level first, then prefetch role data
        # list() is necessary to materialize the queryset with prefetch_related
        users_list = list(self.userlist.order_by("-role__level").all().prefetch_related("role"))

        # Group users by role in Python to avoid repeated database queries
        ret = defaultdict(list)
        for user in users_list:
            if user.role:  # Skip users without assigned roles
                ret[user.role.name].append(user)

        return dict(ret)

    @property
    def default_charge_rate(self):
        """Retrieve or create the default charging rate for this equipment.

        Returns:
            (ChargingRate):
                The ChargingRate object using the default cost rate.
        """
        return self.charge_rates.get_or_create(cost_rate=CostRate.default())[0]

    def __getattr__(self, name):
        """Dynamically resolve role-based user queries and document categories.

        Enables access to users with specific roles (e.g., equipment.manager) and
        document categories (e.g., equipment.sops, equipment.ras) as attributes.

        Args:
            name (str):
                Attribute name to resolve. Can be a role name or document category plural.

        Returns:
            (QuerySet):
                QuerySet of Account objects for roles, or Document objects for file categories.

        Raises:
            AttributeError:
                If the name cannot be resolved to a role or document category.
        """
        Role = apps.get_model(app_label="accounts", model_name="role")

        try:
            role = Role.objects.get(name__iexact=name)
            data = self.userlist.filter(role__level__gte=role.level)
            return Account.objects.filter(equipmentlist__in=data)
        except Role.DoesNotExist:
            pass
        if name in [f"{x}s" for x in Document.CATAGORIES_DICT.keys()] + ["all_files"]:
            category = name[:-1]
        else:
            return self.__getattribute__(name)
        if category == "all_file":
            my_docs = models.Q(equipment=self)
            location_docs = models.Q(location__in=self.location.all_parents)
        else:
            my_docs = models.Q(category=category, equipment=self)
            location_docs = models.Q(category=category, location__in=self.location.all_parents)
        return (
            Document.objects.filter(my_docs | location_docs).order_by().order_by("title", "-version").distinct("title")
        )

    def get_shift(self, time):
        """Determine which shift contains the specified time.

        Identifies the appropriate Shift object based on whether the given time
        falls within any of the equipment's defined shifts, handling midnight
        crossover correctly.

        Args:
            time (datetime or time):
                The time to check. Can be a datetime object or time object.

        Returns:
            (Shift or None):
                The Shift object containing the specified time, or None if no match or no shifts defined.

        Raises:
            TypeError:
                If time is neither a datetime nor a time object.
        """
        if self.shifts.all().count() == 0:
            return None
        if isinstance(time, dt):
            time = time.time()
        elif not isinstance(time, Time):
            raise TypeError("Was expecting to get either a datetime or time object.")
        if delta_t(time, self.shifts.first().start_time).total_seconds() < 0:  # Booking from previous day
            time = dt.combine(dt.today(), time) + td(days=1)
        else:
            time = dt.combine(dt.today(), time)
        for shift in self.shifts.all():
            s = dt.combine(dt.today(), shift.start_time)
            e = dt.combine(dt.today(), shift.end_time)
            if (e - s).total_seconds() <= 0:
                e += td(days=1)
            if (time - s).total_seconds() >= 0 and (e - time).total_seconds() > 0:
                return shift
        return None

    def get_charge_rate(self, other):
        """Determine the applicable charging rate for a given entity.

        Matches the charging rate based on the cost centre associated with the entity
        and the relevant date. Falls back to the default cost rate if no specific
        match is found.

        Args:
            other (CostCentre, BookingEntry, Account, or object):
                Entity to determine charging rate for. Must have an associated cost centre
                or be a cost centre itself.

        Returns:
            (ChargingRate):
                The applicable ChargingRate object.

        Raises:
            TypeError:
                If a cost centre cannot be extracted from the provided object.
        """
        BookingEntry = self.bookings.model
        match other:
            case Account():
                charge_centre = other.default_project
                date = Date.today()
            case BookingEntry():
                charge_centre = other.cost_centre
                date = other.slot.lower.date()
            case CostCentre():
                charge_centre = other
                date = Date.today()
            case _:
                for attr in ["cost_centre", "project", "default_cost_centre", "default_project"]:
                    if charge_centre := getattr(other, attr, None):
                        break
                else:
                    raise TypeError(f"Can;'t get a cost centre from a {type(other)}")
                date = Date.today()

        try:
            return self.charge_rates.get(cost_rate=charge_centre.rate, dates__contains=date)
        except ChargingRate.DoesNotExist:
            pass
        try:
            return self.charge_rates.get(cost_rate=CostRate.default(), dates__contains=date)
        except ChargingRate.DoesNotExist:
            rate, _ = ChargingRate.objects.get_or_create(equipment=self, cost_rate=CostRate.default(), charge_rate=0)
            return rate

    def can_edit(self, target):
        """Check whether a user has permission to edit this equipment.

        Users can edit equipment if they are a superuser, the equipment owner,
        or have a manager role for the equipment.

        Args:
            target (Account):
                The user account to check permissions for.

        Returns:
            (bool):
                True if the user can edit the equipment, False otherwise.
        """
        return (target.is_superuser) or (self.owner == target) or (target in self.manager)


class UserListEntry(models.Model):
    """Represents a user's authorisation and role for a piece of equipment.

    Links users to equipment with specific roles and manages authorisation holds.
    Holds can be placed on users who have not yet signed off required documents
    or by administrators. The entry tracks when permissions were last updated.

    Attributes:
        equipment (Equipment):
            The equipment item this entry relates to.
        user (Account):
            The user account for this authorisation.
        role (Role or None):
            The user's role for this equipment (e.g., "user", "manager").
        hold (bool):
            Whether user clearance is pending document sign-off. Default is True.
        admin_hold (bool):
            Whether an administrative hold is in place. Default is False.
        updated (datetime):
            Timestamp of the last update to this entry. Updated automatically.
    """

    class Meta:
        ordering = ["equipment", "-role", "user"]
        unique_together = ["equipment", "user"]
        verbose_name = "User List Entry"
        verbose_name_plural = "User List Entries"

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="userlist")
    user = models.ForeignKey("accounts.Account", on_delete=models.CASCADE, related_name="equipmentlist")
    role = models.ForeignKey("accounts.Role", on_delete=models.SET_NULL, null=True, blank=True)
    hold = models.BooleanField(default=True, verbose_name="User clearable hold")
    admin_hold = models.BooleanField(default=False, verbose_name="Management hold")
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.display_name}: {self.role.name} of {self.equipment.name}"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """Save the entry and manage hold status based on role changes.

        Automatically sets hold to True for new entries or when a user's role level
        increases. For existing entries, checks whether hold should be maintained
        based on document sign-off requirements.

        Keyword Parameters:
            force_insert (bool):
                Force an INSERT operation. Default is False.
            force_update (bool):
                Force an UPDATE operation. Default is False.
            using (str or None):
                Database alias to use. Default is None.
            update_fields (list or None):
                List of field names to update. Default is None.
        """
        if self.pk and not self.hold:  # Check if the role has increased and hold if so
            old = UserListEntry.objects.get(pk=self.pk)
            if old.role.level < self.role.level:  # Old role level was lower
                self.hold = True
        elif not self.pk:  # New User List entries need to be held
            self.hold = True
        else:
            self.hold = self.check_for_hold()

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    @property
    def documents(self):
        """Retrieve all documents associated with the equipment.

        Returns:
            (QuerySet):
                QuerySet of Document objects for the equipment and its location.
        """
        return self.equipment.all_files.all()

    @property
    def sign_off_docs(self):
        """Retrieve documents requiring user sign-off.

        Returns only risk assessments and standard operating procedures that
        users must acknowledge before being cleared for equipment use.

        Returns:
            (QuerySet):
                QuerySet of Document objects with categories "ra" or "sop".
        """
        return self.documents.filter(category__in=["ra", "sop"])

    def check_for_hold(self):
        """Determine whether a hold should be placed on this user entry.

        Checks if the user has signed off all required risk assessment and SOP
        documents. Returns True if any required signatures are missing.

        Returns:
            (bool):
                True if hold should be maintained (missing signatures), False if user
                can be cleared (all documents signed).

        Notes:
            This method does not modify the hold flag; it only returns what the
            value should be.
        """
        for doc in self.sign_off_docs:
            if doc.signatures.filter(user=self.user, version=doc.version).count() == 0:
                return True
        else:
            return False


class DocumentSignOff(models.Model):
    """Records a user's acknowledgement of reading a specific document version.

    Tracks when users have read and signed off on safety documents, SOPs, and
    risk assessments. Each sign-off is tied to a specific document version to
    ensure users review updated materials.

    Attributes:
        document (Document):
            The document that was signed off.
        version (float):
            The version number of the document that was signed.
        user (Account):
            The user who signed off the document.
        created (datetime):
            Timestamp when the sign-off was created. Set automatically.
    """

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="signatures")
    version = models.FloatField()
    user = models.ForeignKey("accounts.Account", on_delete=models.CASCADE, related_name="signatures")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["document", "version", "user"]  # Enforce unique document/user/version

    def __str__(self):
        return f"{self.document.title} v{self.version} ({self.user.display_name}) {self.created}"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """Save the sign-off and update related user list entry hold status.

        After recording the sign-off, checks all equipment user list entries for
        this user where the document is relevant. If all required documents are
        now signed, removes the hold from those entries.

        Keyword Parameters:
            force_insert (bool):
                Force an INSERT operation. Default is False.
            force_update (bool):
                Force an UPDATE operation. Default is False.
            using (str or None):
                Database alias to use. Default is None.
            update_fields (list or None):
                List of field names to update. Default is None.
        """
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)
        # Find all items of equipment for which this is a file.
        search_Q = models.Q(equipment__files=self.document)
        # If this document is attached to a location, find all equipment in this and child locations.
        if self.document.all_locations:
            search_Q |= models.Q(equipment__location__in=self.document.all_locations)
        userlists = self.user.equipmentlist.filter(search_Q)
        for userlist in userlists.all():
            userlist.hold = userlist.check_for_hold()
            userlist.save()


class ChargingRate(models.Model):
    """Represents the cost of using equipment for a specific cost rate and date range.

    Each charging rate associates equipment with a cost rate (e.g., internal, external,
    commercial) and defines the charge per shift. Multiple charging rates can exist
    for the same equipment with different date ranges to handle price changes over time.

    Attributes:
        equipment (Equipment):
            The equipment item this rate applies to.
        cost_rate (CostRate):
            The cost rate category (e.g., internal vs external users).
        charge_rate (float):
            Cost per shift in pounds sterling. Default is 0.0.
        comment (str or None):
            Optional comment explaining the rate.
        dates (DateRange or None):
            Date range during which this rate is applicable. Defaults to current date
            through end of year 2999 if not specified.
    """

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="charge_rates")
    cost_rate = models.ForeignKey(CostRate, on_delete=models.CASCADE, related_name="equipment_rates")
    charge_rate = models.FloatField(default=0.0, verbose_name="Cost per shift")
    comment = models.CharField(max_length=80, blank=True, null=True)
    dates = DateRangeField(blank=True, null=True, verbose_name="Applicable Dates")

    class Meta:
        unique_together = ["equipment", "cost_rate", "dates"]  # Enforce unique equipment, cost_rate, effective dates

    def __str__(self):
        return f"{self.cost_rate.name} for {self.equipment.name} £{self.charge_rate}/shift"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """Save the charging rate and manage overlapping date ranges.

        Automatically sets default date ranges if not specified (today through year 2999).
        If a charging rate with overlapping dates exists for the same equipment and
        cost rate, truncates the old rate's date range to avoid conflicts.

        Keyword Parameters:
            force_insert (bool):
                Force an INSERT operation. Default is False.
            force_update (bool):
                Force an UPDATE operation. Default is False.
            using (str or None):
                Database alias to use. Default is None.
            update_fields (list or None):
                List of field names to update. Default is None.
        """
        if not self.dates:
            self.dates = DateRange(lower=Date.today(), upper=Date(2999, 12, 31))
        if not self.dates.lower:
            self.dates = DateRange(lower=Date.today(), upper=self.dates.upper)
        if not self.dates.upper:
            self.dates = DateRange(lower=self.dates.lower, upper=Date(2999, 12, 31))
        try:
            if not self.pk:
                old = self.__class__.objects.get(
                    equipment=self.equipment, cost_rate=self.cost_rate, dates__contains=self.dates.lower
                )
            else:
                old = self.__class__.objects.exclude(pk=self.pk).get(
                    equipment=self.equipment, cost_rate=self.cost_rate, dates__contains=self.dates.lower
                )
            old.dates = DateRange(lower=old.dates.lower, upper=self.dates.lower)
        except self.__class__.DoesNotExist:  # No overlapping charge_)rate
            return super().save(
                force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields
            )
        old.save(old)
        return super().save(
            force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields
        )


@patch_model(FlatPage, prep=property)
def slug(self):
    """Generate a URL-friendly slug from the page title.

    Returns:
        (str):
            Slugified version of the title (lowercase, hyphens instead of spaces).
    """
    return slugify(self.title)


@patch_model(Account, prep=property)
def signoffs(self):
    """Retrieve equipment entries where the user has outstanding sign-offs.

    Returns:
        (QuerySet):
            QuerySet of UserListEntry objects with hold=True for this user.
    """
    return self.equipmentlist.filter(hold=True)


@patch_model(Account, prep=property)
def management_holds(self):
    """Retrieve equipment where the user has administrative holds.

    Returns:
        (QuerySet):
            QuerySet of Equipment objects where this user has admin_hold=True.
    """
    return self.user_of.filter(admin_hold=True)
