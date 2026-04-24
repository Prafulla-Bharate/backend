"""
Career Application Configuration
================================
"""

from django.apps import AppConfig


class CareerConfig(AppConfig):
    """Configuration for the Career application."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.career"
    verbose_name = "Career"
