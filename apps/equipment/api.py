# -*- coding: utf-8 -*-
"""
Created on Sun Jun 25 16:21:16 2023

@author: phygbu
"""
# external imports
from accounts.api import AccountSerializer
from rest_framework import routers, serializers, viewsets

# app imports
from .models import Equipment, Location, UserListEntry


# Serializers define the API representation.
class UserListEntrySeriqlizer(serializers.ModelSerializer):
    class Meta:
        model = UserListEntry
        exclude = ["equipment"]
        depth = 1


class EquipmentSerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField("get_users")

    class Meta:
        model = Equipment
        fields = ["id", "name", "description", "owner", "photos", "files", "users"]
        depth = 10

    def get_users(self, equipment):
        return UserListEntrySeriqlizer(instance=equipment.users.all(), many=True).data


# Serializers define the API representation.
class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        exclude = []


# ViewSets define the view behavior.
# ViewSets define the view behavior.
class EquipmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer


class UserListEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserListEntry.objects.all()
    serializer_class = UserListEntrySeriqlizer


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


router = [
    (r"locations", LocationViewSet),
    ("user_list_entries", UserListEntryViewSet),
    (r"equipment_items", EquipmentViewSet),
]
