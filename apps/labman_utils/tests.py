# -*- coding: utf-8 -*-
"""Tests for the labman_utils app.

This module tests utility functions and model functionality from the labman_utils
application, including time conversion helpers, the ObfuscatedCharField decoding
logic, and the NamedObject base model.
"""
# Python imports
import base64
import codecs
from datetime import datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import Mock


class TestIsAuthenticatedViewMixin:
    """Tests for redirects from views that require authentication."""

    def test_uses_configured_login_url(self):
        """Anonymous requests are sent into the configured ADFS flow."""
        # Django imports
        from django.contrib.auth.models import AnonymousUser
        from django.http import HttpResponse
        from django.test import RequestFactory, override_settings
        from django.views import View

        # external imports
        from labman_utils.views import IsAuthenticaedViewMixin

        class ProtectedView(IsAuthenticaedViewMixin, View):
            """Provide the ProtectedView implementation."""

            def get(self, request):
                """Perform the get operation."""
                return HttpResponse()

        request = RequestFactory().get("/protected/")
        request.user = AnonymousUser()

        with override_settings(LOGIN_URL="django_auth_adfs:login"):
            response = ProtectedView.as_view()(request)

        assert response.status_code == 302
        assert response.url == "/oauth2/login?next=/protected/"


class TestResourceEditingPermissions:
    """Tests for the shared content-editing permission rules."""

    @staticmethod
    def _user(*, superuser=False, editor_group=False):
        """Build a mock account with configurable editing privileges."""
        user = Mock(is_authenticated=True, is_superuser=superuser)
        user.groups.filter.return_value.exists.return_value = editor_group
        return user

    def test_academic_or_staff_group_members_are_editors(self):
        """Academic and Staff group membership grants general editing access."""
        # external imports
        from labman_utils.views import is_academic_or_staff

        user = self._user(editor_group=True)

        assert is_academic_or_staff(user)
        user.groups.filter.assert_called_once_with(name__in=("Academic", "Staff"))

    def test_equipment_manager_can_edit_linked_resource(self):
        """An equipment owner or manager can edit a resource linked to their equipment."""
        # external imports
        from labman_utils.views import can_edit_equipment_resource

        user = self._user()
        equipment = Mock()
        equipment.can_edit.return_value = True
        resource = SimpleNamespace(equipment=Mock())
        resource.equipment.all.return_value = [equipment]

        assert can_edit_equipment_resource(user, resource)

    def test_unrelated_account_cannot_edit_linked_resource(self):
        """An unrelated authenticated account cannot edit an equipment resource."""
        # external imports
        from labman_utils.views import can_edit_equipment_resource

        user = self._user()
        equipment = Mock()
        equipment.can_edit.return_value = False
        resource = SimpleNamespace(equipment=Mock())
        resource.equipment.all.return_value = [equipment]

        assert not can_edit_equipment_resource(user, resource)

    def test_unrelated_account_cannot_delete_photo(self):
        """A non-editor who does not manage the equipment cannot delete its photo."""
        # external imports
        from labman_utils.views import PhotoDialog

        user = self._user()
        equipment = Mock()
        equipment.can_edit.return_value = False
        photo = Mock()
        photo.equipment.all.return_value = [equipment]
        view = PhotoDialog()
        view.request = SimpleNamespace(user=user)
        view.get_object = Mock(return_value=photo)

        response = view.htmx_delete_photo(view.request)

        assert response.status_code == 403
        photo.delete.assert_not_called()


class TestToSeconds:
    """Tests for the to_seconds utility function."""

    def test_midnight(self):
        """to_seconds returns 0 for midnight."""
        # external imports
        from labman_utils.models import to_seconds

        assert to_seconds(time(0, 0, 0)) == 0

    def test_one_hour(self):
        """to_seconds returns 3600 for 01:00:00."""
        # external imports
        from labman_utils.models import to_seconds

        assert to_seconds(time(1, 0, 0)) == 3600

    def test_one_minute(self):
        """to_seconds returns 60 for 00:01:00."""
        # external imports
        from labman_utils.models import to_seconds

        assert to_seconds(time(0, 1, 0)) == 60

    def test_one_second(self):
        """to_seconds returns 1 for 00:00:01."""
        # external imports
        from labman_utils.models import to_seconds

        assert to_seconds(time(0, 0, 1)) == 1

    def test_noon(self):
        """to_seconds returns 43200 for 12:00:00."""
        # external imports
        from labman_utils.models import to_seconds

        assert to_seconds(time(12, 0, 0)) == 43200

    def test_with_datetime(self):
        """to_seconds works with datetime objects using the time component."""
        # external imports
        from labman_utils.models import to_seconds

        dt_val = datetime(2024, 1, 15, 9, 30, 0)
        assert to_seconds(dt_val) == 9 * 3600 + 30 * 60


