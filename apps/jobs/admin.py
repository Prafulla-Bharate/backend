"""
Jobs Admin Configuration
========================
Django admin configuration for job models.
"""

from django.contrib import admin
from django.utils.html import format_html

from apps.jobs.models import (
    Company,
    JobPosting,
    SavedJob,
    JobApplication,
    ApplicationActivity,
    JobAlert,
    JobRecommendation,
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Admin configuration for Company."""
    
    list_display = [
        "name",
        "industry",
        "size",
        "headquarters",
        "is_verified",
        "jobs_count",
    ]
    list_filter = ["industry", "size", "is_verified"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["name"]
    
    def jobs_count(self, obj):
        return obj.job_postings.count()
    jobs_count.short_description = "Jobs"


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    """Admin configuration for JobPosting."""
    
    list_display = [
        "title",
        "company",
        "job_type",
        "experience_level",
        "work_arrangement",
        "location",
        "status",
        "is_featured",
        "applications_count",
        "posted_at",
    ]
    list_filter = [
        "status", "job_type", "experience_level",
        "work_arrangement", "is_featured"
    ]
    search_fields = ["title", "description", "company__name"]
    prepopulated_fields = {"slug": ("title",)}
    ordering = ["-posted_at"]
    autocomplete_fields = ["company"]
    
    fieldsets = [
        (None, {
            "fields": ("title", "slug", "description", "company")
        }),
        ("Type & Level", {
            "fields": ("job_type", "experience_level", "work_arrangement")
        }),
        ("Location", {
            "fields": ("location", "city", "state", "country")
        }),
        ("Salary", {
            "fields": (
                "salary_min", "salary_max", "salary_currency",
                "salary_period", "show_salary"
            )
        }),
        ("Requirements", {
            "fields": (
                "required_skills", "preferred_skills",
                "required_education", "required_experience_years",
                "benefits"
            )
        }),
        ("Application", {
            "fields": ("apply_url", "apply_email")
        }),
        ("Relations", {
            "fields": ("career_path",)
        }),
        ("Source", {
            "fields": ("source", "external_id", "source_url"),
            "classes": ("collapse",)
        }),
        ("Status", {
            "fields": ("status", "posted_at", "expires_at", "is_featured")
        }),
        ("Statistics", {
            "fields": ("views_count", "applications_count"),
            "classes": ("collapse",)
        }),
    ]


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    """Admin configuration for SavedJob."""
    
    list_display = ["user", "job", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__email", "job__title"]
    ordering = ["-created_at"]


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    """Admin configuration for JobApplication."""
    
    list_display = [
        "user",
        "job",
        "status",
        "match_score_display",
        "submitted_at",
        "is_deleted",
    ]
    list_filter = ["status", "is_deleted", "cover_letter_ai_generated"]
    search_fields = ["user__email", "job__title"]
    ordering = ["-created_at"]
    
    def match_score_display(self, obj):
        """Display match score with color."""
        score = float(obj.match_score or 0)
        color = "green" if score >= 70 else "orange" if score >= 40 else "red"
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, score
        )
    match_score_display.short_description = "Match"


@admin.register(ApplicationActivity)
class ApplicationActivityAdmin(admin.ModelAdmin):
    """Admin configuration for ApplicationActivity."""
    
    list_display = ["application", "activity_type", "created_at"]
    list_filter = ["activity_type", "created_at"]
    search_fields = ["application__job__title", "description"]
    ordering = ["-created_at"]


@admin.register(JobAlert)
class JobAlertAdmin(admin.ModelAdmin):
    """Admin configuration for JobAlert."""
    
    list_display = [
        "user",
        "name",
        "frequency",
        "is_active",
        "last_sent_at",
    ]
    list_filter = ["frequency", "is_active"]
    search_fields = ["user__email", "name"]
    ordering = ["-created_at"]


@admin.register(JobRecommendation)
class JobRecommendationAdmin(admin.ModelAdmin):
    """Admin configuration for JobRecommendation."""
    
    list_display = [
        "user",
        "job",
        "match_score",
        "is_viewed",
        "is_dismissed",
        "created_at",
    ]
    list_filter = ["is_viewed", "is_dismissed"]
    search_fields = ["user__email", "job__title"]
    ordering = ["-match_score"]
