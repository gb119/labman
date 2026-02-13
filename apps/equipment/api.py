# -*- coding: utf-8 -*-
"""REST Framework endpoints for the equipment app.

This module defines serializers and viewsets for exposing Equipment, Location,
and UserListEntry objects through the Django REST Framework API.
"""
# external imports
from accounts.api import AccountSerializer
from rest_framework import routers, serializers, viewsets

# app imports
from .models import Equipment, Location, UserListEntry


class UserListEntrySeriqlizer(serializers.ModelSerializer):
    """Serializer for UserListEntry objects.

    Serializes user list entry data with nested relationships for API responses.

    Notes:
        The class name appears to have a typo ('Seriqlizer' instead of 'Serializer').
    """

    class Meta:
        model = UserListEntry
        exclude = ["equipment"]
        depth = 1


class EquipmentSerializer(serializers.ModelSerializer):
    """Serializer for Equipment objects.

    Serializes equipment data including users, photos, and files with deep
    nested relationships for comprehensive API responses.

    Attributes:
        users (SerializerMethodField):
            Custom field for serializing associated users.
    """

    users = serializers.SerializerMethodField("get_users")

    class Meta:
        model = Equipment
        fields = ["id", "name", "description", "owner", "photos", "files", "users"]
        depth = 10

    def get_users(self, equipment):
        """Get serialized user list entries for the equipment.

        Args:
            equipment (Equipment):
                The equipment instance being serialized.

        Returns:
            (list): List of serialized user list entry data.
        """
        return UserListEntrySeriqlizer(instance=equipment.users.all(), many=True).data


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location objects.

    Serializes all location fields for API responses.
    """

    class Meta:
        model = Location
        exclude = []


class EquipmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API viewset for Equipment objects.

    Provides list and detail views for equipment through the REST API.
    Supports standard REST operations: GET (list and detail).

    Attributes:
        queryset (QuerySet):
            All Equipment objects.
        serializer_class (class):
            EquipmentSerializer for object serialization.
    """

    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer


class UserListEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API viewset for UserListEntry objects.

    Provides list and detail views for user list entries through the REST API.
    Supports standard REST operations: GET (list and detail).

    Attributes:
        queryset (QuerySet):
            All UserListEntry objects.
        serializer_class (class):
            UserListEntrySeriqlizer for object serialization.
    """

    queryset = UserListEntry.objects.all()
    serializer_class = UserListEntrySeriqlizer


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API viewset for Location objects.

    Provides list and detail views for locations through the REST API.
    Supports standard REST operations: GET (list and detail).

    Attributes:
        queryset (QuerySet):
            All Location objects.
        serializer_class (class):
            LocationSerializer for object serialization.
    """

    queryset = Location.objects.all()
    serializer_class = LocationSerializer


router = [
    (r"locations", LocationViewSet),
    ("user_list_entries", UserListEntryViewSet),
    (r"equipment_items", EquipmentViewSet),
]
