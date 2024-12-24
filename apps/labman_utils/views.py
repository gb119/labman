# -*- coding: utf-8 -*-
"""
Created on Tue Jul 18 14:56:26 2023

@author: phygbu
"""
# Django imports
from django.contrib.auth.mixins import UserPassesTestMixin


class IsAuthenticaedViewMixin(UserPassesTestMixin):
    login_url = "/login"

    def test_func(self):
        return hasattr(self, "request") and not self.request.user.is_anonymous


class IsSuperuserViewMixin(IsAuthenticaedViewMixin):
    def test_func(self):
        return super().test_finc() and self.request.user.is_superuser


class IsStaffViewMixin(IsSuperuserViewMixin):
    def test_func(self):
        return IsAuthenticaedViewMixin.test_func(self) and (self.request.user.is_staff or super().test_finc())
