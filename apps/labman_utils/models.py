# -*- coding: utf-8 -*-
"""Base models and utility functions for the labman application.

This module provides core model base classes and time manipulation utilities
used throughout the labman Django application. It includes NamedObject and
ResourcedObject base classes for common model functionality, as well as
helper functions for working with dates and times.
"""
# Python imports
from datetime import date, datetime as dt, time, timedelta as td
from functools import reduce

# Django imports
from django.apps import apps
from django.conf import settings
from django.contrib.admin import widgets as admin_widgets
from django.contrib.flatpages.models import FlatPage
from django.db import models, transaction
from django.utils.html import format_html

# external imports
import pytz
from django_simple_file_handler import models as dsfh
from photologue.models import Photo
from sitetree.models import TreeBase, TreeItemBase
from sortedm2m.fields import SortedManyToManyField
from tinymce.models import HTMLField

# app imports
from .fields import ObfuscatedCharField
from .widgets import AdminObfuscatedTinyMCE, ObfuscatedTinyMCE

DEFAULT_TZ = pytz.timezone(settings.TIME_ZONE)


class ObfuscatedHTMLField(HTMLField):
    """Custom HTML field that uses obfuscated widgets for security.

    This field extends TinyMCE's HTMLField to use custom obfuscated widgets
    that prevent email addresses and other sensitive data from being easily
    harvested from rendered HTML content.
    """

    def formfield(self, **kwargs):
        """Create a form field with obfuscated widgets.

        Keyword Parameters:
            **kwargs (dict):
                Additional keyword arguments to pass to the parent formfield method.

        Returns:
            (Field): A form field configured with obfuscated widgets.
        """
        defaults = {"form_class": ObfuscatedCharField, "widget": ObfuscatedTinyMCE}
        defaults.update(kwargs)

        # As an ugly hack, we override the admin widget
        if defaults["widget"] == admin_widgets.AdminTextareaWidget:
            defaults["widget"] = AdminObfuscatedTinyMCE

        return super().formfield(**defaults)


def to_seconds(value):
    """Convert a DateTime or time object to the number of seconds after midnight.

    Args:
        value (datetime or time):
            The time value to convert.

    Returns:
        (int): Number of seconds since midnight.

    Notes:
        This function appears to have a bug - it uses 50 for minute conversion
        instead of 60. This may be intentional but should be verified.
    """
    return value.second + value.minute * 60 + value.hour * 3600


def delta_t(time1, time2):
    """Calculate the time difference between two time objects.

    Args:
        time1 (datetime or time):
            First time value.
        time2 (datetime or time):
            Second time value.

    Returns:
        (timedelta): The difference between time1 and time2.

    Notes:
        If datetime objects are provided, extracts the time component before
        calculating the difference. The calculation combines each time with
        today's date to perform the subtraction.
    """
    if isinstance(time1, dt):
        time1 = time1.time()
    if isinstance(time2, dt):
        time2 = time2.time()
    return dt.combine(date.today(), time1) - dt.combine(date.today(), time2)


def replace_time(date_time, seconds):
    """Replace the time component of a datetime with a specified number of seconds.

    Args:
        date_time (datetime):
            The datetime whose time component should be replaced.
        seconds (int):
            Number of seconds since midnight for the new time.

    Returns:
        (datetime): A datetime with the same date but time set to the specified seconds.

    Notes:
        The returned datetime will have a timezone applied via ensure_tz.
    """
    day = date_time.date()
    delta_time = td(seconds=seconds)
    ret = dt.combine(day, time.min) + delta_time
    return ensure_tz(ret)


def ensure_tz(time):
    """Ensure that a datetime has a timezone, applying DEFAULT_TZ if needed.

    Args:
        time (datetime):
            The datetime to check and potentially modify.

    Returns:
        (datetime): The datetime with a timezone guaranteed to be set.

    Notes:
        If the input datetime is naive (no timezone), DEFAULT_TZ is applied.
        If it already has a timezone, it is returned unchanged.
    """
    if time.tzinfo is None:
        time = DEFAULT_TZ.localize(time)
    return time


