"""
Learning Admin Configuration
============================
Django admin configuration for learning models.
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from apps.learning.models import (
    LearningPath,
    LearningPhase,
    LearningResource,
    UserLearningPathEnrollment,
    UserResourceProgress,
    KnowledgeCheckpoint,
    UserCheckpointAttempt,
    RecommendedResource,
    ProjectSubmission,
    CertificateVerification,
)


class LearningPhaseInline(admin.TabularInline):
    """Inline for learning phases."""
    
    model = LearningPhase
    extra = 0
    fields = ["title", "order", "estimated_hours"]
    ordering = ["order"]


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    """Admin configuration for LearningPath."""
    
    list_display = [
        "title",
        "difficulty",
        "category",
        "estimated_hours",
        "enrollments_count",
        "average_rating_display",
        "is_published",
        "is_featured",
    ]
    list_filter = ["difficulty", "category", "is_published", "is_featured", "is_ai_generated"]
    search_fields = ["title", "description"]
    prepopulated_fields = {"slug": ("title",)}
    ordering = ["-is_featured", "-created_at"]
    filter_horizontal = ["target_careers"]
    inlines = [LearningPhaseInline]
    
    fieldsets = [
        (None, {
            "fields": ("title", "slug", "description", "short_description")
        }),
        ("Classification", {
            "fields": ("difficulty", "category", "tags")
        }),
        ("Content", {
            "fields": (
                "skills_covered", "prerequisites", "objectives",
                "estimated_hours", "thumbnail"
            )
        }),
        ("Relations", {
            "fields": ("target_careers",)
        }),
        ("AI Generation", {
            "fields": ("is_ai_generated", "ai_model_used"),
            "classes": ("collapse",)
        }),
        ("Statistics", {
            "fields": ("enrollments_count", "completions_count", "average_rating"),
            "classes": ("collapse",)
        }),
        ("Status", {
            "fields": ("is_published", "is_featured")
        }),
    ]
    
    def average_rating_display(self, obj):
        """Display rating with stars."""
        rating = float(obj.average_rating or 0)
        stars = "★" * int(rating) + "☆" * (5 - int(rating))
        return format_html(
            '<span title="{:.2f}">{}</span>',
            rating, stars
        )
    average_rating_display.short_description = "Rating"


@admin.register(LearningPhase)
class LearningPhaseAdmin(admin.ModelAdmin):
    """Admin configuration for LearningPhase."""
    
    list_display = [
        "title",
        "learning_path",
        "order",
        "estimated_hours",
        "resources_count",
    ]
    list_filter = ["learning_path"]
    search_fields = ["title", "learning_path__title"]
    ordering = ["learning_path", "order"]
    
    def resources_count(self, obj):
        return obj.resources.count()
    resources_count.short_description = "Resources"


@admin.register(LearningResource)
class LearningResourceAdmin(admin.ModelAdmin):
    """Admin configuration for LearningResource."""
    
    list_display = [
        "title",
        "resource_type",
        "provider",
        "difficulty",
        "duration_minutes",
        "is_free",
        "average_rating",
        "completions_count",
    ]
    list_filter = ["resource_type", "provider", "difficulty", "is_free"]
    search_fields = ["title", "description", "author"]
    ordering = ["-created_at"]
    
    fieldsets = [
        (None, {
            "fields": ("title", "description", "url", "thumbnail")
        }),
        ("Type", {
            "fields": ("resource_type", "provider", "author", "difficulty")
        }),
        ("Duration & Pricing", {
            "fields": ("duration_minutes", "is_free", "price", "price_currency")
        }),
        ("Classification", {
            "fields": ("skills", "tags")
        }),
        ("Phase Association", {
            "fields": ("phase", "order_in_phase")
        }),
        ("Statistics", {
            "fields": ("views_count", "completions_count", "average_rating"),
            "classes": ("collapse",)
        }),
    ]


@admin.register(UserLearningPathEnrollment)
class UserLearningPathEnrollmentAdmin(admin.ModelAdmin):
    """Admin configuration for enrollments."""
    
    list_display = [
        "user",
        "learning_path",
        "status",
        "progress_percentage",
        "started_at",
        "completed_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["user__email", "learning_path__title"]
    ordering = ["-created_at"]


@admin.register(UserResourceProgress)
class UserResourceProgressAdmin(admin.ModelAdmin):
    """Admin configuration for resource progress."""
    
    list_display = [
        "user",
        "resource",
        "status",
        "progress_percentage",
        "time_spent_minutes",
        "is_bookmarked",
    ]
    list_filter = ["status", "is_bookmarked"]
    search_fields = ["user__email", "resource__title"]
    ordering = ["-updated_at"]


@admin.register(KnowledgeCheckpoint)
class KnowledgeCheckpointAdmin(admin.ModelAdmin):
    """Admin configuration for checkpoints."""
    
    list_display = [
        "title",
        "phase",
        "checkpoint_type",
        "passing_score",
        "max_attempts",
        "is_required",
    ]
    list_filter = ["checkpoint_type", "is_required"]
    search_fields = ["title", "phase__title"]
    ordering = ["phase", "order"]


@admin.register(UserCheckpointAttempt)
class UserCheckpointAttemptAdmin(admin.ModelAdmin):
    """Admin configuration for checkpoint attempts."""
    
    list_display = [
        "user",
        "checkpoint",
        "attempt_number",
        "score",
        "passed",
        "created_at",
    ]
    list_filter = ["passed", "created_at"]
    search_fields = ["user__email", "checkpoint__title"]
    ordering = ["-created_at"]


@admin.register(RecommendedResource)
class RecommendedResourceAdmin(admin.ModelAdmin):
    """Admin configuration for recommendations."""
    
    list_display = [
        "user",
        "resource",
        "relevance_score",
        "for_skill",
        "is_viewed",
        "is_dismissed",
    ]
    list_filter = ["is_viewed", "is_dismissed"]
    search_fields = ["user__email", "resource__title"]
    ordering = ["-created_at"]


@admin.register(ProjectSubmission)
class ProjectSubmissionAdmin(admin.ModelAdmin):
    """Admin queue for reviewing project submissions."""

    list_display = [
        "title",
        "user",
        "status",
        "overall_score",
        "phase",
        "created_at",
        "reviewed_at",
    ]
    list_filter = ["status", "phase", "created_at", "reviewed_at"]
    search_fields = ["title", "description", "user__email", "project_url"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["mark_approved", "mark_needs_revision", "mark_rejected"]

    fieldsets = [
        ("Submission", {
            "fields": (
                "id", "user", "phase", "enrollment", "title", "description",
                "project_url", "live_demo_url", "technologies", "skills_demonstrated",
            )
        }),
        ("Review", {
            "fields": ("status", "overall_score", "ai_review", "reviewed_at", "reviewer_notes")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    ]

    @admin.action(description="Mark selected projects as Approved")
    def mark_approved(self, request, queryset):
        count = queryset.update(
            status=ProjectSubmission.SubmissionStatus.APPROVED,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"{count} project(s) marked as approved.")

    @admin.action(description="Mark selected projects as Needs Revision")
    def mark_needs_revision(self, request, queryset):
        count = queryset.update(
            status=ProjectSubmission.SubmissionStatus.NEEDS_REVISION,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"{count} project(s) marked as needs revision.")

    @admin.action(description="Mark selected projects as Rejected")
    def mark_rejected(self, request, queryset):
        count = queryset.update(
            status=ProjectSubmission.SubmissionStatus.REJECTED,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"{count} project(s) marked as rejected.")


@admin.register(CertificateVerification)
class CertificateVerificationAdmin(admin.ModelAdmin):
    """Admin queue for manual certificate verification."""

    list_display = [
        "course_name",
        "platform",
        "user",
        "status",
        "verification_method",
        "confidence_display",
        "created_at",
        "verified_at",
    ]
    list_filter = ["status", "verification_method", "platform", "created_at", "verified_at"]
    search_fields = ["course_name", "platform", "certificate_id", "user__email", "certificate_url"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["mark_verified_manual", "mark_manual_review", "mark_rejected"]

    fieldsets = [
        ("Certificate", {
            "fields": (
                "id", "user", "resource", "enrollment",
                "course_name", "platform", "completion_date", "certificate_id",
                "certificate_url", "certificate_image", "skills_covered",
            )
        }),
        ("Verification", {
            "fields": (
                "status", "verification_method", "confidence_score", "verified_at",
                "verification_notes", "ocr_extracted_data",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    ]

    def confidence_display(self, obj):
        if obj.confidence_score is None:
            return "—"
        score = obj.confidence_score * 100 if obj.confidence_score <= 1 else obj.confidence_score
        return f"{round(score)}%"
    confidence_display.short_description = "Confidence"

    @admin.action(description="Mark selected certificates as Verified (Manual)")
    def mark_verified_manual(self, request, queryset):
        count = queryset.update(
            status=CertificateVerification.VerificationStatus.VERIFIED,
            verification_method=CertificateVerification.VerificationMethod.MANUAL,
            verified_at=timezone.now(),
        )
        self.message_user(request, f"{count} certificate(s) marked as verified manually.")

    @admin.action(description="Mark selected certificates as Manual Review")
    def mark_manual_review(self, request, queryset):
        count = queryset.update(
            status=CertificateVerification.VerificationStatus.MANUAL_REVIEW,
            verification_method=CertificateVerification.VerificationMethod.MANUAL,
        )
        self.message_user(request, f"{count} certificate(s) marked for manual review.")

    @admin.action(description="Mark selected certificates as Rejected")
    def mark_rejected(self, request, queryset):
        count = queryset.update(
            status=CertificateVerification.VerificationStatus.REJECTED,
            verification_method=CertificateVerification.VerificationMethod.MANUAL,
        )
        self.message_user(request, f"{count} certificate(s) marked as rejected.")
