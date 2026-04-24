"""
CareerAI Testing Settings
=========================
Optimized settings for running tests.
"""

from .base import *  # noqa

# =============================================================================
# DEBUG MODE
# =============================================================================
DEBUG = False

# =============================================================================
# SECRET KEY (Fixed for testing)
# =============================================================================
SECRET_KEY = "test-secret-key-not-for-production"

# =============================================================================
# DATABASE (In-memory SQLite for speed)
# =============================================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# =============================================================================
# CACHE (Local memory for testing)
# =============================================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# =============================================================================
# PASSWORD HASHER (Faster for testing)
# =============================================================================
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# =============================================================================
# EMAIL (In-memory backend for testing)
# =============================================================================
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# =============================================================================
# FILE STORAGE (Local for testing)
# =============================================================================
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
MEDIA_ROOT = BASE_DIR / "test_media"

# =============================================================================
# THROTTLING (Disabled for testing)
# =============================================================================
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []

# =============================================================================
# MIDDLEWARE (Remove rate limiting for tests)
# =============================================================================
MIDDLEWARE = [m for m in MIDDLEWARE if "RateLimit" not in m]

# =============================================================================
# LOGGING (Minimal for testing)
# =============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
}

# =============================================================================
# FEATURE FLAGS
# =============================================================================
ENABLE_EMAIL_VERIFICATION = False
ENABLE_2FA = False
