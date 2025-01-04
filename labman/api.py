# -*- coding: utf-8 -*-
"""
Read any individual app .api modules

Created on Sun Jun 25 14:43:10 2023

@author: phygbu
"""
__all__ = ["urlpatterns"]
# Python imports
from pathlib import Path

# Django imports
from django.urls import include, path

# external imports
from rest_framework import routers

# app imports
from .settings.production import PROJECT_ROOT

urlpatterns = []

main_router = routers.DefaultRouter()

# Add urls path for all the apps
for f in (Path(PROJECT_ROOT) / "apps").iterdir():
    if not f.is_dir() or f.name.startswith(".") or not (f / "models.py").exists():  # Not a django app
        continue
    if (f / "api.py").exists():
        app_module = __import__(f.name, globals(), locals(), ["api"])
        api = getattr(app_module, "api", None)
        if hasattr(api, "router"):
            for pth, viewset in api.router:
                main_router.register(pth, viewset)
urlpatterns.append(path("", include(main_router.urls)))
