"""
CareerAI Development Settings
=============================
Settings for local development environment.
"""
from dotenv import load_dotenv
load_dotenv()
from .base import *  # noqa


# =============================================================================
# DEBUG MODE
# =============================================================================
DEBUG = True

# =============================================================================
# ALLOWED HOSTS
# =============================================================================
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# =============================================================================
# DATABASE (Use SQLite for quick local dev, or PostgreSQL)
# =============================================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# =============================================================================
# CACHE (Local memory cache for development)
# =============================================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# =============================================================================
# EMAIL (Console backend for development)
# =============================================================================
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# =============================================================================
# CORS (Allow all origins in development)
# =============================================================================
CORS_ALLOW_ALL_ORIGINS = True

# =============================================================================
# STATIC FILES
# =============================================================================
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# =============================================================================
# DEBUG TOOLBAR (Optional)
# =============================================================================
try:
    import debug_toolbar  # noqa

    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

# =============================================================================
# LOGGING (More verbose in development)
# =============================================================================
LOGGING["handlers"]["console"]["level"] = "DEBUG"
LOGGING["loggers"]["apps"]["level"] = "DEBUG"

# =============================================================================
# THROTTLING (Disabled in development)
# =============================================================================
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "anon": "1000/minute",
    "user": "1000/minute",
    "login": "100/minute",
}

# =============================================================================
# FEATURE FLAGS
# =============================================================================
ENABLE_EMAIL_VERIFICATION = False
ENABLE_2FA = False

# =============================================================================
# DISABLE SECURITY SETTINGS FOR DEVELOPMENT
# =============================================================================
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

