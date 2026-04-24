"""
CareerAI Production Settings
============================
Production-grade settings with security hardening.
"""
from dotenv import load_dotenv
load_dotenv()

from decouple import config

from .base import *  # noqa

# =============================================================================
# DEBUG MODE (MUST BE FALSE IN PRODUCTION)
# =============================================================================
DEBUG = False

# =============================================================================
# SECURITY SETTINGS
# =============================================================================
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# =============================================================================
# DATABASE CONNECTION POOLING
# =============================================================================
DATABASES["default"]["CONN_MAX_AGE"] = 600
# Ensure OPTIONS exists before setting connect_timeout
if "OPTIONS" not in DATABASES["default"]:
    DATABASES["default"]["OPTIONS"] = {}
DATABASES["default"]["OPTIONS"]["connect_timeout"] = 10

# =============================================================================
# CACHE SETTINGS (Production - Using in-memory with optional Redis override)
# =============================================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "careerAI-prod-cache",
    }
}

# =============================================================================
# SENTRY ERROR MONITORING (Optional)
# =============================================================================
SENTRY_DSN = config("SENTRY_DSN", default="")

if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                DjangoIntegration(),
            ],
            environment=config("SENTRY_ENVIRONMENT", default="production"),
            traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0.2, cast=float),
            send_default_pii=False,
            attach_stacktrace=True,
            request_bodies="medium",
            max_breadcrumbs=50,
        )
    except ImportError:
        pass  # Sentry not installed, continue without error monitoring

# =============================================================================
# LOGGING (JSON format for production)
# =============================================================================
if "json" not in LOGGING.get("formatters", {}):
    LOGGING.setdefault("formatters", {})["json"] = {
        "format": '{{"level":"{levelname}","time":"{asctime}","logger":"{name}","message":"{message}"}}',
        "style": "{",
    }

LOGGING["handlers"]["console"]["formatter"] = "json"
if "file" in LOGGING.get("handlers", {}):
    LOGGING["handlers"]["file"]["formatter"] = "json"

# =============================================================================
# STATIC FILES (WhiteNoise)
# =============================================================================
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# =============================================================================
# ADMINS (for error emails)
# =============================================================================
ADMINS = [
    ("CareerPilot Admin", config("ADMIN_EMAIL", default="admin@careerpilot.com")),
]

# =============================================================================
# FEATURE FLAGS (Production)
# =============================================================================
ENABLE_EMAIL_VERIFICATION = True
ENABLE_2FA = config("ENABLE_2FA", default=False, cast=bool)
