"""
Core Application Configuration
==============================
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for the Core application."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"
