# -*- coding: utf-8 -*-
"""Tests for the costings app.

This module tests the CostRate and CostCentre models, including creation,
string representations, hierarchical MPTT structure, and the default rate logic.
"""
# Django imports
import pytest


class TestCostRate:
    """Tests for the CostRate model."""

    @pytest.mark.django_db
    def test_create_cost_rate(self, cost_rate):
        """Creating a CostRate persists it to the database."""
        from costings.models import CostRate

        assert CostRate.objects.filter(name="standard").exists()

    @pytest.mark.django_db
    def test_str_returns_name(self, cost_rate):
        """__str__ returns the cost rate name."""
        assert str(cost_rate) == "standard"

    @pytest.mark.django_db
    def test_default_creates_standard(self):
        """CostRate.default() creates and returns a 'standard' rate."""
        from costings.models import CostRate

        rate = CostRate.default()
        assert rate.name == "standard"
        assert CostRate.objects.filter(name="standard").exists()

    @pytest.mark.django_db
    def test_default_returns_existing_standard(self, cost_rate):
        """CostRate.default() returns existing 'standard' rate without creating duplicate."""
        from costings.models import CostRate

        rate = CostRate.default()
        assert rate.pk == cost_rate.pk
        assert CostRate.objects.filter(name="standard").count() == 1


class TestCostCentre:
    """Tests for the CostCentre model."""

    @pytest.mark.django_db
    def test_create_cost_centre(self, cost_centre):
        """Creating a CostCentre persists it to the database."""
        from costings.models import CostCentre

        assert CostCentre.objects.filter(name="Test Project").exists()

    @pytest.mark.django_db
    def test_str_representation(self, cost_centre):
        """__str__ returns 'ShortName:Name (AccountCode)'."""
        expected = "TP:Test Project (ACC001)"
        assert str(cost_centre) == expected

    @pytest.mark.django_db
    def test_url_property(self, cost_centre):
        """url property returns the correct detail URL."""
        expected = f"/costings/cost_centre_detail/{cost_centre.pk}/"
        assert cost_centre.url == expected

    @pytest.mark.django_db
    def test_default_rate_assigned_on_save(self, db):
        """CostCentre.save() assigns default CostRate when none is given."""
        from costings.models import CostCentre, CostRate

        cc = CostCentre.objects.create(name="Rate Test CC", short_name="RTCC", account_code="ACC999")
        assert cc.rate is not None
        assert cc.rate.name == "standard"

    @pytest.mark.django_db
    def test_parent_child_hierarchy(self, cost_centre, db):
        """Creating a child CostCentre correctly sets the MPTT hierarchy."""
        from costings.models import CostCentre

        child = CostCentre.objects.create(
            name="Sub Project",
            short_name="SP",
            account_code="ACC002",
            parent=cost_centre,
        )
        assert child.parent == cost_centre
        assert child in cost_centre.get_descendants()

    @pytest.mark.django_db
    def test_children_property_includes_descendants(self, cost_centre, db):
        """children property returns all descendants including self."""
        from costings.models import CostCentre

        child = CostCentre.objects.create(
            name="Child CC",
            short_name="CCC",
            account_code="ACC003",
            parent=cost_centre,
        )
        children = list(cost_centre.children)
        assert child in children

    @pytest.mark.django_db
    def test_all_parents_property(self, cost_centre, db):
        """all_parents property returns ancestor chain including self."""
        from costings.models import CostCentre

        child = CostCentre.objects.create(
            name="Grandchild CC",
            short_name="GCC",
            account_code="ACC004",
            parent=cost_centre,
        )
        parents = list(child.all_parents)
        assert cost_centre in parents
        assert child in parents

    @pytest.mark.django_db
    def test_unique_name_constraint(self, cost_centre):
        """Creating a second CostCentre with the same name raises an error."""
        from costings.models import CostCentre
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            CostCentre.objects.create(name="Test Project", short_name="TP2", account_code="ACC099")
