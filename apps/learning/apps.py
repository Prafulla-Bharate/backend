"""
Learning App Configuration
==========================
"""

from django.apps import AppConfig


class LearningConfig(AppConfig):
    """Configuration for the Learning app."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.learning"
    verbose_name = "Learning"
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.learning.signals  # noqa: F401
        except ImportError:
            pass
