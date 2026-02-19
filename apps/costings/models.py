# -*- coding: utf-8 -*-
"""Models for cost centres and charging rates.

This module defines models for managing financial aspects of laboratory equipment
and resources, including cost centres, charging rates, and chargeable items.
"""
# Python imports
# Django imports
from django.db import models

# external imports
import numpy as np
from labman_utils.models import NamedObject
from mptt.models import MPTTModel, TreeForeignKey
from sortedm2m.fields import SortedManyToManyField


class CostRate(NamedObject):
    """Model representing a charging scheme for equipment usage.

    Cost rates define different pricing structures that can be applied to
    equipment or resources. A default 'standard' rate is always available.
    """

    @classmethod
    def default(cls):
        """Get or create the default 'standard' cost rate.

        Returns:
            (CostRate): The standard cost rate object.

        Notes:
            Creates the 'standard' rate if it doesn't exist, and sets a default
            description if the description is empty.
        """
        std, _ = cls.objects.get_or_create(name="standard")
        if std.description == "":
            std.description = "A default costing rate."
            std.save()
        return std

    def __str__(self):
        """Return a string representation of the cost rate.

        Returns:
            (str): The cost rate name.
        """
        return self.name


class CostCentre(MPTTModel, NamedObject):
    """Model representing a cost centre for financial tracking and organisation.

    Cost centres represent organisational units that can be charged for equipment
    and resource usage. They support hierarchical structures and can be associated
    with locations and equipment. Uses django-mptt for efficient tree management.

    Attributes:
        locations (SortedManyToManyField):
            Physical locations associated with this cost centre.
        equipment (SortedManyToManyField):
            Equipment items associated with this cost centre.
        short_name (CharField):
            Abbreviated name for the cost centre (max 20 characters).
        account_code (CharField):
            Financial account code (max 20 characters).
        rate (ForeignKey):
            Charging rate applied to this cost centre.
        contact (ForeignKey):
            Account responsible for managing this cost centre.
        parent (TreeForeignKey):
            Parent cost centre in the hierarchy.
    """

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name"], name="Unique Cost-centre Name"),
        ]
        ordering = ["tree_id", "lft"]

    class MPTTMeta:
        order_insertion_by = ["name"]

    locations = SortedManyToManyField("equipment.location", related_name="cost_centres", blank=True)
    equipment = SortedManyToManyField("equipment.equipment", related_name="cost_centres", blank=True)
    short_name = models.CharField(max_length=20)
    account_code = models.CharField(max_length=20)
    rate = models.ForeignKey(CostRate, on_delete=models.SET_NULL, null=True, blank=True)
    contact = models.ForeignKey(
        "accounts.Account", on_delete=models.CASCADE, related_name="managed_cost_centres", blank=True, null=True
    )
    parent = TreeForeignKey("self", on_delete=models.CASCADE, related_name="direct_children", null=True, blank=True)

    @property
    def all_parents(self):
        """Return all cost centres that are parents of this cost centre.

        Returns:
            (QuerySet): Cost centres that contain this cost centre in the hierarchy.
        """
        # Use MPTT get_ancestors with include_self=True
        return self.get_ancestors(include_self=True)

    @property
    def children(self):
        """Return all sub-cost centres of this cost centre.

        This property returns a QuerySet that can be iterated directly in templates
        without calling .all().

        Returns:
            (QuerySet): All descendant cost centres in the hierarchy including self.

        Examples:
            Can be used directly in templates::

                {% for cc in cost_centre.children %}
                    {{ cc.name }}
                {% endfor %}

        Notes:
            This returns all descendants including self via MPTT's get_descendants().
            For direct children only, access the reverse relation via
            `self.direct_children.all()`.
        """
        # Use MPTT get_descendants with include_self=True
        return self.get_descendants(include_self=True)

    def __getattr__(self, name):
        """Provide dynamic access to all related objects in the hierarchy.

        Args:
            name (str):
                Attribute name. If starting with 'all_', returns related objects
                from this cost centre and all parent cost centres.

        Returns:
            (QuerySet): Related objects across the hierarchy.

        Raises:
            AttributeError: If the attribute doesn't exist or doesn't start with 'all_'.
        """
        if not name.startswith("all_"):
            return super().__getrattr__(name)
        field = name[4:]
        if field not in self._meta.fields or not hasattr(getattr(self, field), "model"):
            return super().__getrattr__(name)

        linked = getattr(self, field)
        if hasattr(linked, "cost_centre"):
            search = {"cost_centre__in": self.all_parents.all()}
        elif hasattr(linked, "project"):
            search = {"project__in": self.all_parents.all()}

        return linked.objects.filter(**search)

    def __str__(self):
        """Return a string representation of the cost centre.

        Returns:
            (str): String in the format "ShortName:Name (AccountCode)".
        """
        return f"{self.short_name}:{self.name} ({self.account_code})"

    @property
    def url(self):
        """Return the URL for the detail page of this cost centre.

        Returns:
            (str): URL path to the cost centre detail page.
        """
        return f"/costings/cost_centre_detail/{self.pk}/"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """Save the cost centre, assigning default rate if needed.

        Keyword Parameters:
            force_insert (bool):
                Force an INSERT operation.
            force_update (bool):
                Force an UPDATE operation.
            using (str):
                Database alias to use.
            update_fields (list):
                List of field names to update.

        Notes:
            If no rate is specified, assigns the default rate. MPTT handles
            tree structure updates automatically.
        """
        if self.rate is None:
            self.rate = CostRate.default()
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class ChargeableItem(models.Model):
    """Base class for representing a single use of a chargeable resource.

    This abstract model provides common fields for tracking resource usage
    that should be charged to cost centres.

    Attributes:
        cost_centre (ForeignKey):
            The cost centre to charge for this usage.
        ledger_date (DateField):
            Date when the charge was recorded (auto-set on creation).
        charge (FloatField):
            The amount to charge for this usage.

    Notes:
        This is an abstract model. Concrete models should inherit from this
        class and add specific fields for the type of resource being charged.
    """

    class Meta:
        abstract = True

    cost_centre = models.ForeignKey(
        CostCentre, on_delete=models.SET_NULL, related_name="%(class)s_charges", blank=True, null=True
    )
    ledger_date = models.DateField(auto_now_add=True)
    charge = models.FloatField(blank=True)
    comment = models.CharField(max_length=80, blank=True, null=True)

    def calculate_charge(self):
        """Calculate the charge to be applied for this istem."""
        raise NotImplementedError(f"{self.__class__.__name__} should implement a calculate_charge method!")

    def get_default_cost_centre(self):
        """Return a default cost_centre for this item."""
        raise NotImplementedError(f"{self.__class__.__name__} should have implemented get_default_cost_centre method")

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """Enforce charge calculation and cost_centre allocation."""
        self.charge = self.calculate_charge()
        if not self.cost_centre:
            self.const_centre = self.get_default_cost_centre()
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
