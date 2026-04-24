"""
Interview Admin Configuration
=============================
Django admin configuration for interview models.
"""

from django.contrib import admin
from django.utils.html import format_html

from apps.interview.models import (
    InterviewQuestion,
    InterviewSession,
    InterviewResponse,
    InterviewTip,
    UserInterviewPreference,
    InterviewSchedule,
)


@admin.register(InterviewQuestion)
class InterviewQuestionAdmin(admin.ModelAdmin):
    """Admin configuration for InterviewQuestion."""
    
    list_display = [
        "question_preview",
        "question_type",
        "difficulty",
        "category",
        "times_asked",
        "average_rating",
        "is_active",
    ]
    list_filter = ["question_type", "difficulty", "category", "is_active"]
    search_fields = ["question", "category", "tags"]
    filter_horizontal = ["career_paths"]
    ordering = ["-times_asked"]
    
    fieldsets = [
        (None, {
            "fields": ("question", "question_type", "difficulty", "category")
        }),
        ("Classification", {
            "fields": ("tags", "companies", "expected_topics")
        }),
        ("Answer Guidance", {
            "fields": ("sample_answer", "answer_tips")
        }),
        ("STAR Method Hints", {
            "fields": (
                "situation_hint", "task_hint",
                "action_hint", "result_hint"
            ),
            "classes": ("collapse",)
        }),
        ("Relations", {
            "fields": ("career_paths",)
        }),
        ("Statistics", {
            "fields": ("times_asked", "average_rating"),
            "classes": ("collapse",)
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
    ]
    
    def question_preview(self, obj):
        return obj.question[:80] + "..." if len(obj.question) > 80 else obj.question
    question_preview.short_description = "Question"


class InterviewResponseInline(admin.TabularInline):
    """Inline for interview responses."""
    
    model = InterviewResponse
    extra = 0
    fields = ["order", "question", "ai_score", "completed_at"]
    readonly_fields = ["question", "ai_score", "completed_at"]
    ordering = ["order"]


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    """Admin configuration for InterviewSession."""
    
    list_display = [
        "title",
        "user",
        "session_type",
        "status",
        "num_questions",
        "overall_score",
        "completed_at",
    ]
    list_filter = ["session_type", "status", "difficulty_preference"]
    search_fields = ["title", "user__email", "target_company"]
    ordering = ["-created_at"]
    inlines = [InterviewResponseInline]
    
    fieldsets = [
        (None, {
            "fields": ("user", "title", "session_type", "status")
        }),
        ("Target", {
            "fields": ("job_application", "target_career", "target_company")
        }),
        ("Settings", {
            "fields": (
                "question_types", "difficulty_preference",
                "num_questions", "duration_minutes"
            )
        }),
        ("Timing", {
            "fields": ("scheduled_at", "started_at", "completed_at")
        }),
        ("Results", {
            "fields": ("overall_score", "ai_feedback", "strengths", "improvements")
        }),
    ]


@admin.register(InterviewResponse)
class InterviewResponseAdmin(admin.ModelAdmin):
    """Admin configuration for InterviewResponse."""
    
    list_display = [
        "session",
        "order",
        "question_preview",
        "ai_score",
        "time_taken_seconds",
        "is_flagged",
    ]
    list_filter = ["is_flagged", "session__session_type"]
    search_fields = ["session__title", "question__question"]
    ordering = ["session", "order"]
    
    def question_preview(self, obj):
        return obj.question.question[:50] + "..."
    question_preview.short_description = "Question"


@admin.register(InterviewTip)
class InterviewTipAdmin(admin.ModelAdmin):
    """Admin configuration for InterviewTip."""
    
    list_display = ["title", "category", "order", "is_featured"]
    list_filter = ["category", "is_featured"]
    search_fields = ["title", "content"]
    filter_horizontal = ["career_paths"]
    ordering = ["category", "order"]


@admin.register(UserInterviewPreference)
class UserInterviewPreferenceAdmin(admin.ModelAdmin):
    """Admin configuration for preferences."""
    
    list_display = [
        "user",
        "preferred_difficulty",
        "default_num_questions",
        "default_duration_minutes",
    ]
    search_fields = ["user__email"]


@admin.register(InterviewSchedule)
class InterviewScheduleAdmin(admin.ModelAdmin):
    """Admin configuration for InterviewSchedule."""
    
    list_display = [
        "user",
        "application",
        "interview_type",
        "status",
        "round_number",
        "scheduled_at",
    ]
    list_filter = ["interview_type", "status"]
    search_fields = ["user__email", "application__job__title"]
    ordering = ["-scheduled_at"]
    
    fieldsets = [
        (None, {
            "fields": ("user", "application", "interview_type", "status")
        }),
        ("Schedule", {
            "fields": (
                "round_number", "scheduled_at",
                "duration_minutes", "timezone"
            )
        }),
        ("Location", {
            "fields": ("location", "meeting_link")
        }),
        ("Interviewer", {
            "fields": ("interviewer_name", "interviewer_title")
        }),
        ("Preparation", {
            "fields": ("preparation_notes", "questions_to_ask")
        }),
        ("Feedback", {
            "fields": ("feedback", "self_assessment")
        }),
    ]
