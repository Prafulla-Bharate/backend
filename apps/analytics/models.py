"""
Analytics Models
================
Database models for analytics and insights.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserActivity(models.Model):
    """Tracks user activity events."""
    
    class ActivityType(models.TextChoices):
        LOGIN = "login", _("Login")
        LOGOUT = "logout", _("Logout")
        PAGE_VIEW = "page_view", _("Page View")
        RESUME_VIEW = "resume_view", _("Resume View")
        RESUME_DOWNLOAD = "resume_download", _("Resume Download")
        JOB_VIEW = "job_view", _("Job View")
        JOB_APPLY = "job_apply", _("Job Application")
        JOB_SAVE = "job_save", _("Job Saved")
        LEARNING_START = "learning_start", _("Learning Started")
        LEARNING_COMPLETE = "learning_complete", _("Learning Completed")
        INTERVIEW_START = "interview_start", _("Interview Started")
        INTERVIEW_COMPLETE = "interview_complete", _("Interview Completed")
        PROFILE_UPDATE = "profile_update", _("Profile Update")
        SEARCH = "search", _("Search")
        API_CALL = "api_call", _("API Call")
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activities"
    )
    activity_type = models.CharField(
        max_length=30,
        choices=ActivityType.choices
    )
    description = models.TextField(blank=True)
    
    # Context
    resource_type = models.CharField(max_length=50, blank=True)
    resource_id = models.UUIDField(null=True, blank=True)
    resource_name = models.CharField(max_length=255, blank=True)
    
    # Request details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(blank=True)
    path = models.CharField(max_length=500, blank=True)
    
    # Device info
    device_type = models.CharField(max_length=20, blank=True)
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)
    
    # Session
    session_id = models.CharField(max_length=100, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "User Activity"
        verbose_name_plural = "User Activities"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "activity_type"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["activity_type", "created_at"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.activity_type} - {self.created_at}"


class UserMetrics(models.Model):
    """Aggregated daily metrics for users."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="metrics"
    )
    date = models.DateField()
    
    # Activity counts
    page_views = models.PositiveIntegerField(default=0)
    sessions = models.PositiveIntegerField(default=0)
    time_spent_minutes = models.PositiveIntegerField(default=0)
    
    # Job metrics
    jobs_viewed = models.PositiveIntegerField(default=0)
    jobs_saved = models.PositiveIntegerField(default=0)
    jobs_applied = models.PositiveIntegerField(default=0)
    
    # Learning metrics
    learning_time_minutes = models.PositiveIntegerField(default=0)
    resources_completed = models.PositiveIntegerField(default=0)
    checkpoints_passed = models.PositiveIntegerField(default=0)
    
    # Interview metrics
    practice_sessions = models.PositiveIntegerField(default=0)
    questions_answered = models.PositiveIntegerField(default=0)
    average_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    
    # Resume metrics
    resume_views = models.PositiveIntegerField(default=0)
    resume_downloads = models.PositiveIntegerField(default=0)
    
    # Profile
    profile_completeness = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Metrics"
        verbose_name_plural = "User Metrics"
        ordering = ["-date"]
        unique_together = ["user", "date"]
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["date"]),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.date}"


class CareerAnalytics(models.Model):
    """Career path analytics and progress tracking."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="career_analytics"
    )
    career_path = models.ForeignKey(
        "career.CareerPath",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics"
    )
    
    # Progress
    overall_progress = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    skills_progress = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    experience_progress = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    education_progress = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    
    # Skills analysis
    total_skills = models.PositiveIntegerField(default=0)
    acquired_skills = models.PositiveIntegerField(default=0)
    in_progress_skills = models.PositiveIntegerField(default=0)
    missing_skills = models.JSONField(default=list, blank=True)
    strong_skills = models.JSONField(default=list, blank=True)
    
    # Market position
    market_demand_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    salary_percentile = models.PositiveIntegerField(
        null=True, blank=True
    )
    competition_level = models.CharField(max_length=20, blank=True)
    
    # Recommendations
    next_steps = models.JSONField(default=list, blank=True)
    recommended_resources = models.JSONField(default=list, blank=True)
    
    # Timeline
    estimated_completion_date = models.DateField(null=True, blank=True)
    days_to_goal = models.PositiveIntegerField(null=True, blank=True)
    
    # History
    progress_history = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Career Analytics"
        verbose_name_plural = "Career Analytics"
        ordering = ["-updated_at"]
        unique_together = ["user", "career_path"]
    
    def __str__(self):
        return f"{self.user.email} - Career Analytics"


class LearningAnalytics(models.Model):
    """Learning progress analytics."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="learning_analytics"
    )
    
    # Overall stats
    total_learning_time_hours = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    total_resources_completed = models.PositiveIntegerField(default=0)
    total_checkpoints_passed = models.PositiveIntegerField(default=0)
    total_paths_started = models.PositiveIntegerField(default=0)
    total_paths_completed = models.PositiveIntegerField(default=0)
    
    # Current streak
    current_streak_days = models.PositiveIntegerField(default=0)
    longest_streak_days = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    
    # Performance
    average_checkpoint_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    completion_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    
    # Time patterns
    preferred_learning_time = models.CharField(max_length=20, blank=True)
    preferred_day_of_week = models.CharField(max_length=15, blank=True)
    average_session_length_minutes = models.PositiveIntegerField(default=0)
    
    # Categories breakdown
    category_progress = models.JSONField(default=dict, blank=True)
    
    # Skills gained
    skills_acquired = models.JSONField(default=list, blank=True)
    
    # Monthly history
    monthly_stats = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Learning Analytics"
        verbose_name_plural = "Learning Analytics"
    
    def __str__(self):
        return f"{self.user.email} - Learning Analytics"


