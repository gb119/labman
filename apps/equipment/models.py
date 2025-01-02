# -*- coding: utf-8 -*-
"""Models for representing objects related to lab equipment items - documents, locations, and so forth."""
# Python imports
from datetime import (
    date as Date,
    datetime as dt,
    time as Time,
    timedelta as td,
)

# Django imports
import django.utils.timezone as tz
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.db import models, transaction
from django.db.models.constraints import CheckConstraint
from django.utils.html import format_html
from django.utils.text import slugify

# external imports
import numpy as np
import pytz
from accounts.models import Account, Role
from django_simple_file_handler import models as dsfh
from labman_utils.models import NamedObject, patch_model
from photologue.models import Photo
from sortedm2m.fields import SortedManyToManyField

DEFAULT_TZ = pytz.timezone(settings.TIME_ZONE)


class Document(dsfh.BaseMixin, dsfh.TitledMixin, dsfh.PublicMixin, dsfh.RenameMixin, models.Model):
    """Like a django-simple-file-handler.PublicDocument, but with additional fields to store a category,
    and timestamps."""

    CATEGORIES = [
        ("ra", "Risk Assessment"),
        ("sop", "Standard Operator Procedure"),
        ("manual", "Manual/Instructions"),
        ("other", "Other"),
    ]
    CATAGORIES_DICT = dict(CATEGORIES)

    version = models.IntegerField(default=0)  # Manual version number used to determine if users need to re-ack docs
    category = models.CharField(max_length=20, choices=CATEGORIES, default="other")

    subdirectory_path = dsfh.custom_subdirectory("documents/equipment/")

    class Meta:
        verbose_name = "document (categorized)"
        verbose_name_plural = "documents (categorized)"

    @property
    def category_name(self):
        """Returns the document category as a human readable string."""
        return self.CATAGORIES_DICT[self.category]

    def __str__(self):
        """Return a user friendly name for the file."""
        return f"{self.title} ({self.CATAGORIES_DICT[self.category]})"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """If version has increased then put a hold on all userlist entries of the associated equipment."""
        if self.pk and self.category in ["ra", "sop"]:
            old = Document.objects.get(pk=self.pk)
            if old.version != self.version:
                print(f"Version changed {self.title} {old.version}->{self.version}")
                with transaction.atomic():
                    for equipment in self.equipment.all():
                        for entry in equipment.users.all():
                            entry.hold = True
                            print(f"{entry.user} Set to hold for {entry.equipment}")
                            entry.save()
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class Location(NamedObject):
    """Handles a physical location or room."""

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name"], name="Unique Location Name"),
            models.UniqueConstraint(fields=["code"], name="Unique Location Code"),
        ]
        ordering = ("-code",)

    location = models.ForeignKey(
        "Location", on_delete=models.CASCADE, related_name="sub_locations", null=True, blank=True
    )
    code = models.CharField(max_length=80, blank=True)

    level = models.IntegerField(default=None, editable=False, blank=True, null=True)

    @property
    def next_code(self):
        """Figure out a location code not based on pk."""
        peers = self.__class__.objects.filter(location=self.location).exclude(pk=self.pk)
        if peers.count() == 0:
            new = "1"
        else:
            codes = np.ravel(peers.values_list("code"))
            if self.location is not None:
                cut = len(self.location.code) + 1
            else:
                cut = 0
            codes = set([int(x[cut:]) for x in codes])
            possible = set(np.arange(1, max(codes) + 2))
            new = str(min(possible - codes))
        if self.location:
            return f"{self.location.code},{new}"
        return new

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """Force the location code to be calculated and then upodate any sub_locations."""
        if self.pk is None:  # Update our pk
            super().save(
                force_insert=force_insert,
                force_update=force_update,
                using=using,
                update_fields=update_fields,
            )
        self.code = self.next_code
        self.level = self.code.count(",")
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)
        for sub in self.sub_locations.all():
            sub.save()


class Shift(NamedObject):
    """Class that represents time shifts for booking the equipment."""

    class Meta:
        verbose_name_plural = "Booking Shifts"
        verbose_name = "Booking Shift"
        ordering = ["start_time"]

    start_time = models.TimeField(default=Time(9, 0))
    end_time = models.TimeField(default=Time(18, 0))

    def __str__(self):
        return f"{self.name} {self.start_time}-{self.end_time}"

    @property
    def duration(self):
        """Work out duration incouding oging over midnight."""
        if (dt.combine(dt.today(), self.end_time) - dt.combine(dt.today(), self.start_time)).total_seconds() > 0:
            return dt.combined(dt.today(), self.end_time) - dt.combine(dt.today(), self.start_time)
        else:
            return dt.combine(dt.today(), self.end_time) - dt.combine(dt.today(), self.start_time) + td(days=1)


