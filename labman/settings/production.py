# Production settings
# app imports
from .common import *

try:
    from .secrets import DATABASES
except ImportError:
    # Provide default DATABASES configuration if secrets.py is not available
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': str(PROJECT_ROOT_PATH / 'run' / 'db.sqlite3'),
        }
    }

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://cdn.jsdelivr.net",
    "https://unpkg.com/",
    "https://code.jquery.com/",
    "https://login.microsoftonline.com",
    "https://graph.microsoft.com",
] + CSRF_TRUSTED_ORIGINS
CORS_ALLOW_METHODS = [
    "GET",
    "PATCH",
    "POST",
    "PUT",
    "DELETE",
]
CORS_ALLOW_HEADERS = [
    "Authorization",
    "Content-Type",
    "Content-Disposition",
    "HX-Boosted",
    "HX-Current-URL",
    "HX-History-Restore-Request",
    "HX-Prompt",
    "HX-Request",
    "HX-Target",
    "HX-Trigger-Name",
    "HX-Trigger",
    "Accept",
    "Range",
    "Location",
]
CORS_EXPOSE_HEADERS = [
    "Accept-Ranges",
    "Content-Encoding",
    "Content-Length",
    "Content-Range",
    "Location",
    "HX-Location",
    "HX-Push-Url",
    "HX-Redirect",
    "HX-Refresh",
    "HX-Replace-Url",
    "HX-Reswap",
    "HX-Retarget",
    "HX-Reselect",
    "HX-Trigger",
    "HX-Trigger-After-Settle",
    "HX-Trigger-After-Swap",
]

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 3600
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Strict"

X_FRAME_OPTIONS = "DENY"

DEBUG = False
