# -*- coding: utf-8 -*-
"""Tests for the labman_utils app.

This module tests utility functions and model functionality from the labman_utils
application, including time conversion helpers, the ObfuscatedCharField decoding
logic, and the NamedObject base model.
"""
# Python imports
import base64
import codecs
from datetime import date, datetime, time, timedelta

# Django imports
import pytest


class TestToSeconds:
    """Tests for the to_seconds utility function."""

    def test_midnight(self):
        """to_seconds returns 0 for midnight."""
        from labman_utils.models import to_seconds

        assert to_seconds(time(0, 0, 0)) == 0

    def test_one_hour(self):
        """to_seconds returns 3600 for 01:00:00."""
        from labman_utils.models import to_seconds

        assert to_seconds(time(1, 0, 0)) == 3600

    def test_one_minute(self):
        """to_seconds returns 60 for 00:01:00."""
        from labman_utils.models import to_seconds

        assert to_seconds(time(0, 1, 0)) == 60

    def test_one_second(self):
        """to_seconds returns 1 for 00:00:01."""
        from labman_utils.models import to_seconds

        assert to_seconds(time(0, 0, 1)) == 1

    def test_noon(self):
        """to_seconds returns 43200 for 12:00:00."""
        from labman_utils.models import to_seconds

        assert to_seconds(time(12, 0, 0)) == 43200

    def test_with_datetime(self):
        """to_seconds works with datetime objects using the time component."""
        from labman_utils.models import to_seconds

        dt_val = datetime(2024, 1, 15, 9, 30, 0)
        assert to_seconds(dt_val) == 9 * 3600 + 30 * 60


class TestDeltaT:
    """Tests for the delta_t utility function."""

    def test_positive_difference(self):
        """delta_t returns positive timedelta when time1 > time2."""
        from labman_utils.models import delta_t

        result = delta_t(time(12, 0), time(9, 0))
        assert result == timedelta(hours=3)

    def test_zero_difference(self):
        """delta_t returns zero timedelta when times are equal."""
        from labman_utils.models import delta_t

        result = delta_t(time(10, 0), time(10, 0))
        assert result == timedelta(0)

    def test_negative_difference(self):
        """delta_t returns negative timedelta when time1 < time2."""
        from labman_utils.models import delta_t

        result = delta_t(time(9, 0), time(12, 0))
        assert result == timedelta(hours=-3)

    def test_with_datetime_objects(self):
        """delta_t extracts time from datetime objects before computing difference."""
        from labman_utils.models import delta_t

        dt1 = datetime(2024, 1, 15, 14, 0, 0)
        dt2 = datetime(2024, 1, 10, 12, 0, 0)
        result = delta_t(dt1, dt2)
        assert result == timedelta(hours=2)


class TestEnsureTz:
    """Tests for the ensure_tz utility function."""

    def test_naive_datetime_gets_timezone(self):
        """ensure_tz adds DEFAULT_TZ to a naive datetime."""
        from labman_utils.models import DEFAULT_TZ, ensure_tz

        naive = datetime(2024, 6, 15, 10, 0, 0)
        result = ensure_tz(naive)
        assert result.tzinfo is not None

    def test_aware_datetime_unchanged(self):
        """ensure_tz returns an already-aware datetime unchanged."""
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
        return codecs.encode(base64_text, "rot_13")

    def test_valid_encoded_value_decoded(self):
        """to_python decodes a properly Base64+ROT13 encoded value."""
        from labman_utils.fields import ObfuscatedCharField

        field = ObfuscatedCharField()
        plain = "<p>Hello world</p>"
        encoded = self._encode(plain)
        result = field.to_python(encoded)
        assert "Hello world" in result

    def test_plain_text_passthrough(self):
        """to_python returns plain text unchanged when it is not valid Base64."""
        from labman_utils.fields import ObfuscatedCharField

        field = ObfuscatedCharField()
        plain = "just plain text !!!"
        result = field.to_python(plain)
        assert result == plain

    def test_empty_string_passthrough(self):
        """to_python handles an empty string without raising."""
        from labman_utils.fields import ObfuscatedCharField

        field = ObfuscatedCharField()
        result = field.to_python("")
        assert result == ""

    def test_html_sanitised(self):
        """to_python strips disallowed HTML tags from decoded content."""
        from labman_utils.fields import ObfuscatedCharField

        field = ObfuscatedCharField()
        dangerous = "<p>Safe</p><script>alert('xss')</script>"
        encoded = self._encode(dangerous)
        result = field.to_python(encoded)
        assert "<script>" not in result
        assert "Safe" in result
