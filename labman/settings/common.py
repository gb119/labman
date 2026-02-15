# Python imports
import socket
import sys
from pathlib import Path

# Import some utility functions

# #########################################################

# ##### Setup system path to include usr/local packages
# Import some utility functions

major, minor = sys.version_info[0:2]
sys.path.append(f"/usr/local/lib/python{major}.{minor}/site-packages")

# ##### PATH CONFIGURATION ################################

# fetch Django's project directory
DJANGO_ROOT_PATH = Path(__file__).parent.parent
DJANGO_ROOT = str(DJANGO_ROOT_PATH)

# fetch the project_root
PROJECT_ROOT_PATH = DJANGO_ROOT_PATH.parent
PROJECT_ROOT = str(PROJECT_ROOT_PATH)

# the name of the whole site
SITE_NAME = DJANGO_ROOT_PATH.name

# collect static files here
STATIC_ROOT = str(PROJECT_ROOT_PATH / "run" / "static")

# collect media files here
MEDIA_ROOT = str(PROJECT_ROOT_PATH / "run" / "media")

# look for static assets here
STATICFILES_DIRS = [
    str(PROJECT_ROOT_PATH / "static"),
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# look for templates here
# This is an internal setting, used in the TEMPLATES directive
PROJECT_TEMPLATES = [
    str(PROJECT_ROOT_PATH / "templates"),
]

# add apps/ to the Python path
sys.path.append(str((DJANGO_ROOT_PATH).absolute()))
sys.path.append(str((PROJECT_ROOT_PATH / "apps").absolute()))

# ##### APPLICATION CONFIGURATION #########################

APPS = {
    f.name: f
    for f in (PROJECT_ROOT_PATH / "apps").iterdir()
    if f.is_dir() and not f.name.startswith(".") and (f / "models.py").exists()
}


# This are the apps
CUSTOM_APPS = list(APPS.keys())
# Autobuild all
appdirs = list(APPS.items())
print("#" * 80)
for app in APPS:
    print(f"Adding {app=}")
print("#" * 80)


# these are the apps
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
    #    "corsheaders",
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

# Middlewares
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    #   "corsheaders.middleware.CorsMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

# Template stuff
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


# Internationalization
USE_I18N = False


# ##### SECURITY CONFIGURATION ############################

# We store the secret key here
# The required SECRET_KEY is fetched at the end of this file
SECRET_FILE = (PROJECT_ROOT_PATH / "run" / "SECRET.key").absolute()

# these persons receive error notification
ADMINS = (("[[ your name ]]", "[[ your_name@example.com ]]"),)
MANAGERS = ADMINS


# ##### DJANGO RUNNING CONFIGURATION ######################

# the default WSGI application
WSGI_APPLICATION = f"{SITE_NAME}.wsgi.application"

# the root URL configuration
ROOT_URLCONF = f"{SITE_NAME}.urls"

# This site's ID
SITE_ID = 1

# The URL for static files
STATIC_URL = "/static/"

# the URL for media files
MEDIA_URL = "/media/"

# ##### Settings for CSRF protection
try:
    DNS_NAME = f"{SITE_NAME}.leeds.ac.uk"
    IP_ADDR = socket.gethostbyname(DNS_NAME)
except socket.gaierror:
    DNS_NAME = "loxcalhost"
    IP_ADDR = "127.0.0.1"

ALLOWED_HOSTS = [
    DNS_NAME,
    IP_ADDR,
    "localhost",
    "127.0.0.1",
    "127.0.0.1:8443",
    "localhost:8443",
    "stoner-intranet-dev.leeds.ac.uk",
    "stoner-intranet.leeds.ac.uk",
]
CSRF_TRUSTED_ORIGINS = [f"https://{x}" for x in ALLOWED_HOSTS]

# #### Session Settings

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 7 * 24 * 360  # keep sessions open all week

# ##### Login settings

HTTPS_SUPPORT = True
SECURE_REQUIRED_PATHS = ("/oauth2/login",)

# ##### Default autofield type

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# ##### DEBUG CONFIGURATION ###############################
DEBUG = False


# ##### INTERNATIONALIZATION ##############################

LANGUAGE_CODE = "en"
TIME_ZONE = "Europe/London"

# Internationalization
USE_I18N = True

# Localisation

# enable timezone awareness by default
USE_TZ = True


# Finally grab the SECRET KEY
try:
    SECRET_KEY = SECRET_FILE.read_text().strip()
except IOError:
    try:
        # Django imports
        from django.utils.crypto import get_random_string

        chars = "abcdefghijklmnopqrstuvwxyz0123456789!$%&()=+-_"
        SECRET_KEY = get_random_string(50, chars)
        SECRET_FILE.write_text(SECRET_KEY)
    except IOError:
        raise Exception("Could not open %s for writing!" % SECRET_FILE)

# LOGGING config

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": str(PROJECT_ROOT_PATH / "logs" / "django.log"),
        },
        "debugging": {
            "level": "ERROR",  # reset to DEBUG to get full debugging
            "class": "logging.FileHandler",
            "filename": str(PROJECT_ROOT_PATH / "logs" / "debugging.log"),
        },
        "file_info": {
            "class": "logging.FileHandler",
            "filename": str(PROJECT_ROOT_PATH / "logs" / "form_data.log"),
        },
        "mail_admins": {"level": "ERROR", "class": "django.utils.log.AdminEmailHandler"},
    },
    "formatters": {"verbose": {"format": "%(asctime)s %(levelname)-8s [%(name)s:%(lineno)s] %(message)s"}},
    "loggers": {
        "": {"handlers": ["file", "debugging"], "level": "DEBUG", "propagate": True},
        "auth": {"handlers": ["file"], "level": "INFO", "propagate": True},
        "django.request": {"handlers": ["mail_admins"], "level": "ERROR", "propagate": True},
        "django.security": {"handlers": ["mail_admins"], "level": "ERROR", "propagate": True},
        "labman_utils.middleware": {
            "handlers": ["file_info"],
            "propagate": False,
        },
    },
}

