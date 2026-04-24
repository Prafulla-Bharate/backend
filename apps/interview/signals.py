"""
Interview Signals
=================
Signal handlers for interview-related events.
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.interview.models import (
    InterviewSession,
    InterviewResponse,
    InterviewSchedule,
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=InterviewSession)
def handle_session_completed(sender, instance, **kwargs):
    """Log session completion."""
    if instance.status == InterviewSession.SessionStatus.COMPLETED:
        logger.info(
            f"Interview session {instance.id} completed for user {instance.user_id}"
        )


@receiver(post_save, sender=InterviewSchedule)
def handle_schedule_created(sender, instance, created, **kwargs):
    """Log new interview schedule."""
    if created:
        logger.info(f"Interview scheduled: {instance.id}")


@receiver(pre_save, sender=InterviewSchedule)
def handle_schedule_status_change(sender, instance, **kwargs):
    """Handle schedule status changes."""
    if not instance.pk:
        return

    try:
        old_instance = InterviewSchedule.objects.get(pk=instance.pk)
    except InterviewSchedule.DoesNotExist:
        return

    if old_instance.scheduled_at != instance.scheduled_at:
        instance.status = InterviewSchedule.Status.RESCHEDULED
        logger.info(f"Interview {instance.id} rescheduled")


@receiver(post_save, sender=InterviewResponse)
def handle_response_evaluated(sender, instance, **kwargs):
    """Complete session when all responses have been evaluated."""
    if instance.ai_score is not None:
        session = instance.session
        unevaluated = session.responses.filter(
            completed_at__isnull=False,
            ai_score__isnull=True
        ).count()

        if unevaluated == 0 and session.responses.filter(
            completed_at__isnull=False
        ).exists():
            if session.status == InterviewSession.SessionStatus.IN_PROGRESS:
                from apps.interview.services import SessionService
                SessionService.complete_session(session)
