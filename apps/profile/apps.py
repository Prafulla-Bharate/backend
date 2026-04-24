"""
Profile Application Configuration
=================================
"""

from django.apps import AppConfig


class ProfileConfig(AppConfig):
    """Configuration for the Profile application."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.profile"
    verbose_name = "User Profile"

    def ready(self):
        """Import signal handlers when app is ready."""
        import apps.profile.signals  # noqa: F401
