# -*- coding: utf-8 -*-
"""Tests for the costings app.

This module tests the CostRate and CostCentre models including creation,
string representations, hierarchical MPTT structure, and the default rate logic,
as well as the costings views.
"""
# Python imports
import inspect
from datetime import date
from unittest.mock import Mock, patch

# Django imports
from django.db import models
from django.db.backends.postgresql.psycopg_any import DateRange
from django.urls import reverse

# external imports
import pytest


class TestCostRate:
    """Tests for the CostRate model."""

    @pytest.mark.django_db
    def test_create_cost_rate(self, cost_rate):
        """Creating a CostRate persists it to the database."""
        # external imports
        from costings.models import CostRate

        assert CostRate.objects.filter(name="standard").exists()

    @pytest.mark.django_db
    def test_str_returns_name(self, cost_rate):
        """__str__ returns the cost rate name."""
        assert str(cost_rate) == "standard"

    @pytest.mark.django_db
    def test_default_creates_standard(self):
        """CostRate.default() creates and returns a 'standard' rate."""
        # external imports
        from costings.models import CostRate

        rate = CostRate.default()
        assert rate.name == "standard"
        assert CostRate.objects.filter(name="standard").exists()

    @pytest.mark.django_db
    def test_default_returns_existing_standard(self, cost_rate):
        """CostRate.default() returns existing 'standard' rate without creating duplicate."""
        # external imports
        from costings.models import CostRate

        rate = CostRate.default()
        assert rate.pk == cost_rate.pk
        assert CostRate.objects.filter(name="standard").count() == 1


class TestCostCentre:
    """Tests for the CostCentre model."""

    @pytest.mark.django_db
    def test_create_cost_centre(self, cost_centre):
        """Creating a CostCentre persists it to the database."""
        # external imports
        from costings.models import CostCentre

        assert CostCentre.objects.filter(name="Test Project").exists()

    @pytest.mark.django_db
    def test_str_representation(self, cost_centre):
        """__str__ returns 'ShortName:Name (AccountCode)'."""
        expected = "TP:Test Project (ACC001)"
        assert str(cost_centre) == expected

    @pytest.mark.django_db
    def test_url_property(self, cost_centre):
        """Verify that url property returns the correct detail URL."""
        expected = f"/costings/cost_centre_detail/{cost_centre.pk}/"
        assert cost_centre.url == expected

    @pytest.mark.django_db
    def test_default_rate_assigned_on_save(self, db):
        """CostCentre.save() assigns default CostRate when none is given."""
        # external imports
        from costings.models import CostCentre

        cc = CostCentre.objects.create(name="Rate Test CC", short_name="RTCC", account_code="ACC999")
        assert cc.rate is not None
        assert cc.rate.name == "standard"

    @pytest.mark.django_db
    def test_parent_child_hierarchy(self, cost_centre, db):
        """Creating a child CostCentre correctly sets the MPTT hierarchy."""
        # external imports
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
        """Verify that children property returns all descendants including self."""
        # external imports
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
        # external imports
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
        # Django imports
        from django.db import IntegrityError

        # external imports
        from costings.models import CostCentre

        with pytest.raises(IntegrityError):
            CostCentre.objects.create(name="Test Project", short_name="TP2", account_code="ACC099")


class TestModelSaveContracts:
    """Tests for custom model save signatures and derived charge fields."""

    def test_overrides_accept_django_positional_save_arguments(self):
        """Every custom save override retains Django's transitional ``*args`` contract."""
        # external imports
        from accounts.models import ResearchGroup
        from bookings.models import BookingEntry
        from costings.models import ChargeableItem, CostCentre
        from equipment.models import (
            ChargingRate,
            DocumentSignOff,
            UserListEntry,
        )
        from labman_utils.models import Document

        overrides = (
            ResearchGroup.save,
            BookingEntry.save,
            ChargeableItem.save,
            CostCentre.save,
            ChargingRate.save,
            DocumentSignOff.save,
            UserListEntry.save,
            Document.save,
        )

        for save in overrides:
            parameters = inspect.signature(save).parameters.values()
            assert any(parameter.kind is inspect.Parameter.VAR_POSITIONAL for parameter in parameters)

    def test_chargeable_item_assigns_default_cost_centre(self):
        """ChargeableItem.save stores its default in the correctly named field."""
        # external imports
        from bookings.models import BookingEntry
        from costings.models import ChargeableItem, CostCentre

        booking = BookingEntry()
        default_cost_centre = CostCentre()
        booking.calculate_charge = lambda: 12.5
        booking.get_default_cost_centre = lambda: default_cost_centre

        with patch.object(models.Model, "save", autospec=True):
            ChargeableItem.save(booking)

        assert booking.charge == 12.5
        assert booking.cost_centre is default_cost_centre

    def test_charging_rate_rollover_saves_existing_rate_without_positional_arguments(self):
        """ChargingRate.save closes an old range with a normal model save."""
        # external imports
        from equipment.models import ChargingRate

        old_rate = Mock(dates=DateRange(date(2025, 1, 1), date(2026, 1, 1)))
        new_rate = ChargingRate(
            equipment_id=1,
            cost_rate_id=1,
            charge_rate=10.0,
            dates=DateRange(date(2025, 6, 1), date(2026, 6, 1)),
        )
        new_rate._state.fields_cache["equipment"] = Mock()
        new_rate._state.fields_cache["cost_rate"] = Mock()

        with (
            patch.object(ChargingRate.objects, "get", return_value=old_rate),
            patch.object(models.Model, "save", autospec=True),
        ):
            new_rate.save()

        old_rate.save.assert_called_once_with()


class TestCostingsViews:
    """Integration tests for costings app views."""

    @pytest.mark.django_db
    def test_cost_centre_filter_view_requires_login(self, client):
        """Unauthenticated requests to Cost_CentreView redirect to login."""
        url = reverse("costings:cost_centre_filter")
        response = client.get(url)
        assert response.status_code in (302, 301)
        assert response["Location"].startswith(f"{reverse('core_login')}?")

    @pytest.mark.django_db
    def test_cost_centre_filter_view_returns_200_via_htmx(self, client_logged_in):
        """Cost_CentreView returns 200 when called via HTMX with id_cost_centre trigger."""
        url = reverse("costings:cost_centre_filter")
        response = client_logged_in.get(url, HTTP_HX_REQUEST="true", HTTP_HX_TRIGGER_NAME="id_cost_centre")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_new_cost_centre_dialog_requires_superuser(self, client_logged_in):
        """Verify that CostCentreDialog (new) redirects non-superusers."""
        url = reverse("costings:new_cost_centre")
        response = client_logged_in.get(url)
        assert response.status_code in (302, 301, 403)

    @pytest.mark.django_db
    def test_new_cost_centre_dialog_accessible_to_superuser(self, client_superuser):
        """Verify that CostCentreDialog (new) is accessible to superusers."""
        url = reverse("costings:new_cost_centre")
        response = client_superuser.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_edit_cost_centre_dialog_accessible_to_superuser(self, client_superuser, cost_centre):
        """Verify that CostCentreDialog (edit) is accessible to superusers."""
        url = reverse("costings:edit_cost_centre", kwargs={"pk": cost_centre.pk})
        response = client_superuser.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_new_cost_centre_dialog_requires_login(self, client):
        """Unauthenticated requests to CostCentreDialog redirect to login."""
        url = reverse("costings:new_cost_centre")
        response = client.get(url)
        assert response.status_code in (302, 301)
        assert response["Location"].startswith(f"{reverse('core_login')}?")

    @pytest.mark.django_db
    def test_cost_centre_full_description_context_via_htmx(self, client_logged_in, cost_centre):
        """Cost_CentreView returns the full description context for a valid cost_centre_id."""
        url = reverse("costings:cost_centre_filter")
        response = client_logged_in.get(
            url,
            {"cost_centre_id": cost_centre.pk},
            HTTP_HX_REQUEST="true",
            HTTP_HX_TRIGGER_NAME="full_description",
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_cost_centre_full_description_invalid_id(self, client_logged_in):
        """Cost_CentreView handles an invalid cost_centre_id gracefully."""
        url = reverse("costings:cost_centre_filter")
        response = client_logged_in.get(
            url,
            {"cost_centre_id": 99999},
            HTTP_HX_REQUEST="true",
            HTTP_HX_TRIGGER_NAME="full_description",
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_delete_cost_centre_forbidden_for_regular_user(self, client_logged_in, cost_centre):
        """htmx_delete_costcentre returns 403 for a non-superuser."""
        url = reverse("costings:edit_cost_centre", kwargs={"pk": cost_centre.pk})
        response = client_logged_in.delete(
            url,
            HTTP_HX_REQUEST="true",
            HTTP_HX_TRIGGER_NAME="costcentre",
        )
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_delete_cost_centre_succeeds_for_superuser(self, client_superuser, cost_centre):
        """htmx_delete_costcentre deletes the cost centre and returns 204 for a superuser."""
        # external imports
        from costings.models import CostCentre

        pk = cost_centre.pk
        url = reverse("costings:edit_cost_centre", kwargs={"pk": pk})
        response = client_superuser.delete(
            url,
            HTTP_HX_REQUEST="true",
            HTTP_HX_TRIGGER_NAME="costcentre",
        )
        assert response.status_code == 204
        assert not CostCentre.objects.filter(pk=pk).exists()
