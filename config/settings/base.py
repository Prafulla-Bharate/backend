"""
CareerAI Base Settings
======================
Common settings shared across all environments.
This file contains production-ready defaults.
"""
from dotenv import load_dotenv
load_dotenv()
import os
from datetime import timedelta
from pathlib import Path

from decouple import config, Csv


# =============================================================================
# PATHS
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = BASE_DIR / "apps"

# =============================================================================
# CORE SETTINGS
# =============================================================================
DEBUG = config("DEBUG", default=False, cast=bool)
SECRET_KEY = config("SECRET_KEY", default="change-me-in-production")
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# APPLICATIONS

# =============================================================================
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "storages",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.profile",
    "apps.career",
    "apps.learning",
    "apps.jobs",
    "apps.interview",
    "apps.analytics",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.RequestLoggingMiddleware",
    "apps.core.middleware.RateLimitMiddleware",
    "apps.core.middleware.AuditLogMiddleware",
]

# =============================================================================
# TEMPLATES
# =============================================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# =============================================================================
# DATABASE
# =============================================================================
# Support both DATABASE_URL (Docker) and individual variables
import dj_database_url

DATABASE_URL = config("DATABASE_URL", default="")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=60)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="careerAI"),
            "USER": config("DB_USER", default="postgres"),
            "PASSWORD": config("DB_PASSWORD", default="postgres"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
            "CONN_MAX_AGE": 60,
            "OPTIONS": {
                "connect_timeout": 10,
            },
        }
    }

# =============================================================================
# CACHE (In-Memory - Django Default)
# =============================================================================
# Using Django's simple in-memory caching for development
# For production, configure with Memcached or Redis as needed
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "careerAI-cache",
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
        }
    }
}


# =============================================================================
# AUTHENTICATION
# =============================================================================
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "apps.users.validators.PasswordComplexityValidator",
    },
]

# Password Hasher - PBKDF2 with 150k iterations
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# =============================================================================
# DJANGO REST FRAMEWORK
# =============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "apps.core.renderers.CareerAIJSONRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.CursorPaginationWithCount",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "50/minute",
        "user": "100/minute",
        "login": "5/minute",
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "NON_FIELD_ERRORS_KEY": "non_field_errors",
}

# =============================================================================
# JWT CONFIGURATION
# =============================================================================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=15, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=30, cast=int)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": config("JWT_ALGORITHM", default="HS256"),
    "SIGNING_KEY": config("JWT_SECRET_KEY", default=SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "TOKEN_OBTAIN_SERIALIZER": "apps.users.serializers.CareerAITokenObtainPairSerializer",
}

# =============================================================================
# CORS CONFIGURATION
# =============================================================================
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-request-id",
]

# =============================================================================
# CSRF CONFIGURATION
# =============================================================================
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:3000,http://localhost:8080,http://127.0.0.1:8080",
    cast=Csv(),
)

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = []  # No custom static assets directory
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =============================================================================
# FILE UPLOAD SETTINGS
# =============================================================================
MAX_UPLOAD_SIZE = config("MAX_UPLOAD_SIZE_MB", default=50, cast=int) * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE

# =============================================================================
# AWS S3 STORAGE (Optional)
# =============================================================================
USE_S3 = config("USE_S3", default=False, cast=bool)

if USE_S3:
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="us-east-1")
    AWS_S3_CUSTOM_DOMAIN = config("AWS_S3_CUSTOM_DOMAIN", default="")
    AWS_DEFAULT_ACL = "private"
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    AWS_QUERYSTRING_AUTH = True
    AWS_S3_FILE_OVERWRITE = False
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="smtp.sendgrid.net")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@careerpilot.com")

# =============================================================================
# LOGGING
# =============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# =============================================================================
# API DOCUMENTATION (drf-spectacular)
# =============================================================================
SPECTACULAR_SETTINGS = {
    "TITLE": "CareerPilot API",
    "DESCRIPTION": "Production-ready AI Career Platform Backend API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/",
    "SECURITY": [{"Bearer": []}],
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
    },
    "TAGS": [
        {"name": "auth", "description": "Authentication endpoints"},
        {"name": "profile", "description": "User profile management"},
        {"name": "career", "description": "Career prediction and trends"},
        {"name": "learning", "description": "Learning paths and progress"},
        {"name": "jobs", "description": "Job listings and applications"},
        {"name": "interview", "description": "Interview practice sessions"},
        {"name": "analytics", "description": "User analytics and metrics"},
    ],
}

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================
# Feature Flags
ENABLE_EMAIL_VERIFICATION = config("ENABLE_EMAIL_VERIFICATION", default=True, cast=bool)
ENABLE_2FA = config("ENABLE_2FA", default=False, cast=bool)

# URLs
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")
BACKEND_URL = config("BACKEND_URL", default="http://localhost:8000")

# =============================================================================
# EXTERNAL API KEYS
# =============================================================================
# Google Gemini AI
GEMINI_API_KEY = config("GEMINI_API_KEY", default="")

# JSearch (Jobs API via RapidAPI)
# Support both keys to keep backward compatibility with existing env files.
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY") or os.getenv("RAPIDAPI_KEY", "")
JSEARCH_API_URL = os.getenv("JSEARCH_API_URL", "https://jsearch.p.rapidapi.com")
JSEARCH_TIMEOUT_SECONDS = float(os.getenv("JSEARCH_TIMEOUT_SECONDS", "7"))
JSEARCH_CACHE_TTL_SECONDS = int(os.getenv("JSEARCH_CACHE_TTL_SECONDS", "300"))

# YouTube Data API
YOUTUBE_API_KEY = config("YOUTUBE_API_KEY", default="")

# =============================================================================
# RATE LIMITING
# =============================================================================
RATE_LIMIT_REQUESTS_PER_MINUTE = config("RATE_LIMIT_REQUESTS_PER_MINUTE", default=100, cast=int)
RATE_LIMIT_BURST = config("RATE_LIMIT_BURST", default=150, cast=int)

# Account Security
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15
PASSWORD_RESET_TOKEN_EXPIRY_HOURS = 2
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = 24

# Streak Settings
STREAK_TIMEZONE_AWARE = True

# XP & Gamification
XP_RESOURCE_COMPLETE = 10
XP_CHECKPOINT_PASS = 50
XP_COURSE_COMPLETE = 100
XP_PROJECT_COMPLETE = 150
XP_INTERVIEW_COMPLETE = 75
XP_DAILY_LOGIN = 5
