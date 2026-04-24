"""
Jobs Services
=============
Minimal business logic used by active jobs APIs.
"""

from datetime import timedelta
from typing import Optional
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.jobs.models import ApplicationActivity, JobApplication, SavedJob


class SavedJobService:
    """Service for saved-job operations."""

    @staticmethod
    @transaction.atomic
    def save_job(user, job, notes: str = "") -> SavedJob:
        saved, created = SavedJob.objects.get_or_create(
            user=user,
            job=job,
            defaults={"notes": notes},
        )

        if not created and notes:
            saved.notes = notes
            saved.save(update_fields=["notes"])

        return saved

    @staticmethod
    def unsave_job(user, job_id: UUID) -> bool:
        deleted, _ = SavedJob.objects.filter(user=user, job_id=job_id).delete()
        return deleted > 0

    @staticmethod
    def get_user_saved_jobs(user):
        return SavedJob.objects.filter(user=user).select_related("job__company").order_by("-created_at")


class ApplicationService:
    """Service for job-application operations."""

    @staticmethod
    @transaction.atomic
    def update_application_status(application: JobApplication, new_status: str, note: str = "") -> JobApplication:
        old_status = application.status
        application.status = new_status
        application.last_updated_at = timezone.now()
        application.save(update_fields=["status", "last_updated_at"])

        ApplicationActivity.objects.create(
            application=application,
            activity_type=ApplicationActivity.ActivityType.STATUS_CHANGE,
            description=f"Status changed from {old_status} to {new_status}",
            metadata={
                "old_status": old_status,
                "new_status": new_status,
                "note": note,
            },
        )

        return application

    @staticmethod
    def get_user_applications(user, status: Optional[str] = None, include_deleted: bool = False):
        queryset = JobApplication.objects.filter(user=user)

        if not include_deleted:
            queryset = queryset.filter(is_deleted=False)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.select_related("job__company").order_by("-created_at")