class TestDeltaT:
    """Tests for the delta_t utility function."""

    def test_positive_difference(self):
        """delta_t returns positive timedelta when time1 > time2."""
        # external imports
        from labman_utils.models import delta_t

        result = delta_t(time(12, 0), time(9, 0))
        assert result == timedelta(hours=3)

    def test_zero_difference(self):
        """delta_t returns zero timedelta when times are equal."""
        # external imports
        from labman_utils.models import delta_t

        result = delta_t(time(10, 0), time(10, 0))
        assert result == timedelta(0)

    def test_negative_difference(self):
        """delta_t returns negative timedelta when time1 < time2."""
        # external imports
        from labman_utils.models import delta_t

        result = delta_t(time(9, 0), time(12, 0))
        assert result == timedelta(hours=-3)

    def test_with_datetime_objects(self):
        """delta_t extracts time from datetime objects before computing difference."""
        # external imports
        from labman_utils.models import delta_t

        dt1 = datetime(2024, 1, 15, 14, 0, 0)
        dt2 = datetime(2024, 1, 10, 12, 0, 0)
        result = delta_t(dt1, dt2)
        assert result == timedelta(hours=2)


class TestEnsureTz:
    """Tests for the ensure_tz utility function."""

    def test_naive_datetime_gets_timezone(self):
        """ensure_tz adds DEFAULT_TZ to a naive datetime."""
        # external imports
        from labman_utils.models import ensure_tz

        naive = datetime(2024, 6, 15, 10, 0, 0)
        result = ensure_tz(naive)
        assert result.tzinfo is not None

    def test_aware_datetime_unchanged(self):
        """ensure_tz returns an already-aware datetime unchanged."""
        # external imports
        import pytz
        from labman_utils.models import ensure_tz

        tz = pytz.utc
        aware = tz.localize(datetime(2024, 6, 15, 10, 0, 0))
        result = ensure_tz(aware)
        assert result == aware


class TestObfuscatedCharField:
    """Tests for the ObfuscatedCharField decoding logic."""

    @staticmethod
    def _encode(text):
        """Encode text mirroring the JavaScript client: ROT13(Base64(text))."""
        base64_text = base64.b64encode(text.encode("utf-8")).decode("ascii")
        return f"ROT13+B64:{codecs.encode(base64_text, 'rot_13')}"

    def test_valid_encoded_value_decoded(self):
        """to_python decodes a properly Base64+ROT13 encoded value."""
        # external imports
        from labman_utils.fields import ObfuscatedCharField

        field = ObfuscatedCharField()
        plain = "<p>Hello world</p>"
        encoded = self._encode(plain)
        result = field.to_python(encoded)
        assert "Hello world" in result

    def test_plain_text_passthrough(self):
        """to_python returns plain text unchanged when it is not valid Base64."""
        # external imports
        from labman_utils.fields import ObfuscatedCharField

        field = ObfuscatedCharField()
        plain = "just plain text !!!"
        result = field.to_python(plain)
        assert result == plain

    def test_empty_string_passthrough(self):
        """to_python handles an empty string without raising."""
        # external imports
        from labman_utils.fields import ObfuscatedCharField

        field = ObfuscatedCharField()
        result = field.to_python("")
        assert result == ""

    def test_html_sanitised(self):
        """to_python strips disallowed HTML tags from decoded content."""
        # external imports
        from labman_utils.fields import ObfuscatedCharField

        field = ObfuscatedCharField()
        dangerous = "<p>Safe</p><script>alert('xss')</script>"
        encoded = self._encode(dangerous)
        result = field.to_python(encoded)
        assert "<script>" not in result
        assert "Safe" in result


class TestDocumentLinkDialogInitialValues:
    """Tests for initial values used by the document-linking forms."""

    def test_equipment_form_uses_standard_model_form_initial_values(self):
        """Equipment linking delegates initial-value handling to UpdateView."""
        # external imports
        from labman_utils.views import DocumentLinkDialog

        view = DocumentLinkDialog()
        view.kwargs = {"equipment": 42}
        view.initial = {"sentinel": "value"}

        assert view.get_initial() == {"sentinel": "value"}

    def test_document_form_populates_existing_reverse_links(self):
        """Document linking includes its current equipment and location links."""
        # external imports
        from labman_utils.views import DocumentLinkDialog

        equipment = [object()]
        locations = [object()]
        document = SimpleNamespace(
            id=42,
            equipment=Mock(all=Mock(return_value=equipment)),
            location=Mock(all=Mock(return_value=locations)),
        )
        view = DocumentLinkDialog()
        view.kwargs = {"pk": document.id}
        view.get_object = Mock(return_value=document)

        assert view.get_initial() == {
            "id": document.id,
            "equipment": equipment,
            "location": locations,
        }
