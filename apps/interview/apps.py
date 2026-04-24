"""
Interview App Configuration
============================
"""

from django.apps import AppConfig


class InterviewConfig(AppConfig):
    """Configuration for the Interview app."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.interview"
    verbose_name = "Interview"
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.interview.signals  # noqa: F401
        except ImportError:
            pass
