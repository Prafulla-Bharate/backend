"""
Interview Serializers
=====================
Serializers for interview-related data.
"""

from rest_framework import serializers

from apps.interview.models import (
    InterviewQuestion,
    InterviewSession,
    InterviewResponse,
    InterviewTip,
    InterviewSchedule,
)


class InterviewQuestionMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer used in response nesting — includes STAR hints for live practice."""

    class Meta:
        model = InterviewQuestion
        fields = [
            "id", "question", "question_type", "difficulty", "category",
            "situation_hint", "task_hint", "action_hint", "result_hint",
        ]


# ============================================================================
# Response Serializers
# ============================================================================

class InterviewResponseSerializer(serializers.ModelSerializer):
    """Full serializer for responses."""
    
    question = InterviewQuestionMinimalSerializer(read_only=True)
    ai_analysis = serializers.SerializerMethodField()

    class Meta:
        model = InterviewResponse
        fields = [
            "id", "question", "order", "response_text",
            "response_audio_url", "response_video_url",
            "started_at", "completed_at", "time_taken_seconds",
            "ai_score", "ai_feedback", "ai_analysis",
            "content_score", "structure_score", "clarity_score",
            "relevance_score", "self_rating", "self_notes",
            "is_flagged"
        ]

    def get_ai_analysis(self, obj):
        # Always include best_answer and rubric if present on question
        analysis = obj.ai_analysis or {}
        if hasattr(obj.question, "sample_answer") and obj.question.sample_answer:
            analysis["best_answer"] = obj.question.sample_answer
        if hasattr(obj.question, "answer_tips") and obj.question.answer_tips:
            analysis["rubric"] = obj.question.answer_tips
        return analysis


class SubmitResponseSerializer(serializers.Serializer):
    """Serializer for submitting a response."""
    
    response_text = serializers.CharField(required=False, allow_blank=True)
    response_audio_url = serializers.URLField(required=False)
    response_video_url = serializers.URLField(required=False)
    response_audio_file = serializers.FileField(required=False)
    response_video_file = serializers.FileField(required=False)
    time_taken_seconds = serializers.IntegerField(min_value=0, default=0)
    self_rating = serializers.IntegerField(
        min_value=1, max_value=5, required=False
    )
    self_notes = serializers.CharField(required=False, allow_blank=True)


# ============================================================================
# Session Serializers
# ============================================================================

class InterviewSessionSerializer(serializers.ModelSerializer):
    """Full serializer for sessions."""
    
    responses = InterviewResponseSerializer(many=True, read_only=True)
    questions_answered = serializers.SerializerMethodField()
    
    class Meta:
        model = InterviewSession
        fields = [
            "id", "title", "session_type", "status",
            "target_career", "target_company",
            "question_types", "difficulty_preference", "num_questions",
            "scheduled_at", "started_at", "completed_at", "duration_minutes",
            "overall_score", "ai_feedback", "strengths", "improvements",
            "responses", "questions_answered", "created_at"
        ]
    
    def get_questions_answered(self, obj):
        return obj.responses.filter(completed_at__isnull=False).count()


class InterviewSessionListSerializer(serializers.ModelSerializer):
    """List serializer for sessions."""
    
    questions_answered = serializers.SerializerMethodField()
    
    class Meta:
        model = InterviewSession
        fields = [
            "id", "title", "session_type", "status",
            "target_company", "num_questions", "questions_answered",
            "overall_score", "scheduled_at", "completed_at"
        ]
    
    def get_questions_answered(self, obj):
        return obj.responses.filter(completed_at__isnull=False).count()


class CreateSessionSerializer(serializers.Serializer):
    """Serializer for creating a session."""
    
    title = serializers.CharField(max_length=200)
    session_type = serializers.ChoiceField(
        choices=InterviewSession.SessionType.choices,
        default=InterviewSession.SessionType.PRACTICE
    )
    job_application_id = serializers.UUIDField(required=False)
    target_career_id = serializers.UUIDField(required=False)
    target_company = serializers.CharField(required=False, allow_blank=True)
    question_types = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    difficulty_preference = serializers.ChoiceField(
        choices=InterviewQuestion.DifficultyLevel.choices,
        default=InterviewQuestion.DifficultyLevel.MEDIUM
    )
    num_questions = serializers.IntegerField(min_value=1, max_value=20, default=5)
    duration_minutes = serializers.IntegerField(min_value=5, max_value=180, default=30)
    technical_mcq_count = serializers.IntegerField(min_value=0, max_value=20, required=False)
    coding_count = serializers.IntegerField(min_value=0, max_value=20, required=False)
    coding_language = serializers.CharField(required=False, allow_blank=True)
    coding_mode = serializers.ChoiceField(choices=["logic", "function", "leetcode"], required=False)
    real_section = serializers.ChoiceField(
        choices=["technical_round", "technical_interview", "hr_round"],
        required=False,
    )
    scheduled_at = serializers.DateTimeField(required=False)


# ============================================================================
# Tip Serializers
# ============================================================================

class InterviewTipSerializer(serializers.ModelSerializer):
    """Serializer for interview tips."""
    
    class Meta:
        model = InterviewTip
        fields = [
            "id", "title", "content", "category",
            "question_types", "is_featured", "order"
        ]


# ============================================================================
# Schedule Serializers
# ============================================================================


class InterviewScheduleListSerializer(serializers.ModelSerializer):
    """List serializer for schedules."""

    job_title = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()

    def get_job_title(self, obj) -> str:
        try:
            return obj.application.job.title if obj.application and obj.application.job else ""
        except Exception:
            return ""

    def get_company_name(self, obj) -> str:
        try:
            return (
                obj.application.job.company.name
                if obj.application and obj.application.job and obj.application.job.company
                else ""
            )
        except Exception:
            return ""
    
    class Meta:
        model = InterviewSchedule
        fields = [
            "id", "job_title", "company_name", "interview_type",
            "status", "round_number", "scheduled_at"
        ]


class PracticeStatsSerializer(serializers.Serializer):
    """Serializer for practice statistics."""
    
    total_sessions = serializers.IntegerField()
    total_questions_answered = serializers.IntegerField()
    average_score = serializers.FloatField()
    total_practice_time_minutes = serializers.IntegerField()
    by_question_type = serializers.DictField()
    improvement_areas = serializers.ListField(child=serializers.CharField())
