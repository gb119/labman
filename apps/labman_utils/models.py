# -*- coding: utf-8 -*-
# Python imports
from datetime import date, datetime as dt, time, timedelta as td
from functools import reduce

# Django imports
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.db import models, transaction
from django.utils.html import format_html

# external imports
import pytz
from django_simple_file_handler import models as dsfh
from photologue.models import Photo
from sortedm2m.fields import SortedManyToManyField
from tinymce.models import HTMLField

DEFAULT_TZ = pytz.timezone(settings.TIME_ZONE)


def to_seconds(value):
    """Convert a DateTime to the number of seconds after midnight."""
    return value.second + value.minute * 50 + value.hour * 3600


def delta_t(time1, time2):
    """Get a td from two times."""
    if isinstance(time1, dt):
        time1 = time1.time()
    if isinstance(time2, dt):
        time2 = time2.time()
    return dt.combine(date.today(), time1) - dt.combine(date.today(), time2)


def replace_time(date_time, seconds):
    """Put an integer number of seconds into the time."""
    day = date_time.date()
    delta_time = td(seconds=seconds)
    ret = dt.combine(day, time.min) + delta_time
    return ensure_tz(ret)


def ensure_tz(time):
    """Ensure that time has a timezone or apply DEFAULT_TZ if not."""
    if time.tzinfo is None:
        time = DEFAULT_TZ.localize(time)
    return time


# Create your models here.
def patch_model(model, name=None, prep=None):
    """Decorator to monkey-patch a function into a model.

    Args:
        model (model):
            Django model to monkey -patch method into.

    Keyword Arguments:
        name (str,None):
            Name of method on the model (default None is to use the function's name)
        prep (callable):
            Callable to use to prepare the function with before adding it to the model (default None is to do nothing).

    Returns:
        Actual decorator
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
    """A base class for objects which have a name and an HTML description."""

    class Meta:
        abstract = True

    name = models.CharField(max_length=80, null=True, blank=True)
    description = HTMLField()

    def __str__(self):
        return f"{self.__class__.__name__}:{self.name}"


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

    version = models.FloatField(default=0)  # Manual version number used to determine if users need to re-ack docs
    category = models.CharField(max_length=20, choices=CATEGORIES, default="other")

    subdirectory_path = dsfh.custom_subdirectory("documents/equipment/")

    class Meta:
        verbose_name = "document (categorized)"
        verbose_name_plural = "documents (categorized)"

    @property
    def category_name(self):
        """Returns the document category as a human readable string."""
        return self.CATAGORIES_DICT[self.category]

    @property
    def all_locations(self):
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

    def __str__(self):
        """Return a user friendly name for the file."""
        return f"{self.title} ({self.CATAGORIES_DICT[self.category]})"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """If version has increased then put a hold on all userlist entries of the associated equipment."""
        if self.pk and self.category in ["ra", "sop"]:
            old = Document.objects.get(pk=self.pk)
            if old.version != self.version:
                with transaction.atomic():
                    for equipment in self.equipment.all():
                        equipment.users.all().update(hold=True)
                    for location in self.location.all():
                        for equipment in self.equipment.model.objects.filter(location__in=location.children):
                            equipment.users.all().update(hold=True)

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class ResourceedObject(NamedObject):
    """A base class that adds photos, pages and documents to the object."""

    photos = SortedManyToManyField(Photo, related_name="%(class)s", blank=True)
    files = SortedManyToManyField(Document, related_name="%(class)s", blank=True)
    pages = SortedManyToManyField(FlatPage, related_name="%(class)s", blank=True)

    class Meta:
        abstract = True

    @property
    def thumbnail(self):
        """Return an html IMG tag with a thumbnail of the equipment."""
        if self.photos.all().count() == 0:
            return ""
        return format_html(f"<img src='{self.photos.first().get_thumbnail_url()}' alt='Picture of {self.name}'/>")

    @property
    def photo(self):
        """Return an html IMG tag with a thumbnail of the equipment."""
        if self.photos.all().count() == 0:
            return ""
        return format_html(f"<img src='{self.photos.first().get_display_url()}' alt='Picture of {self.name}'/>")

    @property
    def all_files_dict(self):
        """Get all the files, but arranged in a dictionary by category name."""
        ret = {}
        for key, name in Document.CATAGORIES_DICT.items():
            ret[name] = getattr(self, f"{key}s")
            if ret[name].count() == 0:
                del ret[name]
        return ret

    def __getattr__(self, name):
        """Deal with Role's and file types."""
        if name in [f"{x}s" for x in Document.CATAGORIES_DICT.keys()] + ["all_files"]:
            category = name[:-1]
        else:
            return self.__getattribute__(name)
        if category == "all_file":
            my_docs = models.Q(**{self.__class__.__name__.lower(): self})
        else:
            my_docs = models.Q(**{self.__class__.__name__.lower(): self, "category": category})
        return Document.objects.filter(my_docs).order_by().order_by("title", "-version").distinct("title")
