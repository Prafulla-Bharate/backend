"""
User Signals
============
Signal handlers for user-related events.
"""

import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import User, UserPreferences

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_preferences(sender, instance: User, created: bool, **kwargs):
    """Create user preferences when a new user is created."""
    if created:
        UserPreferences.objects.get_or_create(user=instance)
        logger.debug(f"Created preferences for user: {instance.email}")


@receiver(post_save, sender=User)
def log_user_created(sender, instance: User, created: bool, **kwargs):
    """Log when a new user is created."""
    if created:
        logger.info(f"New user created: {instance.email}")
