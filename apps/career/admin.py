"""
Career Admin Configuration
==========================
Django admin configuration for career models.
"""

from django.contrib import admin
from django.utils.html import format_html

from apps.career.models import (
    CareerPath,
    CareerPrediction,
    CareerMarketTrend,
    UserCareerGoal,
    UserCareerBookmark,
    CareerComparison,
)


@admin.register(CareerPath)
class CareerPathAdmin(admin.ModelAdmin):
    """Admin configuration for CareerPath."""
    
    list_display = [
        "title",
        "career_level",
        "industry",
        "category",
        "demand_score_display",
        "growth_rate",
        "salary_median",
        "job_openings",
        "is_active",
    ]
    list_filter = [
        "career_level",
        "industry",
        "category",
        "is_active",
    ]
    search_fields = ["title", "description", "required_skills"]
    prepopulated_fields = {"slug": ("title",)}
    ordering = ["-demand_score", "title"]
    filter_horizontal = ["next_paths"]
    
    fieldsets = [
        (None, {
            "fields": ("title", "slug", "description", "is_active")
        }),
        ("Classification", {
            "fields": ("career_level", "industry", "category")
        }),
        ("Requirements", {
            "fields": (
                "required_skills", "preferred_skills",
                "required_education", "required_experience_years",
                "certifications"
            )
        }),
        ("Career Progression", {
            "fields": ("parent_path", "next_paths")
        }),
        ("Salary", {
            "fields": ("salary_min", "salary_max", "salary_median")
        }),
        ("Market Data", {
            "fields": (
                "demand_score", "growth_rate", "job_openings",
                "last_updated_market_data"
            )
        }),
        ("Content", {
            "fields": ("day_in_life", "challenges", "rewards"),
            "classes": ("collapse",)
        }),
    ]
    
    def demand_score_display(self, obj):
        """Display demand score with color."""
        score = float(obj.demand_score or 0)
        color = "green" if score >= 0.7 else "orange" if score >= 0.4 else "red"
        return format_html(
            '<span style="color: {};">{:.2f}</span>',
            color, score
        )
    demand_score_display.short_description = "Demand"


@admin.register(CareerPrediction)
class CareerPredictionAdmin(admin.ModelAdmin):
    """Admin configuration for CareerPrediction."""
    
    list_display = [
        "user",
        "status",
        "confidence_score",
        "model_used",
        "user_rating",
        "created_at",
    ]
    list_filter = ["status", "model_used", "created_at"]
    search_fields = ["user__email"]
    ordering = ["-created_at"]
    readonly_fields = [
        "model_used", "model_version", "processing_time_ms",
        "tokens_used", "created_at"
    ]
    
    fieldsets = [
        (None, {
            "fields": ("user", "status", "error_message")
        }),
        ("Input", {
            "fields": ("input_data",),
            "classes": ("collapse",)
        }),
        ("Results", {
            "fields": (
                "recommended_careers", "current_career_assessment",
                "skill_gaps", "recommended_skills",
                "recommended_courses", "career_timeline",
                "salary_projection"
            ),
            "classes": ("collapse",)
        }),
        ("AI Metadata", {
            "fields": (
                "model_used", "model_version", "confidence_score",
                "processing_time_ms", "tokens_used"
            )
        }),
        ("Feedback", {
            "fields": ("user_rating", "user_feedback")
        }),
    ]


@admin.register(CareerMarketTrend)
class CareerMarketTrendAdmin(admin.ModelAdmin):
    """Admin configuration for CareerMarketTrend."""
    
    list_display = [
        "name",
        "trend_type",
        "direction",
        "change_percentage",
        "industry",
        "is_featured",
        "data_date",
    ]
    list_filter = ["trend_type", "direction", "industry", "is_featured"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["-data_date", "-change_percentage"]
    
    fieldsets = [
        (None, {
            "fields": ("name", "slug", "trend_type", "direction", "is_featured")
        }),
        ("Values", {
            "fields": (
                "current_value", "previous_value", "change_percentage",
                "historical_data"
            )
        }),
        ("Context", {
            "fields": (
                "industry", "region", "description", "impact_analysis",
                "related_skills", "related_careers"
            )
        }),
        ("Source", {
            "fields": ("data_source", "data_date")
        }),
    ]


@admin.register(UserCareerGoal)
class UserCareerGoalAdmin(admin.ModelAdmin):
    """Admin configuration for UserCareerGoal."""
    
    list_display = [
        "user",
        "title",
        "target_career",
        "status",
        "priority",
        "progress_percentage",
        "target_date",
    ]
    list_filter = ["status", "priority"]
    search_fields = ["user__email", "title"]
    ordering = ["-created_at"]
    
    fieldsets = [
        (None, {
            "fields": ("user", "target_career", "title", "description")
        }),
        ("Status", {
            "fields": (
                "status", "priority", "progress_percentage",
                "target_date", "started_at", "completed_at"
            )
        }),
        ("Milestones", {
            "fields": ("milestones",),
            "classes": ("collapse",)
        }),
        ("AI Plan", {
            "fields": ("action_plan", "recommended_resources"),
            "classes": ("collapse",)
        }),
        ("Notes", {
            "fields": ("notes",)
        }),
    ]


@admin.register(UserCareerBookmark)
class UserCareerBookmarkAdmin(admin.ModelAdmin):
    """Admin configuration for UserCareerBookmark."""
    
    list_display = ["user", "career_path", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__email", "career_path__title"]
    ordering = ["-created_at"]


@admin.register(CareerComparison)
class CareerComparisonAdmin(admin.ModelAdmin):
    """Admin configuration for CareerComparison."""
    
    list_display = [
        "user",
        "career_count",
        "recommended_career",
        "model_used",
        "created_at",
    ]
    list_filter = ["created_at"]
    search_fields = ["user__email"]
    filter_horizontal = ["careers"]
    ordering = ["-created_at"]
    
    def career_count(self, obj):
        """Display number of careers compared."""
        return obj.careers.count()
    career_count.short_description = "Careers"
