"""
Interview Models
================
Database models for interview preparation and practice.
"""

import uuid

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class InterviewQuestion(TimeStampedModel):
    """Interview question bank."""
    
    class QuestionType(models.TextChoices):
        BEHAVIORAL = "behavioral", "Behavioral"
        TECHNICAL = "technical", "Technical"
        SITUATIONAL = "situational", "Situational"
        CASE_STUDY = "case_study", "Case Study"
        CODING = "coding", "Coding"
        SYSTEM_DESIGN = "system_design", "System Design"
        BRAINTEASER = "brainteaser", "Brainteaser"
    
    class DifficultyLevel(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
        default=QuestionType.BEHAVIORAL
    )
    difficulty = models.CharField(
        max_length=10,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.MEDIUM
    )
    
    # Context
    category = models.CharField(max_length=100, blank=True)
    tags = models.JSONField(default=list, blank=True)
    companies = models.JSONField(default=list, blank=True)  # Known to be asked at
    
    # For technical/coding questions
    expected_topics = models.JSONField(default=list, blank=True)
    sample_answer = models.TextField(blank=True)
    answer_tips = models.JSONField(default=list, blank=True)
    
    # STAR method hints (for behavioral)
    situation_hint = models.TextField(blank=True)
    task_hint = models.TextField(blank=True)
    action_hint = models.TextField(blank=True)
    result_hint = models.TextField(blank=True)
    
    # Related career
    career_paths = models.ManyToManyField(
        "career.CareerPath",
        related_name="interview_questions",
        blank=True
    )
    
    # Statistics
    times_asked = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["-times_asked", "-created_at"]
        indexes = [
            models.Index(fields=["question_type"]),
            models.Index(fields=["difficulty"]),
            models.Index(fields=["category"]),
        ]
    
    def __str__(self):
        return self.question[:100]


class InterviewSession(TimeStampedModel):
    """Interview practice session."""
    
    class SessionType(models.TextChoices):
        PRACTICE = "practice", "Practice"
        MOCK = "mock", "Mock Interview"
        AI_FEEDBACK = "ai_feedback", "AI Feedback Session"
    
    class SessionStatus(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_sessions"
    )
    
    # Session details
    title = models.CharField(max_length=200)
    session_type = models.CharField(
        max_length=20,
        choices=SessionType.choices,
        default=SessionType.PRACTICE
    )
    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.SCHEDULED
    )
    
    # Related to job application
    job_application = models.ForeignKey(
        "jobs.JobApplication",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_sessions"
    )
    
    # Target career/company
    target_career = models.ForeignKey(
        "career.CareerPath",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    target_company = models.CharField(max_length=200, blank=True)
    
    # Question settings
    question_types = models.JSONField(default=list, blank=True)
    difficulty_preference = models.CharField(
        max_length=10,
        choices=InterviewQuestion.DifficultyLevel.choices,
        default=InterviewQuestion.DifficultyLevel.MEDIUM
    )
    num_questions = models.PositiveIntegerField(default=5)
    
    # Timing
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    
    # Results
    overall_score = models.PositiveIntegerField(null=True, blank=True)
    ai_feedback = models.TextField(blank=True)
    strengths = models.JSONField(default=list, blank=True)
    improvements = models.JSONField(default=list, blank=True)
    
    # Soft delete
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["session_type"]),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.title}"


