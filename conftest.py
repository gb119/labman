# -*- coding: utf-8 -*-
"""Root conftest.py providing shared pytest fixtures for the labman test suite.

This module defines fixtures that create test instances of the main models used
across the labman application. All fixtures that require database access are
marked with the ``django_db`` marker through the ``db`` fixture dependency.
"""
# Python imports
from datetime import time

# Django imports
import pytest


@pytest.fixture
def research_group(db):
    """Create and return a test ResearchGroup instance.

    Args:
        db: pytest-django database fixture.

    Returns:
        (ResearchGroup): A saved ResearchGroup with code 'TEST'.
    """
    from accounts.models import ResearchGroup

    return ResearchGroup.objects.create(code="TEST", name="Test Group")


@pytest.fixture
def superuser(db):
    """Create and return a superuser Account instance.

    Args:
        db: pytest-django database fixture.

    Returns:
        (Account): A saved superuser account with username 'admin'.
    """
    from accounts.models import Account

    return Account.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="testpassword123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def regular_user(db, research_group):
    """Create and return a regular (non-staff) Account instance.

    Args:
        db: pytest-django database fixture.
        research_group (ResearchGroup): The research group to assign.

    Returns:
        (Account): A saved regular user account with username 'testuser'.
    """
    from accounts.models import Account

    return Account.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpassword123",
        first_name="Test",
        last_name="User",
        research_group=research_group,
    )


@pytest.fixture
def cost_rate(db):
    """Create and return a test CostRate instance.

    Args:
        db: pytest-django database fixture.

    Returns:
        (CostRate): A saved CostRate with name 'standard'.
    """
    from costings.models import CostRate

    rate, _ = CostRate.objects.get_or_create(name="standard", defaults={"description": "Standard rate"})
    return rate


@pytest.fixture
def cost_centre(db, cost_rate, regular_user):
    """Create and return a test CostCentre instance.

    Args:
        db: pytest-django database fixture.
        cost_rate (CostRate): The charging rate to assign.
        regular_user (Account): The contact account.

    Returns:
        (CostCentre): A saved CostCentre with name 'Test Project'.
    """
    from costings.models import CostCentre

    return CostCentre.objects.create(
        name="Test Project",
        short_name="TP",
        account_code="ACC001",
        rate=cost_rate,
        contact=regular_user,
    )


@pytest.fixture
def location(db):
    """Create and return a top-level test Location instance.

    Args:
        db: pytest-django database fixture.

    Returns:
        (Location): A saved top-level Location with name 'Test Lab'.
    """
    from equipment.models import Location

    return Location.objects.create(name="Test Lab")


@pytest.fixture
def child_location(db, location):
    """Create and return a child Location nested under ``location``.

    Args:
        db: pytest-django database fixture.
        location (Location): The parent location.

    Returns:
        (Location): A saved child Location with name 'Test Room'.
    """
    from equipment.models import Location

    return Location.objects.create(name="Test Room", parent=location)


@pytest.fixture
def shift(db):
    """Create and return a test Shift instance.

    Args:
        db: pytest-django database fixture.

    Returns:
        (Shift): A saved Shift covering 09:00–17:00.
    """
    from equipment.models import Shift

    return Shift.objects.create(name="Day Shift", start_time=time(9, 0), end_time=time(17, 0))


@pytest.fixture
def role_trainee(db):
    """Create and return a trainee Role instance.

    Args:
        db: pytest-django database fixture.

    Returns:
        (Role): A saved Role at trainee level (0).
    """
    from accounts.models import Role

    role, _ = Role.objects.get_or_create(name="Trainee", defaults={"level": 0})
    return role


@pytest.fixture
def role_user(db):
    """Create and return a user Role instance.

    Args:
        db: pytest-django database fixture.

    Returns:
        (Role): A saved Role at user level (100).
    """
    from accounts.models import Role

    role, _ = Role.objects.get_or_create(name="User", defaults={"level": 100})
    return role


@pytest.fixture
def equipment(db, location, regular_user):
    """Create and return a test Equipment instance.

    Args:
        db: pytest-django database fixture.
        location (Location): The location for the equipment.
        regular_user (Account): The owner of the equipment.

    Returns:
        (Equipment): A saved Equipment item named 'Test Instrument'.
    """
    from equipment.models import Equipment

    return Equipment.objects.create(
        name="Test Instrument",
        location=location,
        owner=regular_user,
        category="characterisation",
    )


@pytest.fixture
def client_logged_in(client, regular_user):
    """Return a Django test client logged in as the regular user.

    Args:
        client: pytest-django client fixture.
        regular_user (Account): The user to log in as.

    Returns:
        (Client): A Django test client with an active session.
    """
    client.force_login(regular_user)
    return client


@pytest.fixture
def client_superuser(client, superuser):
    """Return a Django test client logged in as the superuser.

    Args:
        client: pytest-django client fixture.
        superuser (Account): The superuser account.

    Returns:
        (Client): A Django test client logged in as superuser.
    """
    client.force_login(superuser)
    return client
