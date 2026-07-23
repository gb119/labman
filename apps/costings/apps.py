"""Provide apps functionality for the apps.costings package."""

# Django imports
from django.apps import AppConfig


class CostingsConfig(AppConfig):
    """Provide the CostingsConfig implementation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> CostingsConfig.__name__
            'CostingsConfig'
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "costings"
