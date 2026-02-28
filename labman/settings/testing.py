# -*- coding: utf-8 -*-
"""Django settings for running the test suite.

This module provides Django settings optimised for running tests with pytest-django.
It uses PostgreSQL (required for django.contrib.postgres features), disables external
authentication backends that require network infrastructure, and configures a minimal
set of logging handlers to avoid file I/O during tests.
"""
# Python imports
import os
import sys
from pathlib import Path

# ##### PATH CONFIGURATION ################################

DJANGO_ROOT_PATH = Path(__file__).parent.parent
DJANGO_ROOT = str(DJANGO_ROOT_PATH)

PROJECT_ROOT_PATH = DJANGO_ROOT_PATH.parent
PROJECT_ROOT = str(PROJECT_ROOT_PATH)

SITE_NAME = DJANGO_ROOT_PATH.name

STATIC_ROOT = str(PROJECT_ROOT_PATH / "run" / "static")
MEDIA_ROOT = str(PROJECT_ROOT_PATH / "run" / "media")

STATICFILES_DIRS = [str(PROJECT_ROOT_PATH / "static")]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

PROJECT_TEMPLATES = [str(PROJECT_ROOT_PATH / "templates")]

sys.path.append(str((DJANGO_ROOT_PATH).absolute()))
sys.path.append(str((PROJECT_ROOT_PATH / "apps").absolute()))

# ##### APPLICATION CONFIGURATION #########################

APPS = {
    f.name: f
    for f in (PROJECT_ROOT_PATH / "apps").iterdir()
    if f.is_dir() and not f.name.startswith(".") and (f / "models.py").exists()
}

CUSTOM_APPS = list(APPS.keys())

DEFAULT_APPS = [
    "django_bootstrap5",
    "django.contrib.postgres",
    "labman_suit.SuitConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.flatpages",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dal",
    "dal_select2",
    "photologue",
    "sortedm2m",
    "constance",
    "django_extensions",
    "django_htmx",
    "mptt",
    "rest_framework",
    "import_export",
    "sitetree",
    "tinymce",
    "easy_pdf",
    "django_simple_file_handler",
] + CUSTOM_APPS

INSTALLED_APPS = DEFAULT_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": PROJECT_TEMPLATES,
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "constance.context_processors.config",
                "django.template.context_processors.request",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
            "builtins": [
                "django.templatetags.static",
                "mathfilters.templatetags.mathfilters",
                "labman_utils.templatetags.labman_tags",
            ],
        },
    }
]

USE_I18N = True

# ##### SECURITY CONFIGURATION ############################

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "test-only-insecure-secret-key-do-not-use-in-production")

ADMINS = []
MANAGERS = ADMINS

# ##### DJANGO RUNNING CONFIGURATION ######################

WSGI_APPLICATION = f"{SITE_NAME}.wsgi.application"
ROOT_URLCONF = f"{SITE_NAME}.urls"
SITE_ID = 1
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

ALLOWED_HOSTS = ["*"]

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 7 * 24 * 3600

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

DEBUG = True

LANGUAGE_CODE = "en"
TIME_ZONE = "Europe/London"
USE_TZ = True

# ##### DATABASE CONFIGURATION ############################

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "labman_test"),
        "USER": os.environ.get("POSTGRES_USER", "labman"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "labman"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "TEST": {
            "NAME": os.environ.get("POSTGRES_TEST_DB", "labman_test"),
        },
    }
}

# ##### AUTHENTICATION CONFIGURATION ######################

AUTH_USER_MODEL = "accounts.Account"

LOGIN_URL = "core_login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "core_login"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# ##### LOGGING CONFIGURATION #############################
# Minimal logging for tests to avoid file I/O

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

# ##### CONSTANCE SETTINGS ################################

CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"
CONSTANCE_CONFIG = {"TEST": (42, "Test Field")}

# ##### REST FRAMEWORK SETTINGS ###########################

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"]
}

# ##### SITETREE SETTINGS #################################

SITETREE_ITEMS_FIELD_ROOT_ID = -1
SITETREE_CLS = "labman_utils.tree.CustomSiteTree"
SITETREE_MODEL_TREE = "labman_utils.GroupedTree"
SITETREE_MODEL_TREE_ITEM = "labman_utils.GroupedTreeItem"

# ##### TINYMCE SETTINGS ##################################

TINYMCE_DEFAULT_CONFIG = {
    "height": "480px",
    "width": "800px",
}

# Import Application-specific Settings
for app in CUSTOM_APPS:
    try:
        app_module = __import__(app, globals(), locals(), ["settings"])
        app_settings = getattr(app_module, "settings", None)
        for setting in dir(app_settings):
            if setting == setting.upper():
                set_val = getattr(app_settings, setting)
                if isinstance(set_val, dict):
                    locals()[setting].update(set_val)
                elif isinstance(set_val, (list, tuple)):
                    locals()[setting] = locals()[setting] + set_val
                else:
                    locals()[setting] = set_val
    except ImportError:
        pass
