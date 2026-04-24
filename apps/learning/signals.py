"""
Learning Signals
================
Signal handlers for learning-related events.
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.learning.models import (
    LearningPath,
    UserLearningPathEnrollment,
    UserResourceProgress,
    UserCheckpointAttempt,
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=UserLearningPathEnrollment)
def handle_enrollment_created(sender, instance, created, **kwargs):
    """Log new enrollment."""
    if created:
        logger.info(
            f"User {instance.user_id} enrolled in learning path {instance.learning_path_id}"
        )


@receiver(pre_save, sender=UserLearningPathEnrollment)
def handle_enrollment_status_change(sender, instance, **kwargs):
    """Update timestamps on enrollment status changes."""
    if not instance.pk:
        return

    try:
        old_instance = UserLearningPathEnrollment.objects.get(pk=instance.pk)
    except UserLearningPathEnrollment.DoesNotExist:
        return

    if (
        old_instance.status != UserLearningPathEnrollment.EnrollmentStatus.COMPLETED
        and instance.status == UserLearningPathEnrollment.EnrollmentStatus.COMPLETED
    ):
        from django.utils import timezone
        instance.completed_at = timezone.now()
        logger.info(f"Enrollment {instance.id} completed")

    if (
        old_instance.status == UserLearningPathEnrollment.EnrollmentStatus.ENROLLED
        and instance.status == UserLearningPathEnrollment.EnrollmentStatus.IN_PROGRESS
    ):
        from django.utils import timezone
        instance.started_at = timezone.now()
        logger.info(f"Enrollment {instance.id} started")


@receiver(post_save, sender=UserResourceProgress)
def handle_resource_completed(sender, instance, **kwargs):
    """Log resource completion."""
    if instance.status == UserResourceProgress.ProgressStatus.COMPLETED:
        logger.info(
            f"User {instance.user_id} completed resource {instance.resource_id}"
        )


@receiver(post_save, sender=UserCheckpointAttempt)
def handle_checkpoint_passed(sender, instance, created, **kwargs):
    """Log checkpoint pass."""
    if created and instance.passed:
        logger.info(
            f"User {instance.user_id} passed checkpoint {instance.checkpoint_id}"
        )


@receiver(post_save, sender=LearningPath)
def handle_path_published(sender, instance, **kwargs):
    """Log learning path publication."""
    if instance.is_published:
        logger.info(f"Learning path published: {instance.id}")