def patch_model(model, name=None, prep=None):
    """Decorator to monkey-patch a function into a Django model.

    Args:
        model (Model):
            Django model class to monkey-patch the method into.

    Keyword Parameters:
        name (str or None):
            Name of the method on the model. If None, uses the function's name.
        prep (callable or None):
            Callable to use to prepare the function before adding it to the model.
            If None, no preparation is performed.

    Returns:
        (callable): Decorator function that performs the monkey-patching.

    Examples:
        @patch_model(MyModel, name='custom_method')
        def my_function(self):
            return self.field * 2
    """

    def patch_model_decorator(func):
        if name is None:
            attr_name = func.__name__
        else:
            attr_name = name
        if prep is not None:
            doc = func.__doc__
            func = prep(func)
            func.__doc__ = doc
        setattr(model, attr_name, func)

    return patch_model_decorator


class NamedObject(models.Model):
    """Base class for models with a name and HTML description.

    This abstract model provides common fields for named entities throughout
    the labman application. All models inheriting from this class will have
    a name and description field.

    Attributes:
        name (CharField):
            The name of the object, maximum 80 characters.
        description (ObfuscatedHTMLField):
            An HTML description of the object with email obfuscation.
    """

    class Meta:
        abstract = True

    name = models.CharField(max_length=80, null=True, blank=True)
    description = ObfuscatedHTMLField()

    def __str__(self):
        """Return a string representation combining class name and object name.

        Returns:
            (str): String in the format "ClassName:object_name".
        """
        return f"{self.__class__.__name__}:{self.name}"