class InterviewResponse(TimeStampedModel):
    """User's response to an interview question."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        InterviewSession,
        on_delete=models.CASCADE,
        related_name="responses"
    )
    question = models.ForeignKey(
        InterviewQuestion,
        on_delete=models.CASCADE,
        related_name="responses"
    )
    
    # Response
    order = models.PositiveIntegerField(default=0)
    response_text = models.TextField(blank=True)
    response_audio_url = models.URLField(blank=True)
    response_video_url = models.URLField(blank=True)
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    
    # AI Evaluation
    ai_score = models.PositiveIntegerField(null=True, blank=True)
    ai_feedback = models.TextField(blank=True)
    ai_analysis = models.JSONField(default=dict, blank=True)
    
    # Detailed scores
    content_score = models.PositiveIntegerField(null=True, blank=True)
    structure_score = models.PositiveIntegerField(null=True, blank=True)
    clarity_score = models.PositiveIntegerField(null=True, blank=True)
    relevance_score = models.PositiveIntegerField(null=True, blank=True)
    
    # Self evaluation
    self_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    self_notes = models.TextField(blank=True)
    
    # Flagged for review
    is_flagged = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["session", "order"]
        unique_together = ["session", "question"]
    
    def __str__(self):
        return f"{self.session.title} - Q{self.order}"


class InterviewTip(TimeStampedModel):
    """Interview tips and best practices."""
    
    class TipCategory(models.TextChoices):
        PREPARATION = "preparation", "Preparation"
        DURING = "during", "During Interview"
        FOLLOW_UP = "follow_up", "Follow Up"
        BODY_LANGUAGE = "body_language", "Body Language"
        COMMUNICATION = "communication", "Communication"
        TECHNICAL = "technical", "Technical"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=TipCategory.choices,
        default=TipCategory.PREPARATION
    )
    
    # Related
    question_types = models.JSONField(default=list, blank=True)
    career_paths = models.ManyToManyField(
        "career.CareerPath",
        related_name="interview_tips",
        blank=True
    )
    
    # Order
    order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["category", "order"]
    
    def __str__(self):
        return self.title


class UserInterviewPreference(TimeStampedModel):
    """User's interview preferences."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_preferences"
    )
    
    # Preferred settings
    preferred_question_types = models.JSONField(default=list, blank=True)
    preferred_difficulty = models.CharField(
        max_length=10,
        choices=InterviewQuestion.DifficultyLevel.choices,
        default=InterviewQuestion.DifficultyLevel.MEDIUM
    )
    default_duration_minutes = models.PositiveIntegerField(default=30)
    default_num_questions = models.PositiveIntegerField(default=5)
    
    # Focus areas
    focus_skills = models.JSONField(default=list, blank=True)
    weak_areas = models.JSONField(default=list, blank=True)
    
    # Notifications
    reminder_before_minutes = models.PositiveIntegerField(default=30)
    
    class Meta:
        verbose_name_plural = "User interview preferences"
    
    def __str__(self):
        return f"Preferences for {self.user.email}"


class InterviewSchedule(TimeStampedModel):
    """Scheduled real interview."""
    
    class InterviewType(models.TextChoices):
        PHONE = "phone", "Phone Screen"
        VIDEO = "video", "Video Call"
        ONSITE = "onsite", "On-site"
        TECHNICAL = "technical", "Technical Interview"
        BEHAVIORAL = "behavioral", "Behavioral Interview"
        PANEL = "panel", "Panel Interview"
        FINAL = "final", "Final Interview"
    
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        RESCHEDULED = "rescheduled", "Rescheduled"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_schedules"
    )
    
    # Related application
    application = models.ForeignKey(
        "jobs.JobApplication",
        on_delete=models.CASCADE,
        related_name="interview_schedules"
    )
    
    # Details
    interview_type = models.CharField(
        max_length=20,
        choices=InterviewType.choices,
        default=InterviewType.VIDEO
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    round_number = models.PositiveIntegerField(default=1)
    
    # Timing
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    timezone = models.CharField(max_length=50, default="UTC")
    
    # Location/Link
    location = models.CharField(max_length=500, blank=True)
    meeting_link = models.URLField(blank=True)
    
    # Interviewer info
    interviewer_name = models.CharField(max_length=200, blank=True)
    interviewer_title = models.CharField(max_length=200, blank=True)
    
    # Preparation
    preparation_notes = models.TextField(blank=True)
    questions_to_ask = models.JSONField(default=list, blank=True)
    
    # Post-interview
    feedback = models.TextField(blank=True)
    self_assessment = models.PositiveSmallIntegerField(null=True, blank=True)
    
    # Soft delete
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["scheduled_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["scheduled_at"]),
        ]
    
    def __str__(self):
        try:
            job_title = self.application.job.title if self.application and self.application.job else "Interview"
        except Exception:
            job_title = "Interview"
        return f"{job_title} - Round {self.round_number}"
