# -*- coding: utf-8 -*-
"""Models for representing objects related to lab equipment items - documents, locations, and so forth."""
# Python imports
# Django imports
from django.db import models

# external imports
import numpy as np
from labman_utils.models import NamedObject
from sortedm2m.fields import SortedManyToManyField


class CostRate(NamedObject):
    """A model class to identify charging schemes."""

    @classmethod
    def default(cls):
        """Ensure we have a costing rate called 'standard.'"""
        std, _ = cls.objects.get_or_create(name="standard")
        if std.description == "":
            std.description = "A default costing rate."
            std.save()
        return std

    def __str__(self):
        """Just use self.name for the string representation."""
        return self.name


class CostCentre(NamedObject):
    """Handles a physical location or room."""

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name"], name="Unique Cost-centre Name"),
            models.UniqueConstraint(fields=["code"], name="Unique cost-centre Code"),
        ]
        ordering = ("-code",)

    locations = SortedManyToManyField("equipment.location", related_name="cost_centres", blank=True)
    equipment = SortedManyToManyField("equipment.equipment", related_name="cost_centres", blank=True)
    short_name = models.CharField(max_length=20)
    account_code = models.CharField(max_length=20)
    rate = models.ForeignKey(CostRate, on_delete=models.SET_NULL, null=True, blank=True)
    contact = models.ForeignKey(
        "accounts.Account", on_delete=models.CASCADE, related_name="managed_cost_centres", blank=True, null=True
    )
    super_cost_centre = models.ForeignKey(
        "CostCentre", on_delete=models.CASCADE, related_name="sub_cost_centres", null=True, blank=True
    )
    code = models.CharField(max_length=80, blank=True)
    level = models.IntegerField(default=None, editable=False, blank=True, null=True)

    @property
    def next_code(self):
        """Figure out a location code not based on pk."""
        peers = self.__class__.objects.filter(super_cost_centre=self.super_cost_centre).exclude(pk=self.pk)
        if peers.count() == 0:
            new = "1"
        else:
            codes = np.ravel(peers.values_list("code"))
            if self.super_cost_centre is not None:
                cut = len(self.super_cost_centre.code) + 1
            else:
                cut = 0
            codes = set([int(x[cut:]) for x in codes])
            possible = set(np.arange(1, max(codes) + 2))
            new = str(min(possible - codes))
        if self.super_cost_centre:
            return f"{self.super_cost_centre.code},{new}"
        return new

    @property
    def _code_regexp(self):
        """Create a regexp that will match all parent locations."""
        parts = self.code.split(",")
        if len(parts) <= 1:
            return self.code
        pat = ""
        for part in reversed(parts[1:]):
            pat = f"(,{part}{pat})?"
        return f"^{parts[0]}{pat}$"

    @property
    def all_parents(self):
        """Return a set of all locations that contain this location."""
        if self.level == 0:
            return self.__class__.objects.filter(code=self.code)
        return self.__class__.objects.filter(code__regex=self._code_regexp).order_by("-code")

    @property
    def children(self):
        """Return a set of all sub-locations of this location."""
        query = models.Q(code__regex=f"^{self.code}[^0-9]") | models.Q(code=self.code)
        return self.__class__.objects.filter(query).order_by("code")

    def __getattr__(self, name):
        """Code around all_* properties."""
        if not name.startswith("all_"):
            return super().__getrattr__(name)
        field = name[4:]
        if field not in self._meta.fields or not hasattr(getattr(self, field), "model"):
            return super().__getrattr__(name)

        linked = getattr(self, field)
        if hasattr(linked, "cost_centre"):
            search = {"cost_centre__in": self.all_parents}
        elif hasattr(linked, "project"):
            search = {"project__in": self.all_parents}

        return linked.objects.filter(**search)

    def __str__(self):
        """Make a better string representation."""
        return f"{self.short_name}:{self.name} ({self.account_code})"

    @property
    def url(self):
        """Return a URL for the detail page of this location."""
        return f"/costings/cost_centre_detail/{self.pk}/"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """Force the cost_centre code to be calculated and then upodate any sub_locations."""
        if self.pk is None:  # Update our pk
            super().save(
                force_insert=force_insert,
                force_update=force_update,
                using=using,
                update_fields=update_fields,
            )
        if self.rate is None:
            self.rate = CostRate.default()
        self.code = self.next_code
        self.level = self.code.count(",")
        super().save(update_fields=update_fields)
        for sub in self.sub_cost_centres.all():
            sub.save()


class ChargeableItgem(models.Model):
    """Base class to represent a single use of a charable resource."""

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