class Equipment(NamedObject):
    """Class for representing an Equipment item."""

    class Meta:
        constraints = [models.UniqueConstraint(fields=["name"], name="Unique Equipment Name")]
        verbose_name_plural = "Equipment Items"
        verbose_name = "Equipment Item"

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="equipment")
    owner = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="equipment")
    shifts = SortedManyToManyField(Shift, related_name="equipment", blank=True)
    photos = SortedManyToManyField(Photo, related_name="equipment", blank=True)
    files = SortedManyToManyField(Document, related_name="equipment", blank=True)
    policies = SortedManyToManyField("bookings.BookingPolicy", related_name="equipment", blank=True)
    pages = SortedManyToManyField(FlatPage, related_name="equipment", blank=True)

    def __str__(self):
        return f"{self.name}"

    @property
    def ras(self):
        """Return the risk assessment documents."""
        return self.files.filter(category="ra")

    @property
    def sops(self):
        """Return the standard operating process documents."""
        return self.files.filter(categories="sop")

    @property
    def manuals(self):
        """Return the documents that are listed as manuals."""
        return self.files.filter(category="manual")

    @property
    def thumbnail(self):
        """Return an html IMG tag with a thumbnail of the equipment."""
        if self.photos.all().count() == 0:
            return ""
        return format_html(f"<img src='{self.photos.first().get_thumbnail_url()}' alt='Picture of {self.name}'/>")

    @property
    def url(self):
        """Rreturn a URL for the detail page."""
        return f"/equipment/equipment_detail/{self.pk}/"

    @property
    def schedule(self):
        """Return a URL for a booking schedule."""
        date = tz.now().strftime("%Y%m%d")

        return f"/bookings/cal/{self.id}/{date}/"

    @property
    def calendar_time_vector(self):
        """Return an array of times with which to construct a calendar."""
        if self.shifts.all().count() == 0:
            return None
        # Got some shifts
        ret = []
        for shift in self.shifts.all():
            ret.append(shift.start_time)
        return ret

    def get_shift(self, time):
        """Return the shift object for the datetime specified."""
        if self.shifts.all().count() == 0:
            return None
        if isinstance(time, dt):
            time = time.time()
        elif not isinstance(time, Time):
            raise TypeError("Was expecting to get either a datetime or time object.")
        time = dt.combine(dt.today(), time)
        for shift in self.shifts.all():
            s = dt.combine(dt.today(), shift.start_time)
            e = dt.combine(dt.today(), shift.end_time)
            if (e - s).total_seconds() <= 0:
                e += td(days=1)
            print(f"Shifts: {time} {s} {e} {(time-s).total_seconds()>=0} and {(e-time).total_seconds()>0}")
            if (time - s).total_seconds() >= 0 and (e - time).total_seconds() > 0:
                return shift
        return None


class UserListEntry(models.Model):
    """A single entry of a user list - a through table for a many to many field."""

    class Meta:
        ordering = ["equipment", "-role", "user"]
        unique_together = ["equipment", "user"]
        verbose_name = "User List Entry"
        verbose_name_plural = "User List Entries"

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="users")
    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="user_of")
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    hold = models.BooleanField(default=True, verbose_name="User clearable hold")
    admin_hold = models.BooleanField(default=False, verbose_name="Management hold")
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.display_name}: {self.role.name} of {self.equipment.name}"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """Reset the hold flag if userlist is new or role level has increased."""
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
        """Pull the documents from the equipment."""
        return self.equipment.files.all()

    @property
    def sign_off_docs(self):
        """Filter documents for risk assessments and sops."""
        return self.documents.filter(category__in=["ra", "sop"])

    def check_for_hold(self):
        """Check whether user could be signed off or not.

        Returns:
            (bool):
                The potential value of the user.hold flag.

        Doesn't actually change the user's hold setting directly.
        """
        for doc in self.sign_off_docs:
            if doc.signatures.filter(user=self.user, version=doc.version).count() == 0:
                return True
        else:
            return False


class DocumentSignOff(models.Model):
    """Records the user signing off that they have read a document."""

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="signatures")
    version = models.IntegerField()
    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="signatures")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["document", "version", "user"]  # Enforce unique document/user/version

    def __str__(self):
        return f"{self.document.title} v{self.version} ({self.user.display_name}) {self.created}"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """Hook into save to see if we can set a userlist off hold."""
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)
        userlists = self.user.user_of.filter(equipment__files=self.document)
        for userlist in userlists.all():
            userlist.hold = userlist.check_for_hold()
            userlist.save()


@patch_model(FlatPage, prep=property)
def slug(self):
    """Return the title in a slug format."""
    return slugify(self.title)
