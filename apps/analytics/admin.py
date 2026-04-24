"""
Analytics Admin Configuration
==============================
Django admin configuration for analytics models.
"""

from django.contrib import admin
from django.utils.html import format_html

from apps.analytics.models import (
    UserActivity,
    UserMetrics,
    CareerAnalytics,
    LearningAnalytics,
    JobSearchAnalytics,
    InterviewAnalytics,
    PlatformMetrics,
    AnalyticsEvent,
)


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """Admin for user activities."""
    
    list_display = [
        "user",
        "activity_type",
        "resource_type",
        "device_type",
        "created_at",
    ]
    list_filter = ["activity_type", "device_type", "created_at"]
    search_fields = ["user__email", "resource_name", "description"]
    ordering = ["-created_at"]
    readonly_fields = [
        "id", "user", "activity_type", "description",
        "resource_type", "resource_id", "resource_name",
        "ip_address", "user_agent", "path",
        "device_type", "browser", "os",
        "session_id", "metadata", "created_at"
    ]


@admin.register(UserMetrics)
class UserMetricsAdmin(admin.ModelAdmin):
    """Admin for user metrics."""
    
    list_display = [
        "user",
        "date",
        "page_views",
        "sessions",
        "jobs_applied",
        "learning_time_minutes",
        "practice_sessions",
    ]
    list_filter = ["date"]
    search_fields = ["user__email"]
    ordering = ["-date"]
    date_hierarchy = "date"


@admin.register(CareerAnalytics)
class CareerAnalyticsAdmin(admin.ModelAdmin):
    """Admin for career analytics."""
    
    list_display = [
        "user",
        "career_path",
        "overall_progress",
        "skills_progress",
        "updated_at",
    ]
    search_fields = ["user__email"]
    ordering = ["-updated_at"]
    
    fieldsets = [
        (None, {
            "fields": ("user", "career_path")
        }),
        ("Progress", {
            "fields": (
                "overall_progress", "skills_progress",
                "experience_progress", "education_progress"
            )
        }),
        ("Skills", {
            "fields": (
                "total_skills", "acquired_skills", "in_progress_skills",
                "missing_skills", "strong_skills"
            ),
            "classes": ("collapse",)
        }),
        ("Market Position", {
            "fields": (
                "market_demand_score", "salary_percentile", "competition_level"
            ),
            "classes": ("collapse",)
        }),
        ("Recommendations", {
            "fields": ("next_steps", "recommended_resources"),
            "classes": ("collapse",)
        }),
        ("Timeline", {
            "fields": ("estimated_completion_date", "days_to_goal"),
            "classes": ("collapse",)
        }),
    ]


@admin.register(LearningAnalytics)
class LearningAnalyticsAdmin(admin.ModelAdmin):
    """Admin for learning analytics."""
    
    list_display = [
        "user",
        "total_learning_time_hours",
        "total_resources_completed",
        "current_streak_days",
        "updated_at",
    ]
    search_fields = ["user__email"]
    ordering = ["-updated_at"]


@admin.register(JobSearchAnalytics)
class JobSearchAnalyticsAdmin(admin.ModelAdmin):
    """Admin for job search analytics."""
    
    list_display = [
        "user",
        "total_applications",
        "interviews_scheduled",
        "offers_received",
        "response_rate",
        "updated_at",
    ]
    search_fields = ["user__email"]
    ordering = ["-updated_at"]


@admin.register(InterviewAnalytics)
class InterviewAnalyticsAdmin(admin.ModelAdmin):
    """Admin for interview analytics."""
    
    list_display = [
        "user",
        "total_practice_sessions",
        "total_questions_answered",
        "average_score",
        "updated_at",
    ]
    search_fields = ["user__email"]
    ordering = ["-updated_at"]


@admin.register(PlatformMetrics)
class PlatformMetricsAdmin(admin.ModelAdmin):
    """Admin for platform metrics."""
    
    list_display = [
        "date",
        "total_users",
        "new_users",
        "active_users",
        "applications_submitted",
        "practice_sessions_completed",
    ]
    ordering = ["-date"]
    date_hierarchy = "date"
    
    fieldsets = [
        (None, {
            "fields": ("date",)
        }),
        ("Users", {
            "fields": (
                "total_users", "new_users",
                "active_users", "returning_users"
            )
        }),
        ("Engagement", {
            "fields": (
                "total_sessions", "average_session_duration_minutes",
                "bounce_rate"
            )
        }),
        ("Jobs", {
            "fields": (
                "jobs_posted", "applications_submitted", "jobs_filled"
            )
        }),
        ("Learning", {
            "fields": (
                "resources_accessed", "learning_hours", "completions"
            )
        }),
        ("Interviews", {
            "fields": (
                "practice_sessions_completed", "questions_answered"
            )
        }),
        ("Resumes", {
            "fields": (
                "resumes_created", "resumes_downloaded"
            )
        }),
    ]


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    """Admin for analytics events."""
    
    list_display = [
        "event_name",
        "user",
        "device_type",
        "country",
        "timestamp",
    ]
    list_filter = ["event_name", "device_type", "timestamp"]
    search_fields = ["event_name", "user__email"]
    ordering = ["-timestamp"]
    readonly_fields = [
        "id", "event_name", "user", "properties",
        "session_id", "page_url", "referrer",
        "device_id", "device_type", "browser", "os",
        "screen_resolution", "ip_address",
        "country", "region", "city", "timestamp"
    ]
