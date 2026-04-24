"""
Analytics Signals
=================
Signal handlers for automatic analytics tracking.
"""

import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(pre_save, sender="learning.UserResourceProgress")
def cache_previous_learning_progress(sender, instance, **kwargs):
    """Store previous progress state so analytics updates only apply on real changes."""
    if not instance.pk:
        instance._previous_status = None
        instance._previous_time_spent_minutes = 0
        return

    try:
        previous = sender.objects.get(pk=instance.pk)
        instance._previous_status = previous.status
        instance._previous_time_spent_minutes = previous.time_spent_minutes or 0
    except sender.DoesNotExist:
        instance._previous_status = None
        instance._previous_time_spent_minutes = 0


@receiver(pre_save, sender="interview.InterviewSession")
def cache_previous_interview_status(sender, instance, **kwargs):
    """Store previous interview status so completion analytics are not double-counted."""
    if not instance.pk:
        instance._previous_status = None
        return

    try:
        previous = sender.objects.get(pk=instance.pk)
        instance._previous_status = previous.status
    except sender.DoesNotExist:
        instance._previous_status = None


@receiver(user_logged_in)
def track_login(sender, request, user, **kwargs):
    """Track user login."""
    from apps.analytics.services import ActivityService, MetricsService
    from apps.analytics.models import UserActivity
    
    # Log activity
    ActivityService.log_activity(
        user=user,
        activity_type=UserActivity.ActivityType.LOGIN,
        request=request
    )
    
    # Update metrics
    MetricsService.update_metrics(user, sessions=1)
    
    logger.info(f"User logged in: {user.email}")


@receiver(user_logged_out)
def track_logout(sender, request, user, **kwargs):
    """Track user logout."""
    from apps.analytics.services import ActivityService
    from apps.analytics.models import UserActivity
    
    if user:
        ActivityService.log_activity(
            user=user,
            activity_type=UserActivity.ActivityType.LOGOUT,
            request=request
        )


@receiver(post_save, sender="jobs.JobApplication")
def track_job_application(sender, instance, created, **kwargs):
    """Track job applications."""
    if created:
        from apps.analytics.services import ActivityService, MetricsService
        from apps.analytics.models import UserActivity
        
        # Log activity
        ActivityService.log_activity(
            user=instance.user,
            activity_type=UserActivity.ActivityType.JOB_APPLY,
            resource_type="job",
            resource_id=instance.job_id,
            resource_name=instance.job.title if instance.job else ""
        )
        
        # Update metrics
        MetricsService.update_metrics(instance.user, jobs_applied=1)


@receiver(post_save, sender="learning.UserResourceProgress")
def track_learning_progress(sender, instance, **kwargs):
    """Track learning progress updates."""
    from apps.analytics.models import UserActivity
    from apps.analytics.services import ActivityService, MetricsService

    previous_status = getattr(instance, "_previous_status", None)
    previous_time = getattr(instance, "_previous_time_spent_minutes", 0) or 0
    current_time = instance.time_spent_minutes or 0
    time_delta = max(0, current_time - previous_time)

    if time_delta > 0:
        MetricsService.update_metrics(
            instance.user,
            learning_time_minutes=time_delta,
        )

    completed_now = (
        instance.status == "completed"
        and previous_status != "completed"
    )

    if completed_now:
        ActivityService.log_activity(
            user=instance.user,
            activity_type=UserActivity.ActivityType.LEARNING_COMPLETE,
            resource_type="learning_resource",
            resource_id=instance.resource_id,
            resource_name=instance.resource.title if instance.resource else "",
        )
        MetricsService.update_metrics(
            instance.user,
            resources_completed=1,
        )


@receiver(post_save, sender="interview.InterviewSession")
def track_interview_session(sender, instance, **kwargs):
    """Track interview session completion."""
    previous_status = getattr(instance, "_previous_status", None)
    if instance.status == "completed" and previous_status != "completed":
        from apps.analytics.services import ActivityService, MetricsService
        from apps.analytics.models import UserActivity
        
        # Log activity
        ActivityService.log_activity(
            user=instance.user,
            activity_type=UserActivity.ActivityType.INTERVIEW_COMPLETE,
            resource_type="interview_session",
            resource_id=instance.id,
            resource_name=instance.title
        )
        
        # Update metrics
        MetricsService.update_metrics(
            instance.user,
            practice_sessions=1,
            questions_answered=instance.responses.count()
        )