####### EMAIL SETTINGS ####################################

EMAIL_HOST = ADMINS[0][1]
EMAIL_PORT = 587
EMAIL_SUBJECT_PREFIX = f"{SITE_NAME} :"
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = f"no-reply@{DNS_NAME}"


##########################################################################
AUTH_USER_MODEL = "accounts.Account"

LOGIN_URL = "django_auth_adfs:login"
LOGIN_REDIRECT_URL = "/accounts/me/"

# Only allow manual creation of new users
AUTH_LDAP_CREATE_USER_ON_FLY = False

AUTHENTICATION_BACKENDS = [
    "labman_utils.backend.LeedsAdfsBaseBackend",
    "django_auth_ldap_ad.backend.LDAPBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_LDAP_USE_SASL = False

AUTH_LDAP_BIND_TRANSFORM = "{}@ds.leeds.ac.uk"

AUTH_LDAP_SERVER_URI = ["ldaps://ds.leeds.ac.uk:636", "ldaps://admin.ds.leeds.ac.uk:636"]
AUTH_LDAP_SEARCH_DN = "DC=ds,DC=leeds,DC=ac,DC=uk"
AUTH_LDAP_USER_ATTR_MAP = {"first_name": "givenName", "last_name": "sn", "email": "mail", "number": "employeeID"}

AUTH_LDAP_TRACE_LEVEL = 0
AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    # Groups on left side are memberOf key values. If all the groups are found in single entry, then the flag is set to
    # True. If no entry contains all required groups then the flag is set False.
    "is_superuser": [],
    # Above example will match on entry "CN=WebAdmin,DC=mydomain,OU=People,OU=Users"
    # Above will NOT match "CN=WebAdmin,OU=People,OU=Users" (missing DC=mydomain).
    "is_staff": [
        "CN=PHY_Academic_Staff,OU=Groups,OU=Physics and Astronomy,OU=MAPS,OU=Resources,DC=ds,DC=leeds,DC=ac,DC=uk"
    ],
    # True if one of the conditions is true.
}

# All people that are to be staff are also to belong to this group
AUTH_LDAP_USER_GROUPS_BY_GROUP = {}

AUTH_ADFS = {
    # "RELYING_PARTY_ID": "your-adfs-RPT-name",
    # "CA_BUNDLE": "/path/to/ca-bundle.pem",
    "CLAIM_MAPPING": {"first_name": "given_name", "last_name": "family_name", "email": "email"},
}

###### REST framework settings ###########################

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"]
}


# ### SITETREE Customisation ##############################

SITETREE_ITEMS_FIELD_ROOT_ID = -1

SITETREE_CLS = "labman_utils.tree.CustomSiteTree"
SITETREE_MODEL_TREE = "labman_utils.GroupedTree"
SITETREE_MODEL_TREE_ITEM = "labman_utils.GroupedTreeItem"

###### Constance Settings ################################


CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"

CONSTANCE_CONFIG = {"TEST": (42, "Test Field")}

CONSTANCE_ADDITIONAL_FIELDS = {
    "custdatetime": [
        "django.forms.fields.SplitDateTimeField",
        {
            "widget": "django.forms.widgets.SplitDateTimeWidget",
            "input_date_formats": ["%Y-%m-%d"],
            "input_time_formats": ["%H:%M:%S"],
        },
    ]
}
###### Tinymce Settings ##################################

TINYMCE_DEFAULT_CONFIG = {
    "height": "480px",
    "width": "800px",
    "menubar": "file edit view insert format tools table help",
    "plugins": "advlist autolink lists link image charmap print preview anchor searchreplace visualblocks code "
    "fullscreen insertdatetime media table paste code help wordcount",
    "toolbar": "undo redo | bold italic underline strikethrough | fontselect fontsizeselect formatselect | alignleft "
    "aligncenter alignright alignjustify | outdent indent |  numlist bullist checklist | forecolor "
    "backcolor casechange permanentpen formatpainter removeformat | pagebreak | charmap emoticons | "
    "fullscreen  preview save print | insertfile image media pageembed template link anchor codesample | "
    "a11ycheck ltr rtl | showcomments addcomment code",
    "custom_undo_redo_levels": 10,
    "highlight_on_focus": True,
    "document_base_url": f"https://{DNS_NAME}",
    "relative_urls": True,
    "language": "en_GB",  # To force a specific language instead of the Django current language.
}
# TINYMCE_SPELLCHECKER = True
# TINYMCE_COMPRESSOR = True
###### Django Suit Menu ##################################

# Import Applicaton-specific Settings
for app in CUSTOM_APPS:
    try:
        app_module = __import__(app, globals(), locals(), ["settings"])
        app_settings = getattr(app_module, "settings", None)
        for setting in dir(app_settings):
            if setting == setting.upper():
                set_val = getattr(app_settings, setting)
                if isinstance(set_val, dict):  # Merge app.settings
                    locals()[setting].update(set_val)
                elif isinstance(set_val, (list, tuple)):  # append app.settings
                    locals()[setting] = locals()[setting] + set_val
                else:  # replace with app.settings
                    locals()[setting] = set_val
    except ImportError:
        pass
