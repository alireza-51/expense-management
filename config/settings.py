"""
Django settings for config project.
"""

from pathlib import Path
import os

# -----------------------------
# Utility functions
# -----------------------------
def get_bool_env(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")

def get_list_env(name, default=None, delimiter=","):
    value = os.getenv(name)
    if not value:
        return default or []
    return [item.strip() for item in value.split(delimiter) if item.strip()]

# -----------------------------
# Paths
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------
# Quick-start development settings
# -----------------------------
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-ruk!g%xwp%i5xdu44_3v2^r##i_@8cnabg_#ykdhjrgea#w6i!')
DEBUG = get_bool_env('DJANGO_DEBUG', True)
ALLOWED_HOSTS = get_list_env('DJANGO_ALLOWED_HOSTS', ['localhost', '127.0.0.1'])

# -----------------------------
# Installed apps
# -----------------------------
INSTALLED_APPS = [
    # Third-Party
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "unfold.contrib.constance",
    "jalali_date",
    "rest_framework",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "corsheaders",

    # Django Core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    # Your apps
    "base",
    "categories",
    "expenses",
    "workspaces",
    "users",
]

# -----------------------------
# Middleware (only one list)
# -----------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # MUST be first for CORS to work
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # after SessionMiddleware
    "config.middleware.LanguageMiddleware",      # custom language middleware
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "workspaces.middlewares.WorkspaceMiddleware",  # your custom middleware
]

# -----------------------------
# URLs & Templates
# -----------------------------
ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "workspaces.context_processors.current_workspace",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# -----------------------------
# Database
# -----------------------------
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("DB_NAME", "expense"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# -----------------------------
# Password validation
# -----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------
# Internationalization
# -----------------------------
LANGUAGE_CODE = os.getenv("DJANGO_LANGUAGE_CODE", "en")
USE_I18N = True
USE_L10N = True

LANGUAGES = [
    ("en", "English"),
    ("fa", "فارسی"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# -----------------------------
# Static and media files
# -----------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------
# Calendar configuration
# -----------------------------
USE_JALALI_CALENDAR = get_bool_env("DJANGO_USE_JALALI_CALENDAR", True)
CALENDAR_TYPE = os.getenv("DJANGO_CALENDAR_TYPE", "jalali")
DEFAULT_DASHBOARD_MONTH = os.getenv("DJANGO_DEFAULT_DASHBOARD_MONTH", "current")

# -----------------------------
# Django Unfold settings
# -----------------------------
UNFOLD = {
    "SITE_TITLE": "Expense Management",
    "SITE_HEADER": "Expense Management System",
    "SITE_SYMBOL": "💰",
    "THEME": "light",
    "COLORS": {
        "primary": {
            "50": "250 245 255",
            "100": "243 232 255",
            "200": "233 213 255",
            "300": "216 180 254",
            "400": "196 181 253",
            "500": "168 85 247",
            "600": "147 51 234",
            "700": "126 34 206",
            "800": "107 33 168",
            "900": "88 28 135",
            "950": "59 7 100",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
    },
}

# -----------------------------
# Django REST Framework
# -----------------------------
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASS": "rest_framework.permissions.IsAuthenticated",
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # 'rest_framework.authentication.SessionAuthentication',  # for web / frontend (CSRF protected)
        # 'rest_framework.authentication.BasicAuthentication',    # optional, for testing or admin
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # for API / mobile clients
    ),
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ]
}

SPECTACULAR_SETTINGS = {
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "TITLE": "Expense Management System",
    "DESCRIPTION": "We help you to manage your finances",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# -----------------------------
# CORS headers (fixed)
# -----------------------------
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = ["http://localhost:8080"]
CORS_ALLOW_HEADERS = ["content-type", "authorization"]
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8080",
    "http://localhost:8000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8000",
]
