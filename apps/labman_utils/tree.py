# -*- coding: utf-8 -*-
"""Custom site tree implementation for dynamic menu access control.

This module provides a custom SiteTree handler that extends the base sitetree functionality
to support dynamic access checks for menu items based on custom callable attributes.
"""

# external imports
from sitetree.sitetreeapp import SiteTree


class CustomSiteTree(SiteTree):
    """Custom tree handler that provides dynamic access control for menu items.

    This class extends the SiteTree base class to support custom access checks on menu items.
    It allows items to have dynamic access control through callable attributes that can perform
    runtime checks based on the current context.

    Attributes:
        context (dict):
            The current request context used for access checks.
    """

    def check_access_dyn(self, item, context):
        """Perform dynamic item access check based on the item's access_check callable.

        Args:
            item (object):
                The menu item to check. Expected to have an optional `access_check` callable
                attribute that implements the access control logic.
            context (dict):
                The request context containing information needed for the access check.

        Returns:
            (bool or None):
                The result of the access check if an access_check callable is present,
                None otherwise.

        Notes:
            The access_check callable, if present, receives the tree instance as a keyword
            argument and should return a boolean indicating whether access is granted.
        """
        access_check_func = getattr(item, "access_check", None)

        self.context = context

        if access_check_func:
            return access_check_func(tree=self)

        return None
