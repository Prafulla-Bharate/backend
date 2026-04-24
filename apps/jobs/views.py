"""
Jobs Views
==========
Minimal jobs API surface used by the frontend jobs page.
"""

import logging

from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.models import JobApplication, JobPosting
from apps.jobs.serializers import (
    JobApplicationListSerializer,
    SaveJobSerializer,
    SavedJobSerializer,
    TrackApplicationSerializer,
    UpdateApplicationSerializer,
)
from apps.jobs.services import ApplicationService, SavedJobService

logger = logging.getLogger(__name__)


class JobSearchView(APIView):
    """Search external jobs through the integrated provider."""

    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        query = data.get("query", "").strip() or "Software Developer"
        location = data.get("location", "")
        job_type = data.get("job_type", "")
        work_mode = data.get("work_mode", "")
        experience_level = data.get("experience_level", "")
        date_posted = data.get("date_posted", "week")
        page = int(data.get("page", 1))
        num_pages = min(int(data.get("num_pages", 1)), 1)

        remote_only = work_mode.lower() == "remote" if work_mode else False

        try:
            from services.external import get_job_search_service

            job_search_service = get_job_search_service()
            result = job_search_service.search_jobs(
                query=query,
                location=location or None,
                job_type=job_type or None,
                work_mode=work_mode or None,
                experience_level=experience_level or None,
                remote_jobs_only=remote_only,
                date_posted=date_posted,
                page=page,
                num_pages=num_pages,
            )

            return Response(
                {
                    "jobs": result.get("jobs", []),
                    "total": result.get("total", 0),
                    "page": page,
                    "query_used": query,
                    "source": result.get(
                        "source",
                        "JSearch API (LinkedIn, Indeed, Glassdoor, etc.)",
                    ),
                }
            )
        except Exception as exc:
            logger.error("External job search failed: %s", exc, exc_info=True)
            return Response(
                {"error": "Job search failed", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SavedJobViewSet(viewsets.ModelViewSet):
    """List/create/delete saved jobs for the current user."""

    permission_classes = [IsAuthenticated]
    serializer_class = SavedJobSerializer
    http_method_names = ["get", "post", "delete"]
    ordering = "-created_at"

    def get_queryset(self):
        return SavedJobService.get_user_saved_jobs(self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = SaveJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            job = JobPosting.objects.get(id=serializer.validated_data["job_id"])
        except JobPosting.DoesNotExist:
            return Response(
                {"detail": "Job not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        saved = SavedJobService.save_job(
            request.user,
            job,
            serializer.validated_data.get("notes", ""),
        )
        return Response(
            SavedJobSerializer(saved).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        SavedJobService.unsave_job(request.user, instance.job_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationViewSet(viewsets.ModelViewSet):
    """List/update/delete job applications for the current user."""

    permission_classes = [IsAuthenticated]
    serializer_class = JobApplicationListSerializer
    http_method_names = ["get", "patch", "delete"]
    ordering = "-created_at"

    def get_queryset(self):
        status_filter = self.request.query_params.get("status")
        return ApplicationService.get_user_applications(
            self.request.user,
            status=status_filter,
        )

    def partial_update(self, request, *args, **kwargs):
        application = self.get_object()
        serializer = UpdateApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "status" in data:
            application = ApplicationService.update_application_status(
                application,
                data["status"],
            )

        if "notes" in data:
            application.notes = data["notes"]
            application.save(update_fields=["notes"])

        return Response(JobApplicationListSerializer(application).data)

    def destroy(self, request, *args, **kwargs):
        application = self.get_object()
        application.is_deleted = True
        application.save(update_fields=["is_deleted"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class TrackExternalApplicationView(APIView):
    """Track externally applied jobs without requiring a local posting."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TrackApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        application = JobApplication.objects.create(
            user=request.user,
            is_external=True,
            external_company=data["company"],
            external_position=data["position"],
            external_url=data.get("external_url", ""),
            status=data.get("status", JobApplication.ApplicationStatus.SUBMITTED),
            match_score=data.get("match_score"),
            notes=data.get("notes", ""),
        )

        return Response(
            JobApplicationListSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )
