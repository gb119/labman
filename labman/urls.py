"""labman URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
"""

# Python imports
from pathlib import Path

# Django imports
from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, re_path
from django.views.generic import TemplateView
from django.views.static import serve

# app imports
# Django REST Framework launcher import
from . import api
from .settings.production import DEBUG, MEDIA_ROOT, PROJECT_ROOT
from .views import E403View, E404View, E500View, FileServeView

# Set Error handlers
handler404 = E404View.as_view()
handler403 = E403View.as_view()
handler500 = E500View.as_view()
# ... the rest of your URLconf goes here ...


urlpatterns = [
    # Examples:
    # url(r'^$', 'labman.views.home', name='home'),
    path("", TemplateView.as_view(template_name="home.html")),
    path(r"isteach/", auth_views.LoginView.as_view(), name="core_login"),
    path(r"scoir/", auth_views.LogoutView.as_view(next_page="/"), name="core_logout"),
    path("tinymce/", include("tinymce.urls")),
    path("photologue/", include("photologue.urls", namespace="photologue")),
    path("private-file-pseudo-directory-path/", include("django_simple_file_handler.urls")),
    path("api/", include(api)),  # main api module exports a urlpatterns
    path("api-auth/", include("rest_framework.urls")),  # Needed by REST framework for user authentication
    path("oauth2/", include("django_auth_adfs.urls")),  # Autrhentication via Duo
    path("riaradh/", admin.site.urls),
]

# Add urls path for all the apps
for f in (Path(PROJECT_ROOT) / "apps").iterdir():
    if not f.is_dir() or f.name.startswith("."):
        continue
    if (f / "urls.py").exists():
        urlpatterns.append(path(f"{f.name}/", include(f"{f.name}.urls")))

urlpatterns += [
    re_path(
        r"^media/(?P<path>.*)$",
        FileServeView.as_view(),
        {
            "document_root": MEDIA_ROOT,
        },
        name="media_files",
    ),
]
