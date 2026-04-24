"""
Jobs Serializers
================
Minimal serializers for active jobs endpoints.
"""

from rest_framework import serializers

from apps.jobs.models import JobApplication, JobPosting, SavedJob


class JobPostingListSerializer(serializers.ModelSerializer):
    """Compact job posting serializer used inside saved jobs payload."""

    company_name = serializers.CharField(source="company.name", read_only=True)
    company_logo = serializers.URLField(source="company.logo", read_only=True)

    class Meta:
        model = JobPosting
        fields = [
            "id",
            "title",
            "slug",
            "company_name",
            "company_logo",
            "job_type",
            "experience_level",
            "work_arrangement",
            "location",
            "salary_min",
            "salary_max",
            "show_salary",
            "is_featured",
            "posted_at",
        ]


class SavedJobSerializer(serializers.ModelSerializer):
    """Serializer for saved jobs list/create responses."""

    job = JobPostingListSerializer(read_only=True)

    class Meta:
        model = SavedJob
        fields = ["id", "job", "notes", "created_at"]


class SaveJobSerializer(serializers.Serializer):
    """Serializer for save-job request."""

    job_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True)


class JobApplicationListSerializer(serializers.ModelSerializer):
    """Unified serializer for internal and external job applications."""

    position = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    company_logo = serializers.SerializerMethodField()
    applied_date = serializers.DateTimeField(source="created_at", read_only=True)
    external_url = serializers.URLField(read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "position",
            "company",
            "company_logo",
            "status",
            "match_score",
            "is_external",
            "external_url",
            "notes",
            "submitted_at",
            "applied_date",
            "created_at",
        ]

    def get_position(self, obj):
        if obj.is_external:
            return obj.external_position
        return obj.job.title if obj.job else ""

    def get_company(self, obj):
        if obj.is_external:
            return obj.external_company
        if obj.job and obj.job.company:
            return obj.job.company.name
        return ""

    def get_company_logo(self, obj):
        if obj.is_external:
            return None
        if obj.job and obj.job.company:
            return obj.job.company.logo
        return None


class TrackApplicationSerializer(serializers.Serializer):
    """Serializer for tracking an external job application."""

    company = serializers.CharField(max_length=255)
    position = serializers.CharField(max_length=255)
    external_url = serializers.URLField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=JobApplication.ApplicationStatus.choices,
        default=JobApplication.ApplicationStatus.SUBMITTED,
    )
    match_score = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class UpdateApplicationSerializer(serializers.Serializer):
    """Serializer for patching application status/notes."""

    status = serializers.ChoiceField(
        choices=JobApplication.ApplicationStatus.choices,
        required=False,
    )
    notes = serializers.CharField(required=False, allow_blank=True)
