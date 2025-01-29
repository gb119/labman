# -*- coding: utf-8 -*-
"""Models and code for handling a custom menu."""

# external imports
from sitetree.sitetreeapp import SiteTree


class CustomSiteTree(SiteTree):
    """Custom tree handler to test deep customization abilities."""

    def check_access_dyn(self, item, context):
        """Perform dynamic item access check.

        Args:
            item (Node):
                The item is expected to have `access_check` callable attribute implementing the check.
            context:

        """
        access_check_func = getattr(item, "access_check", None)

        self.context = context

        if access_check_func:
            return access_check_func(tree=self)

        return None
