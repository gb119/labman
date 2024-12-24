#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REST Framework endpiints for the accounts objects.
"""

# Django imports
from django.contrib.auth.models import Group

# external imports
from rest_framework import serializers, viewsets

# app imports
from .models import Account, ResearchGroup, Role


# Serializers define the API representation.
class ResearchGroupSerializer(serializers.ModelSerializer):
    """Serialise the  Research Group objects."""

    class Meta:
        model = ResearchGroup
        fields = ("name", "code")


# Serializers define the API representation.
class AccountSerializer(serializers.ModelSerializer):
    """Serialise the Account objects."""

    class Meta:
        model = Account
        fields = ("username", "title", "first_name", "last_name", "email")


class GroupSerializer(serializers.ModelSerializer):
    """Serialise the Group objects."""

    class Meta:
        model = Group
        fields = ("name",)


class RoleSerializer(serializers.ModelSerializer):
    """Serialise the Role objects."""

    class Meta:
        model = Role
        exclude = []


# ViewSets define the view behavior.
class ResearchGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """API views for Research Groups."""

    queryset = ResearchGroup.objects.all()
    serializer_class = ResearchGroupSerializer


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    """API views for Accounts."""

    queryset = Account.objects.all()
    serializer_class = AccountSerializer


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """API views for Groups."""

    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """API views for Roles."""

    queryset = Role.objects.all()
    serializer_class = RoleSerializer


router = [
    (r"accounts", AccountViewSet),
    (r"groups", GroupViewSet),
    (r"roles", RoleViewSet),
    (r"researchgroups", ResearchGroupViewSet),
]
