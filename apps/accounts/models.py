#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Handles respources that have a physical existence."""

# Django imports
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.flatpages.models import FlatPage
from django.db import models
from django.utils.functional import cached_property, classproperty

# external imports
from photologue.models import Photo
from six import string_types
from sortedm2m.fields import SortedManyToManyField
from tinymce.models import HTMLField

# Create your models here.

TRAINEE = 0
USER = 100
ADVANCED_USER = 200
INSTRUCTOR = 300
MANAGER = 1000


class Project(models.Model):
    """Represent a chargeable project."""

    name = models.CharField(max_length=80)
    short_name = models.CharField(max_length=20)
    code = models.CharField(max_length=20)
    description = HTMLField()

    def __str__(self):
        return f"{self.short_name} ({self.code})"


class ResearchGroup(models.Model):
    """Represetns a |Research Group"""

    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, primary_key=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.name

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        """Sanitise the account code field and then save."""
        self.code = self.code.upper()
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class Account(AbstractUser):
    """Replacement for standard user account model that supports extra attributes."""

    class Meta:
        ordering = ["last_name", "first_name"]
        permissions = [
            ("access_admin", "Can Access the Admin backend"),
        ]

    USERNAME_FIELD = "username"

    number = models.IntegerField(blank=True, null=True)
    title = models.CharField(max_length=20, blank=True, null=True)
    project = SortedManyToManyField(Project, blank=False, related_name="researchers")
    end_date = models.DateField(blank=True, null=True)
    research_group = models.ForeignKey(
        ResearchGroup, on_delete=models.SET_NULL, related_name="members", blank=True, null=True
    )
    manager = models.ForeignKey("Account", on_delete=models.SET_NULL, blank=True, null=True, related_name="managing")
    photos = SortedManyToManyField(Photo, blank=True)
    pages = SortedManyToManyField(FlatPage, blank=True)

    def natural_key(self):
        """Defines the username as a natural key"""
        return self.username

    @cached_property
    def display_name(self):
        """Produce a nicely formmated name for the account."""
        return f"{self.first_name} {self.last_name}"

    @property
    def default_project(self):
        """Returns the first project code associated with this account."""
        return self.project.first()

    @property
    def mugshot(self):
        """Return the first photo object associated with this account."""
        if self.photos.all().count() > 0:
            return self.photos.first()
        return None

    @cached_property
    def formal_name(self):
        """Return a formal name for the account."""
        if self.title is None:
            title = ""
        else:
            title = self.title
        initials = ".".join(self.initials[:-1])
        return f"{title} {initials} {self.last_name}".strip()

    def __str__(self):
        """String conversion includes the name and username."""
        return f"{self.last_name}, {self.first_name} ({self.username})"

    def is_member(self, group):
        """Tests whether the account is part of the group."""
        if not self.pk:
            return False
        if isinstance(group, string_types):
            return self.groups.filter(name=group).count() == 1
        if isinstance(group, Group):
            return self.groups.filter(name=group.name).count() == 1
        return False

    @cached_property
    def initials(self):
        """Return the initials of this user account."""
        if "." in self.email.split("@")[0]:
            userfield = self.email.split("@")[0]
            initials = [x.upper()[0] for x in userfield.split(".")]
            initials = "".join(initials)
        else:
            initials = (self.first_name + "?")[0].upper() + (self.last_name + "?")[0].upper()
        if len(initials) > 1:
            return initials
        return self.username

    @property
    def is_supervisor(self):
        """Return true if the account is a super-user account."""
        return self.managing.count() > 0

    @property
    def primary_project(self):
        if self.project.all().count() > 0:
            return self.project.all().first()
        return None


class Role(models.Model):
    """Class to describe a role within the user management system."""

    class Meta:
        ordering = ["level"]

    name = models.CharField(max_length=20, primary_key=True)
    description = HTMLField(null=True, blank=True)
    level = models.IntegerField(default=TRAINEE)

    def __str__(self):
        """String conversion just uses the name."""
        return self.name

    @classproperty
    def default(cls):
        """Class method that returns the lowest level of user on an item of equipment."""
        return cls.objects.get(level=TRAINEE)

    @classproperty
    def trainee(cls):
        """Return the trainee role."""
        return cls.objects.get(level=TRAINEE)

    @classproperty
    def user(cls):
        """Return the user level role."""
        return cls.objects.get(level=USER)

    @classproperty
    def advanced_user(cls):
        """Return the Advanced User level."""
        return cls.objects.get(level=ADVANCED_USER)

    @classproperty
    def instructor(cls):
        """Return the instructor role."""
        return cls.objects.get(level=INSTRUCTOR)

    @classproperty
    def manager(cls):
        """Return the manager role."""
        return cls.objects.get(level=MANAGER)