class Document(dsfh.BaseMixin, dsfh.TitledMixin, dsfh.PublicMixin, dsfh.RenameMixin, models.Model):
    """Document model for storing categorised files with version control and review tracking.

    Extends django-simple-file-handler functionality to add document categorisation,
    version tracking, and review date management. Documents can be risk assessments,
    SOPs, COSHH forms, manuals, or other types.

    Attributes:
        version (FloatField):
            Manual version number used to determine if users need to re-acknowledge documents.
        category (CharField):
            Document category from predefined choices (ra, sop, coshh, manual, other).
        review_date (DateField):
            Date when the document should be reviewed.
        CATEGORIES (list):
            List of tuples defining valid document categories.
        CATAGORIES_DICT (dict):
            Dictionary mapping category codes to human-readable names.

    Notes:
        When a version is incremented for risk assessments or SOPs, all associated
        equipment user lists are automatically put on hold to ensure re-acknowledgement.
    """

    CATEGORIES = [
        ("ra", "Risk Assessment"),
        ("sop", "Standard Operator Procedure"),
        ("coshh", "COSHH Forms"),
        ("manual", "Manual/Instructions"),
        ("other", "Other"),
    ]
    CATAGORIES_DICT = dict(CATEGORIES)

    version = models.FloatField(default=0)  # Manual version number used to determine if users need to re-ack docs
    category = models.CharField(max_length=20, choices=CATEGORIES, default="other")
    review_date = models.DateField(blank=True, null=True, help_text="Date document should be reviewed on.")

    subdirectory_path = dsfh.custom_subdirectory("documents/equipment/")

    class Meta:
        verbose_name = "document (categorized)"
        verbose_name_plural = "documents (categorized)"

    @property
    def category_name(self):
        """Return the document category as a human-readable string.

        Returns:
            (str): Human-readable category name.
        """
        return self.CATAGORIES_DICT[self.category]

    @property
    def all_locations(self):
        """Return all locations associated with this document, including parent locations.

        Returns:
            (QuerySet or None): QuerySet of Location objects, or None if no locations.
        """
        if not hasattr(self, "location"):
            return None
        q_obs = []
        for location in self.location.all():
            q_obs.append(models.Q(code__startswith=location.code))
        if not q_obs:
            return None
        return (
            self.location.model.objects.filter(reduce(lambda left, right: left | right, q_obs))
            .order_by("code")
            .distinct()
        )

    @property
    def needs_review(self):
        """Check if the document needs review based on review date.

        Returns:
            (bool): True if review_date exists and has passed, False otherwise.
        """
        return self.review_date and self.review_date < dt.today().date()

    @property
    def review_soon(self):
        """Check if the document needs review within the next 30 days.

        Returns:
            (bool): True if review is needed within 30 days, False otherwise.
        """
        return self.review_date and (self.review_date - dt.today().date()) < td(days=30)

    def __str__(self):
        """Return a user-friendly name for the file.

        Returns:
            (str): String combining title and category name.
        """
        return f"{self.title} ({self.CATAGORIES_DICT[self.category]})"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """Save the document and handle version changes for risk assessments and SOPs.

        If the version has increased for RA or SOP documents, puts a hold on all
        userlist entries of associated equipment to ensure re-acknowledgement.

        Keyword Parameters:
            force_insert (bool):
                Force an INSERT operation.
            force_update (bool):
                Force an UPDATE operation.
            using (str):
                Database alias to use.
            update_fields (list):
                List of field names to update.
        """
        if self.pk and self.category in ["ra", "sop"]:
            old = Document.objects.get(pk=self.pk)
            if old.version != self.version:
                with transaction.atomic():
                    # Collect all equipment IDs that need userlist updates
                    equipment_ids = set()

                    # Add equipment directly associated with this document
                    equipment_ids.update(self.equipment.values_list("id", flat=True))

                    # Add equipment at locations associated with this document
                    for location in self.location.all():
                        child_equipment_ids = Equipment.objects.filter(
                            location__in=location.children
                        ).values_list("id", flat=True)
                        equipment_ids.update(child_equipment_ids)

                    # Bulk update all userlist entries for collected equipment
                    if equipment_ids:
                        UserListEntry = apps.get_model("equipment", "UserListEntry")
                        UserListEntry.objects.filter(equipment_id__in=equipment_ids).update(hold=True)

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class ResourceedObject(NamedObject):
    """Base class for objects with photos, documents, and pages.

    Extends NamedObject to add support for photos, files (documents), and
    flat pages. Provides properties and methods for accessing and displaying
    these resources.

    Attributes:
        photos (SortedManyToManyField):
            Related photos for this object.
        files (SortedManyToManyField):
            Related document files for this object.
        pages (SortedManyToManyField):
            Related flat pages for this object.

    Notes:
        This is an abstract model. The many-to-many field names use the
        %(class)s placeholder to create unique reverse relations for each
        concrete model that inherits from this class.
    """

    photos = SortedManyToManyField(Photo, related_name="%(class)s", blank=True)
    files = SortedManyToManyField(Document, related_name="%(class)s", blank=True)
    pages = SortedManyToManyField(FlatPage, related_name="%(class)s", blank=True)

    class Meta:
        abstract = True

    @property
    def thumbnail(self):
        """Return an HTML IMG tag with a thumbnail of the first photo.

        Returns:
            (str): HTML img tag with thumbnail URL, or empty string if no photos.
        """
        if self.photos.all().count() == 0:
            return ""
        return format_html(f"<img src='{self.photos.first().get_thumbnail_url()}' alt='Picture of {self.name}'/>")

    @property
    def photo(self):
        """Return an HTML IMG tag with the display size of the first photo.

        Returns:
            (str): HTML img tag with display URL, or empty string if no photos.
        """
        if self.photos.all().count() == 0:
            return ""
        return format_html(f"<img src='{self.photos.first().get_display_url()}' alt='Picture of {self.name}'/>")

    @property
    def all_files_dict(self):
        """Get all files organised into a dictionary by category name.

        Returns:
            (dict): Dictionary mapping category names to querysets of documents.
                    Only includes categories that have at least one document.
        """
        ret = {}
        for key, name in Document.CATAGORIES_DICT.items():
            ret[name] = getattr(self, f"{key}s")
            if ret[name].count() == 0:
                del ret[name]
        return ret

    def __getattr__(self, name):
        """Provide dynamic access to document categories and all files.

        Args:
            name (str):
                Attribute name being accessed. Handles special cases for document
                category access (e.g., 'ras', 'sops', 'all_files').

        Returns:
            (QuerySet): Documents matching the requested category.

        Raises:
            AttributeError: If the attribute is not a valid document category accessor.
        """
        if name in [f"{x}s" for x in Document.CATAGORIES_DICT.keys()] + ["all_files"]:
            category = name[:-1]
        else:
            return self.__getattribute__(name)
        if category == "all_file":
            my_docs = models.Q(**{self.__class__.__name__.lower(): self})
        else:
            my_docs = models.Q(**{self.__class__.__name__.lower(): self, "category": category})
        return Document.objects.filter(my_docs).order_by().order_by("title", "-version").distinct("title")


