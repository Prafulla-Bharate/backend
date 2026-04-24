"""
Jobs App Configuration
======================
"""

from django.apps import AppConfig


class JobsConfig(AppConfig):
    """Configuration for the Jobs app."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.jobs"
    verbose_name = "Jobs"
