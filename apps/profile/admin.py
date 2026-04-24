"""
Profile Admin Configuration
===========================
Django admin configuration for profile models.
"""

from django.contrib import admin
from django.utils.html import format_html

from apps.profile.models import (
    UserEducation,
    UserExperience,
    SkillCategory,
    Skill,
    UserSkill,
    InterestCategory,
    Interest,
    UserInterest,
    UserCertification,
    UserProject,
    UserLanguage,
    UserSocialLink,
)


@admin.register(UserEducation)
class UserEducationAdmin(admin.ModelAdmin):
    """Admin configuration for UserEducation."""
    
    list_display = [
        "user",
        "institution_name",
        "degree_type",
        "field_of_study",
        "start_date",
        "end_date",
        "is_current",
        "is_verified",
    ]
    list_filter = ["degree_type", "is_current", "is_verified"]
    search_fields = [
        "user__email",
        "user__first_name",
        "institution_name",
        "field_of_study",
    ]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    
    fieldsets = [
        (None, {
            "fields": ("user", "institution_name", "degree_type", "degree_name")
        }),
        ("Details", {
            "fields": (
                "field_of_study", "start_date", "end_date", "is_current",
                "gpa", "gpa_scale", "description", "achievements"
            )
        }),
        ("Location", {
            "fields": ("location", "institution_url")
        }),
        ("Verification", {
            "fields": ("is_verified", "verified_at")
        }),
    ]


@admin.register(UserExperience)
class UserExperienceAdmin(admin.ModelAdmin):
    """Admin configuration for UserExperience."""
    
    list_display = [
        "user",
        "job_title",
        "company_name",
        "employment_type",
        "start_date",
        "end_date",
        "is_current",
        "is_verified",
    ]
    list_filter = [
        "employment_type",
        "work_location_type",
        "is_current",
        "is_verified",
    ]
    search_fields = [
        "user__email",
        "user__first_name",
        "job_title",
        "company_name",
    ]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    
    fieldsets = [
        (None, {
            "fields": (
                "user", "company_name", "job_title", "employment_type",
                "work_location_type"
            )
        }),
        ("Duration", {
            "fields": ("start_date", "end_date", "is_current")
        }),
        ("Details", {
            "fields": (
                "location", "description", "responsibilities",
                "achievements", "technologies"
            )
        }),
        ("Company Info", {
            "fields": ("company_url", "company_industry", "company_size")
        }),
        ("AI Extracted", {
            "fields": ("extracted_skills", "normalized_title"),
            "classes": ("collapse",)
        }),
        ("Verification", {
            "fields": ("is_verified", "verified_at")
        }),
    ]


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for SkillCategory."""
    
    list_display = ["name", "slug", "parent", "order"]
    list_filter = ["parent"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["order", "name"]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    """Admin configuration for Skill."""
    
    list_display = [
        "name",
        "slug",
        "category",
        "is_active",
        "popularity_score",
    ]
    list_filter = ["category", "is_active"]
    search_fields = ["name", "slug", "aliases"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["related_skills"]
    ordering = ["name"]


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    """Admin configuration for UserSkill."""
    
    list_display = [
        "user",
        "skill",
        "proficiency_level",
        "years_of_experience",
        "source",
        "is_primary",
        "is_verified",
    ]
    list_filter = [
        "proficiency_level",
        "source",
        "is_primary",
        "is_verified",
        "skill__category",
    ]
    search_fields = ["user__email", "skill__name"]
    autocomplete_fields = ["user", "skill"]
    ordering = ["-created_at"]


@admin.register(InterestCategory)
class InterestCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for InterestCategory."""
    
    list_display = ["name", "slug", "order"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["order", "name"]


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    """Admin configuration for Interest."""
    
    list_display = ["name", "slug", "category", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["related_skills"]
    ordering = ["name"]


@admin.register(UserInterest)
class UserInterestAdmin(admin.ModelAdmin):
    """Admin configuration for UserInterest."""
    
    list_display = [
        "user",
        "interest",
        "interest_level",
        "source",
        "is_primary",
    ]
    list_filter = ["interest_level", "source", "is_primary", "interest__category"]
    search_fields = ["user__email", "interest__name"]
    autocomplete_fields = ["user", "interest"]
    ordering = ["-created_at"]


@admin.register(UserCertification)
class UserCertificationAdmin(admin.ModelAdmin):
    """Admin configuration for UserCertification."""
    
    list_display = [
        "user",
        "name",
        "issuing_organization",
        "issue_date",
        "expiry_status",
        "is_verified",
    ]
    list_filter = ["issuing_organization", "does_not_expire", "is_verified"]
    search_fields = [
        "user__email",
        "name",
        "issuing_organization",
        "credential_id",
    ]
    filter_horizontal = ["related_skills"]
    ordering = ["-issue_date"]
    
    def expiry_status(self, obj):
        """Display expiry status with color coding."""
        if obj.does_not_expire:
            return format_html('<span style="color: green;">No Expiry</span>')
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        return format_html(
            '<span style="color: blue;">Valid until {}</span>',
            obj.expiry_date
        )
    expiry_status.short_description = "Expiry Status"


@admin.register(UserProject)
class UserProjectAdmin(admin.ModelAdmin):
    """Admin configuration for UserProject."""
    
    list_display = [
        "user",
        "title",
        "status",
        "is_featured",
        "is_public",
        "view_count",
    ]
    list_filter = ["status", "is_featured", "is_public"]
    search_fields = ["user__email", "title", "description"]
    filter_horizontal = ["related_skills"]
    ordering = ["-created_at"]


@admin.register(UserLanguage)
class UserLanguageAdmin(admin.ModelAdmin):
    """Admin configuration for UserLanguage."""
    
    list_display = [
        "user",
        "language_name",
        "proficiency",
        "is_native",
        "is_verified",
    ]
    list_filter = ["proficiency", "is_native", "is_verified"]
    search_fields = ["user__email", "language_name", "language_code"]
    ordering = ["user", "-is_native", "language_name"]


@admin.register(UserSocialLink)
class UserSocialLinkAdmin(admin.ModelAdmin):
    """Admin configuration for UserSocialLink."""
    
    list_display = [
        "user",
        "platform",
        "username",
        "is_primary",
        "is_verified",
        "clickable_url",
    ]
    list_filter = ["platform", "is_primary", "is_verified"]
    search_fields = ["user__email", "username", "url"]
    ordering = ["user", "platform"]
    
    def clickable_url(self, obj):
        """Display clickable URL."""
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            obj.url,
            obj.url[:50] + "..." if len(obj.url) > 50 else obj.url
        )
    clickable_url.short_description = "URL"