class GroupedTree(TreeBase):
    """Placeholder for grouped tree navigation.

    This class extends TreeBase to support grouped tree structures
    in the labman application.
    """


class GroupedTreeItem(TreeItemBase):
    """Tree item with group-based access control.

    Extends TreeItemBase to add group-based permissions for controlling
    access to menu items. Supports allowing and blocking specific groups,
    as well as staff and superuser access controls.

    Attributes:
        groups (ManyToManyField):
            Groups that are allowed to access this menu item.
        not_groups (ManyToManyField):
            Groups that are blocked from accessing this menu item.
        access_staff (IntegerField):
            Controls staff access: 0=neutral, 1=grant, 2=block.
        access_superuser (IntegerField):
            Controls superuser access: 0=neutral, 1=grant, 2=block.
        TRISTATE (list):
            Choices for access control fields.
    """

    TRISTATE = [(0, "--"), (1, "Grant"), (2, "Block")]

    groups = models.ManyToManyField(
        "auth.Group", related_name="allowed_menu_items", verbose_name="Access Groups", blank=True
    )
    not_groups = models.ManyToManyField(
        "auth.Group", related_name="blocked_menu_items", verbose_name="Blocked Groups", blank=True
    )
    access_staff = models.IntegerField(default=0, choices=TRISTATE, verbose_name="Staff Access")
    access_superuser = models.IntegerField(default=0, choices=TRISTATE, verbose_name="Superuser Access")

    def access_check(self, tree):
        """Check whether the current user has access to this tree item.

        Args:
            tree (Tree):
                The tree object containing context and request information.

        Returns:
            (bool or None): True if access is explicitly granted, False if explicitly
                           denied, None if no decision can be made.

        Notes:
            Access control is checked in the following order:
            1. Base authentication via parent class
            2. Superuser access restrictions
            3. Staff access restrictions
            4. Group membership (allowed groups)
            5. Group exclusion (blocked groups)
        """
        auth = tree.check_access_auth(self, tree.context)
        user = tree.current_request.user

        if auth and user.is_authenticated:  # Now check groups

            # If access_superuser is 1 or 2, checker whether user is or is not superuser. Necessary but not sufficient
            if (self.access_superuser == 2 and user.is_superuser) or (
                self.access_superuser == 1 and not user.is_superuser
            ):
                return False
            elif self.access_restricted and self.access_perm_type == self.PERM_TYPE_ANY:
                return True

            # If access_staff is 1 or 2, check whether user is or ir not staff. Necessary but not sufficient
            if (self.access_staff == 2 and user.is_staff) or (self.access_staff == 1 and not user.is_staff):
                return False
            elif self.access_restricted and self.access_perm_type == self.PERM_TYPE_ANY:
                return True

            user_groups = set([x[0] for x in user.groups.all().values_list("name")])
            if self.groups.all().count() > 0:  # If no groups defined, then don't test
                item_groups = set([x[0] for x in self.groups.all().values_list("name")])
                if len(item_groups & user_groups) == 0:  # User not in allowed groups - block
                    return False
            if self.not_groups.all().count() > 0:  # If no groups defined, then don't test
                item_groups = set([x[0] for x in self.not_groups.all().values_list("name")])
                if len(item_groups & user_groups) > 0:  # User in at least 1 blocked group - block
                    return False

        return None  # If we can't make a decision based on groups, don't take a decision at all.


@patch_model(Photo)
def displaY_tag(self, size):
    """Return a complete HTML image tag for the current photo.

    Args:
        size (str):
            Size name for the image (e.g., 'thumbnail', 'display', 'admin_thumbnail').

    Returns:
        (str): HTML img tag with the requested size URL.

    Examples:
        photo.displaY_tag('thumbnail')
        photo.displaY_tag('display')
    """
    url = getattr(self, f"get_{size}_url", lambda: "")()
    return f'<img src="{url}" alt="self.caption" class="photo-display" id="{self.slug}" />'
