"""
WSGI config for labman project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

# Python imports
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "labman.settings.production")

# Django imports
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
