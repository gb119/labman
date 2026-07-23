"""Configure the autocomplete application and discover registered implementations."""

# Python imports
from importlib import import_module

# Django imports
from django.apps import AppConfig, apps

# app imports
from . import Autocomplete, ModelAutocomplete, register


class AutocompleteConfig(AppConfig):
    """.
            Django app config


    Examples:
        Inspect the public interface in an interactive session::

            >>> AutocompleteConfig.__name__
            'AutocompleteConfig'
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "autocomplete"

    def ready(self):
        """Go looking for autocomplete classes to register.

        Examples:
            Inspect the public interface in an interactive session::

                >>> callable(AutocompleteConfig.ready)
                True
        """
        for appname in apps.app_configs:
            if appname == "autocomplete":  # Don't try to import ourself!
                continue
            try:
                mod = import_module(f"{appname}.autocomplete")
            except ImportError:
                continue
            for name in dir(mod):
                obj = getattr(mod, name)
                if isinstance(obj, type) and issubclass(obj, Autocomplete):
                    try:
                        if obj in [Autocomplete, ModelAutocomplete]:
                            continue
                        register(obj)
                    except ValueError:
                        continue
                    print(f"Registered Autocomplete {appname}:{name}")
