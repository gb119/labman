#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REST Framework endpoints for the accounts app.

This module defines serializers and viewsets for exposing Account, ResearchGroup,
Role, and Group objects through the Django REST Framework API.
"""

# Django imports
from django.contrib.auth.models import Group

# external imports
from rest_framework import serializers, viewsets

# app imports
from .models import Account, ResearchGroup, Role


class ResearchGroupSerializer(serializers.ModelSerializer):
    """Serializer for ResearchGroup objects.

    Serializes research group data including name and code fields for API responses.
    """

    class Meta:
        model = ResearchGroup
        fields = ("name", "code")


class AccountSerializer(serializers.ModelSerializer):
    """Serializer for Account objects.

    Serializes user account data including username, title, names, and email for
    API responses.
    """

    class Meta:
        model = Account
        fields = ("username", "title", "first_name", "last_name", "email")


class GroupSerializer(serializers.ModelSerializer):
    """Serializer for Django Group objects.

    Serializes Django authentication group data for API responses.
    """

    class Meta:
        model = Group
        fields = ("name",)


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role objects.

    Serializes all role fields for API responses.
    """

    class Meta:
        model = Role
        exclude = []


class ResearchGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API viewset for ResearchGroup objects.

    Provides list and detail views for research groups through the REST API.
    Supports standard REST operations: GET (list and detail).

    Attributes:
        queryset (QuerySet):
            All ResearchGroup objects.
        serializer_class (class):
            ResearchGroupSerializer for object serialization.
    """

    queryset = ResearchGroup.objects.all()
    serializer_class = ResearchGroupSerializer


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API viewset for Account objects.

    Provides list and detail views for user accounts through the REST API.
    Supports standard REST operations: GET (list and detail).

    Attributes:
        queryset (QuerySet):
            All Account objects.
        serializer_class (class):
            AccountSerializer for object serialization.
    """

    queryset = Account.objects.all()
    serializer_class = AccountSerializer


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API viewset for Django Group objects.

    Provides list and detail views for authentication groups through the REST API.
    Supports standard REST operations: GET (list and detail).

    Attributes:
        queryset (QuerySet):
            All Group objects.
        serializer_class (class):
            GroupSerializer for object serialization.
    """

    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API viewset for Role objects.

    Provides list and detail views for user roles through the REST API.
    Supports standard REST operations: GET (list and detail).

    Attributes:
        queryset (QuerySet):
            All Role objects.
        serializer_class (class):
            RoleSerializer for object serialization.
    """

    queryset = Role.objects.all()
    serializer_class = RoleSerializer


router = [
    (r"accounts", AccountViewSet),
    (r"groups", GroupViewSet),
    (r"roles", RoleViewSet),
    (r"researchgroups", ResearchGroupViewSet),
]
