#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Account and user management models for the labman application.

This module defines models for managing user accounts, research groups, and
roles within the laboratory management system. It extends Django's authentication
system with additional attributes and relationships specific to laboratory
management.
"""

# Django imports
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.flatpages.models import FlatPage
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property, classproperty

# external imports
from costings.models import CostCentre
from labman_utils.models import ResourceedObject
from photologue.models import Photo
from six import string_types
from sortedm2m.fields import SortedManyToManyField

# Create your models here.

TRAINEE = 0
USER = 100
ADVANCED_USER = 200
INSTRUCTOR = 300
MANAGER = 1000


class ResearchGroup(ResourceedObject):
    """Model representing a research group within the laboratory.

            Research groups are organisational units that contain member accounts.
            Each group has a unique code and name, and can have associated photos,
            documents, and pages through the ResourcedObject base class.

    Attributes:
        code (CharField):
            Primary key code for the research group, maximum 10 characters.
            Automatically converted to uppercase on save.


    Examples:
        Inspect the public interface in an interactive session::

            >>> ResearchGroup.__name__
            'ResearchGroup'

    """

    code = models.CharField(max_length=10, primary_key=True)

    class Meta:
        """Configure the Meta class."""

        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["name"], name="Unique Research Group Name")]

    def __str__(self):
        """Return the name of the research group.

        Returns:
            (str): The research group name.

        """
        return self.name

    def save(
        self,
        *args,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        """Save the research group, ensuring the code is uppercase.

        Keyword Parameters:
            force_insert (bool):
                Force an INSERT operation.
            force_update (bool):
                Force an UPDATE operation.
            using (str):
                Database alias to use.
            update_fields (list):
                List of field names to update.


        Args:
            force_insert (object):
                Value supplied for ``force_insert``.
            force_update (object):
                Value supplied for ``force_update``.
            using (object):
                Value supplied for ``using``.
            update_fields (object):
                Value supplied for ``update_fields``.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(ResearchGroup.save)
                True

        """
        self.code = self.code.upper()
        super().save(
            *args,
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class ActiveUsersManager(models.Manager):
    """Prefilter the user accounts for just active users.

    Examples:
        Inspect the public interface in an interactive session::

            >>> ActiveUsersManager.__name__
            'ActiveUsersManager'

    """

    def get_queryset(self):
        """Perform the get queryset operation.

        Returns:
            (object):
                The result of the operation.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(ActiveUsersManager.get_queryset)
                True

        """
        return super().get_queryset().filter(is_active=True)


class Account(AbstractUser):
    """Extended user account model with laboratory-specific attributes.

            This model extends Django's AbstractUser to include additional fields
            for research group membership, project associations, photos, and other
            laboratory management features.

    Attributes:
        number (IntegerField):
            Account number or ID within the organisation.
        title (CharField):
            Professional title (e.g., Dr, Prof, Mr, Ms).
        end_date (DateField):
            Date when the account expires or user leaves.
        research_group (ForeignKey):
            Research group this account belongs to.
        project (SortedManyToManyField):
            Cost centres/projects associated with this account.
        manager (ForeignKey):
            The account's line manager (self-referential).
        photos (SortedManyToManyField):
            Photos associated with this account (e.g., profile pictures).
        pages (SortedManyToManyField):
            Flat pages associated with this account.


    Examples:
        Inspect the public interface in an interactive session::

            >>> Account.__name__
            'Account'

    """

    class Meta:
        """Configure the Meta class."""

        ordering = ["last_name", "first_name"]
        permissions = [
            ("access_admin", "Can Access the Admin backend"),
        ]

    USERNAME_FIELD = "username"

    active = ActiveUsersManager()

    number = models.IntegerField(blank=True, null=True)
    title = models.CharField(max_length=20, blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    research_group = models.ForeignKey(
        ResearchGroup, on_delete=models.SET_NULL, related_name="members", blank=True, null=True
    )
    project = SortedManyToManyField(CostCentre, related_name="accounts", blank=True)
    manager = models.ForeignKey("Account", on_delete=models.SET_NULL, blank=True, null=True, related_name="managing")
    photos = SortedManyToManyField(Photo, blank=True, related_name="accounts")
    pages = SortedManyToManyField(FlatPage, blank=True)

    def natural_key(self):
        """Return the username as a natural key for serialisation.

        Returns:
            (str): The username.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Account.natural_key)
                True

        """
        return self.username

    @cached_property
    def display_name(self):
        """Produce a nicely formatted display name for the account.

        Returns:
            (str): The full name in the format "FirstName LastName".


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Account.display_name)
                True

        """
        return f"{self.first_name} {self.last_name}"

    @property
    def default_project(self):
        """Return the first project code associated with this account.

        Returns:
            (CostCentre or None): The first project, or None if no projects.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Account.default_project)
                True

        """
        return self.project.first()

    @property
    def mugshot(self):
        """Return the first photo object associated with this account.

        Returns:
            (Photo or None): The first photo if available, generic profile image
                            if one exists, or None if neither is available.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Account.mugshot)
                True

        """
        if self.photos.all().count() > 0:
            return self.photos.first()
        try:
            return Photo.objects.get(slug="generic-profile-image")
        except Photo.DoesNotExist:
            return None

    @property
    def mugshot_edit_link(self):
        """Return the URL for editing the account's photo.

        Returns:
            (str): URL to edit existing photo or create new photo.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Account.mugshot_edit_link)
                True

        """
        if self.photos.all().count() > 0:
            return reverse("labman_utils:edit_account_photo", args=(self.pk, self.mugshot.pk))
        return reverse("labman_utils:new_account_photo", args=(self.pk,))

    @cached_property
    def formal_name(self):
        """Return a formal name for the account including title and initials.

        Returns:
            (str): Formal name in the format "Title I. LastName", with appropriate
                  spacing even if title is not set.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Account.formal_name)
                True

        """
        if self.title is None:
            title = ""
        else:
            title = self.title
        initials = ".".join(self.initials[:-1])
        return f"{title} {initials} {self.last_name}".strip()

    @cached_property
    def name(self):
        """Return the formal name for the account.

        Returns:
            (str): Alias for formal_name property.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Account.name)
                True

        """
        return self.formal_name

    @cached_property
    def url(self):
        """Return the URL to the account page.

        Returns:
            (str): URL path to the user's profile page.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Account.url)
                True

        """
        return f"/accounts/user/{self.username}/"

    def __str__(self):
        """Return a string representation of the account.

        Returns:
            (str): String in the format "LastName, FirstName (username)".

        """
        return f"{self.last_name}, {self.first_name} ({self.username})"

    def is_member(self, group):
        """Test whether the account is a member of the specified group.

        Args:
            group (str or Group):
                Either a group name string or a Group object.

        Returns:
            (bool): True if the account is a member of the group, False otherwise.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Account.is_member)
                True

        """
        if not self.pk:
            return False
        if isinstance(group, string_types):
            return self.groups.filter(name=group).count() == 1
        if isinstance(group, Group):
            return self.groups.filter(name=group.name).count() == 1
        return False

    @cached_property
    def initials(self):
        """Return the initials of this user account.

        Returns:
            (str): User's initials derived from email address or name, or username
                  if initials cannot be determined.

        Notes:
            If the email username part contains dots, splits on dots and uses first
            character of each part. Otherwise, uses first character of first and
            last names, or falls back to username if insufficient information.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Account.initials)
                True

        """
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
        """Return True if the account manages other accounts.

        Returns:
            (bool): True if this account is a manager for at least one other account.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Account.is_supervisor)
                True

        """
        return self.managing.count() > 0

    @property
    def primary_project(self):
        """Return the primary project for this account.

        Returns:
            (CostCentre or None): The first project, or None if no projects.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Account.primary_project)
                True

        """
        if self.project.all().count() > 0:
            return self.project.all().first()
        return None

    def can_edit(self, other):
        """Check if another account can edit this account.

        Args:
            other (Account):
                The account attempting to edit this account.

        Returns:
            (bool): True if other is the same account, this account's manager,
                   or a superuser.

        Notes:
            There appears to be a typo in the implementation ('menager' instead
            of 'manager') which may cause this method to fail.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Account.can_edit)
                True

        """
        return other == self or other == self.menager or other.is_superuser


class Role(ResourceedObject):
    """Model representing user roles within the equipment management system.

            Roles define permission levels for equipment access, ranging from trainee
            to manager. Each role has a numeric level and associated CSS styling for
            display purposes.

    Attributes:
        level (IntegerField):
            Numeric level indicating the permission level (0=TRAINEE, 100=USER,
            200=ADVANCED_USER, 300=INSTRUCTOR, 1000=MANAGER).
        css (CharField):
            CSS classes for displaying the role in the interface.


    Examples:
        Inspect the public interface in an interactive session::

            >>> Role.__name__
            'Role'

    """

    class Meta:
        """Configure the Meta class."""

        ordering = ["level"]
        constraints = [models.UniqueConstraint(fields=["name"], name="Unique Role Name")]

    level = models.IntegerField(default=TRAINEE)
    css = models.CharField(max_length=40, default="bg-gradient bg-success text-white", verbose_name="CSS class")

    def __str__(self):
        """Return a string representation of the role.

        Returns:
            (str): The role name.

        """
        return self.name

    @classproperty
    def default(cls):
        """Fetch the role with the lowest access level.

        Returns:
            (Role): The trainee role object.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Role.default)
                True

        """
        return cls.objects.get(level=TRAINEE)

    @classproperty
    def trainee(cls):
        """Return the trainee role.

        Returns:
            (Role): The trainee role object.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Role.trainee)
                True

        """
        return cls.objects.get(level=TRAINEE)

    @classproperty
    def user(cls):
        """Return the user level role.

        Returns:
            (Role): The user role object.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Role.user)
                True

        """
        return cls.objects.get(level=USER)

    @classproperty
    def advanced_user(cls):
        """Return the advanced user level role.

        Returns:
            (Role): The advanced user role object.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Role.advanced_user)
                True

        """
        return cls.objects.get(level=ADVANCED_USER)

    @classproperty
    def instructor(cls):
        """Return the instructor role.

        Returns:
            (Role): The instructor role object.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Role.instructor)
                True

        """
        return cls.objects.get(level=INSTRUCTOR)

    @classproperty
    def manager(cls):
        """Return the manager role.

        Returns:
            (Role): The manager role object.


        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(Role.manager)
                True

        """
        return cls.objects.get(level=MANAGER)