class JobSearchAnalytics(models.Model):
    """Job search activity analytics."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_search_analytics"
    )
    
    # Application stats
    total_applications = models.PositiveIntegerField(default=0)
    applications_this_month = models.PositiveIntegerField(default=0)
    applications_this_week = models.PositiveIntegerField(default=0)
    
    # Status breakdown
    pending_applications = models.PositiveIntegerField(default=0)
    reviewed_applications = models.PositiveIntegerField(default=0)
    interviews_scheduled = models.PositiveIntegerField(default=0)
    offers_received = models.PositiveIntegerField(default=0)
    rejections = models.PositiveIntegerField(default=0)
    
    # Rates
    response_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    interview_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    offer_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    
    # Search behavior
    total_jobs_viewed = models.PositiveIntegerField(default=0)
    total_jobs_saved = models.PositiveIntegerField(default=0)
    average_time_per_application_days = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    
    # Preferences analysis
    most_searched_keywords = models.JSONField(default=list, blank=True)
    preferred_locations = models.JSONField(default=list, blank=True)
    preferred_job_types = models.JSONField(default=list, blank=True)
    salary_range_searched = models.JSONField(default=dict, blank=True)
    
    # Company insights
    companies_applied = models.JSONField(default=list, blank=True)
    companies_responded = models.JSONField(default=list, blank=True)
    
    # Timeline
    average_response_time_days = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    average_time_to_interview_days = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    
    # Weekly history
    weekly_stats = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Job Search Analytics"
        verbose_name_plural = "Job Search Analytics"
    
    def __str__(self):
        return f"{self.user.email} - Job Search Analytics"


class InterviewAnalytics(models.Model):
    """Interview practice analytics."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_analytics"
    )
    
    # Practice stats
    total_practice_sessions = models.PositiveIntegerField(default=0)
    total_questions_answered = models.PositiveIntegerField(default=0)
    total_practice_time_hours = models.DecimalField(
        max_digits=6, decimal_places=2, default=0
    )
    
    # Performance
    average_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    best_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    improvement_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    
    # By type
    scores_by_type = models.JSONField(default=dict, blank=True)
    questions_by_type = models.JSONField(default=dict, blank=True)
    
    # By difficulty
    scores_by_difficulty = models.JSONField(default=dict, blank=True)
    
    # Strengths and weaknesses
    strongest_areas = models.JSONField(default=list, blank=True)
    weakest_areas = models.JSONField(default=list, blank=True)
    
    # Real interviews
    total_real_interviews = models.PositiveIntegerField(default=0)
    real_interview_success_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    
    # Progress history
    weekly_scores = models.JSONField(default=list, blank=True)
    monthly_progress = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Interview Analytics"
        verbose_name_plural = "Interview Analytics"
    
    def __str__(self):
        return f"{self.user.email} - Interview Analytics"


class PlatformMetrics(models.Model):
    """Platform-wide metrics for admin dashboard."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(unique=True)
    
    # User metrics
    total_users = models.PositiveIntegerField(default=0)
    new_users = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    returning_users = models.PositiveIntegerField(default=0)
    
    # Engagement
    total_sessions = models.PositiveIntegerField(default=0)
    average_session_duration_minutes = models.PositiveIntegerField(default=0)
    bounce_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    
    # Jobs
    jobs_posted = models.PositiveIntegerField(default=0)
    applications_submitted = models.PositiveIntegerField(default=0)
    jobs_filled = models.PositiveIntegerField(default=0)
    
    # Learning
    resources_accessed = models.PositiveIntegerField(default=0)
    learning_hours = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    completions = models.PositiveIntegerField(default=0)
    
    # Interview
    practice_sessions_completed = models.PositiveIntegerField(default=0)
    questions_answered = models.PositiveIntegerField(default=0)
    
    # Resume
    resumes_created = models.PositiveIntegerField(default=0)
    resumes_downloaded = models.PositiveIntegerField(default=0)
    
    # Revenue (if applicable)
    revenue = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Platform Metrics"
        verbose_name_plural = "Platform Metrics"
        ordering = ["-date"]
    
    def __str__(self):
        return f"Platform Metrics - {self.date}"


class AnalyticsEvent(models.Model):
    """Raw analytics events for detailed tracking."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_name = models.CharField(max_length=100)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics_events"
    )
    
    # Event properties
    properties = models.JSONField(default=dict, blank=True)
    
    # Context
    session_id = models.CharField(max_length=100, blank=True)
    page_url = models.URLField(blank=True)
    referrer = models.URLField(blank=True)
    
    # Device
    device_id = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=20, blank=True)
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)
    screen_resolution = models.CharField(max_length=20, blank=True)
    
    # Location
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Timing
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Analytics Event"
        verbose_name_plural = "Analytics Events"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["event_name", "timestamp"]),
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["session_id"]),
        ]
    
    def __str__(self):
        return f"{self.event_name} - {self.timestamp}"
