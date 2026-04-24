"""
Analytics App Configuration
============================
"""

from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    """Configuration for Analytics app."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics"
    verbose_name = "Analytics"
    
    def ready(self):
        """Initialize app."""
        try:
            import apps.analytics.signals  # noqa: F401
        except ImportError:
            pass
