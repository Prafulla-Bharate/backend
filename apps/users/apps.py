"""
Users Application Configuration
===============================
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Configuration for the Users application."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    verbose_name = "Users"

    def ready(self):
        """Import signal handlers when app is ready."""
        try:
            import apps.users.signals  # noqa: F401
        except ImportError:
            pass
