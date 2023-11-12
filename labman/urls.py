"""labman URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
"""
from pathlib import Path
# Django imports
from django.conf.urls import include
from django.urls import path, re_path
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.static import serve
from django.views.generic import TemplateView

# ... the rest of your URLconf goes here ...

from .settings.production import PROJECT_ROOT, DEBUG, MEDIA_ROOT

# Django REST Framework launcher import
from . import api

urlpatterns = [
    # Examples:
    # url(r'^$', 'labman.views.home', name='home'),
    path('', TemplateView.as_view(template_name="home.html")),
    path(r"login/", auth_views.LoginView.as_view(), name="core_login"),
    path(r"logout", auth_views.LogoutView.as_view(next_page="/"), name="core_logout"),
    path('tinymce/', include('tinymce.urls')),
    path('photologue/', include('photologue.urls', namespace="photologue")),
    path('private-file-pseudo-directory-path/', include('django_simple_file_handler.urls')),
    path('api/', include(api)), # main api module exports a urlpatterns
    path('api-auth/', include('rest_framework.urls')), # Needed by REST framework for user authentication
    path('admin/', admin.site.urls),
]

# Add urls path for all the apps
for f in (Path(PROJECT_ROOT)/"apps").iterdir():
    if not f.is_dir() or f.name.startswith("."):
        continue
    if (f/"urls.py").exists():
        urlpatterns.append(path(f"{f.name}/", include(f"{f.name}.urls")))

if DEBUG:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {
                "document_root": MEDIA_ROOT,
            },
        ),
    ]
