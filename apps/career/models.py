"""
Career Models
=============
Models for career predictions, market trends, and career paths.
"""

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel, SoftDeleteModel, TimeStampedModel


class CareerPath(BaseModel):
    """
    Model representing a career path or role.
    
    This is a reference table of career paths that users can explore.
    """
    
    class CareerLevel(models.TextChoices):
        ENTRY = "entry", _("Entry Level")
        JUNIOR = "junior", _("Junior")
        MID = "mid", _("Mid Level")
        SENIOR = "senior", _("Senior")
        LEAD = "lead", _("Lead")
        MANAGER = "manager", _("Manager")
        DIRECTOR = "director", _("Director")
        VP = "vp", _("VP")
        C_LEVEL = "c_level", _("C-Level")
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    title = models.CharField(
        max_length=255,
        help_text=_("Career/job title")
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text=_("URL-friendly slug")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of this career path")
    )
    career_level = models.CharField(
        max_length=20,
        choices=CareerLevel.choices,
        default=CareerLevel.MID,
        help_text=_("Career level")
    )
    industry = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Primary industry")
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Job category")
    )
    
    # Required qualifications
    required_skills = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Required skills for this career")
    )
    preferred_skills = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Preferred/nice-to-have skills")
    )
    required_education = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Required education levels")
    )
    required_experience_years = models.PositiveIntegerField(
        default=0,
        help_text=_("Minimum years of experience")
    )
    certifications = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Recommended certifications")
    )
    
    # Career progression
    parent_path = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_paths",
        help_text=_("Previous career path leading to this")
    )
    next_paths = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="previous_paths",
        help_text=_("Potential next career paths")
    )
    
    # Salary information
    salary_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Minimum salary (USD)")
    )
    salary_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Maximum salary (USD)")
    )
    salary_median = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Median salary (USD)")
    )
    
    # Market data
    demand_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text=_("Market demand score (0-1)")
    )
    growth_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Expected growth rate %")
    )
    job_openings = models.PositiveIntegerField(
        default=0,
        help_text=_("Current number of job openings")
    )
    
    # AI-generated content
    day_in_life = models.TextField(
        blank=True,
        help_text=_("Description of a typical day")
    )
    challenges = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Common challenges in this role")
    )
    rewards = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Rewards and benefits of this career")
    )
    
    # Metadata
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether career path is active")
    )
    popularity_score = models.PositiveIntegerField(
        default=0,
        help_text=_("Popularity based on user interest")
    )
    last_updated_market_data = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When market data was last updated")
    )

    class Meta:
        db_table = "career_paths"
        verbose_name = _("Career Path")
        verbose_name_plural = _("Career Paths")
        ordering = ["title"]
        indexes = [
            models.Index(fields=["industry", "career_level"]),
            models.Index(fields=["-demand_score"]),
            models.Index(fields=["-popularity_score"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_career_level_display()})"


class CareerPrediction(TimeStampedModel, SoftDeleteModel):
    """
    Model for storing AI career predictions for users.
    
    Stores personalized career recommendations based on user profile.
    """
    
    class PredictionStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="career_predictions"
    )
    
    # Prediction status
    status = models.CharField(
        max_length=20,
        choices=PredictionStatus.choices,
        default=PredictionStatus.PENDING,
        help_text=_("Current prediction status")
    )
    error_message = models.TextField(
        blank=True,
        help_text=_("Error message if prediction failed")
    )
    
    # Input data snapshot
    input_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Snapshot of user data used for prediction")
    )
    
    # Prediction results
    recommended_careers = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of recommended career paths with scores")
    )
    current_career_assessment = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Assessment of current career position")
    )
    skill_gaps = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Identified skill gaps")
    )
    recommended_skills = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Skills to develop")
    )
    recommended_courses = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Recommended learning resources")
    )
    career_timeline = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Suggested career timeline")
    )
    salary_projection = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Salary projections over time")
    )
    
    # AI metadata
    model_used = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("AI model used for prediction")
    )
    model_version = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Version of the AI model")
    )
    confidence_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text=_("Overall confidence score")
    )
    processing_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Processing time in milliseconds")
    )
    tokens_used = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Number of tokens used")
    )
    
    # User feedback
    user_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("User rating (1-5)")
    )
    user_feedback = models.TextField(
        blank=True,
        help_text=_("User feedback on predictions")
    )

    # User acceptance decision
    is_accepted = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        help_text=_("True = accepted, False = rejected, None = no decision yet")
    )
    accepted_career_title = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Career title the user accepted from this prediction")
    )

    class Meta:
        db_table = "career_predictions"
        verbose_name = _("Career Prediction")
        verbose_name_plural = _("Career Predictions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Career prediction for {self.user.email} ({self.status})"


class CareerMarketTrend(BaseModel):
    """
    Model for storing market trend data.
    
    Tracks industry trends, emerging skills, and job market data.
    """
    
    class TrendType(models.TextChoices):
        SKILL = "skill", _("Skill Trend")
        INDUSTRY = "industry", _("Industry Trend")
        ROLE = "role", _("Role/Title Trend")
        TECHNOLOGY = "technology", _("Technology Trend")
        SALARY = "salary", _("Salary Trend")
    
    class TrendDirection(models.TextChoices):
        UP = "up", _("Trending Up")
        DOWN = "down", _("Trending Down")
        STABLE = "stable", _("Stable")
        EMERGING = "emerging", _("Emerging")
        DECLINING = "declining", _("Declining")
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Name of the trend item")
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text=_("URL-friendly slug")
    )
    trend_type = models.CharField(
        max_length=20,
        choices=TrendType.choices,
        help_text=_("Type of trend")
    )
    direction = models.CharField(
        max_length=20,
        choices=TrendDirection.choices,
        default=TrendDirection.STABLE,
        help_text=_("Trend direction")
    )
    
    # Trend data
    current_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Current value (context-dependent)")
    )
    previous_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Previous period value")
    )
    change_percentage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Percentage change")
    )
    historical_data = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Historical trend data points")
    )
    
    # Additional context
    industry = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Related industry")
    )
    region = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Geographic region")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of the trend")
    )
    impact_analysis = models.TextField(
        blank=True,
        help_text=_("Analysis of trend impact")
    )
    related_skills = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Related skills")
    )
    related_careers = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Related career paths")
    )
    
    # Metadata
    data_source = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Source of trend data")
    )
    data_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date of the data")
    )
    is_featured = models.BooleanField(
        default=False,
        help_text=_("Whether to feature this trend")
    )
    view_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of views")
    )

    class Meta:
        db_table = "career_market_trends"
        verbose_name = _("Career Market Trend")
        verbose_name_plural = _("Career Market Trends")
        ordering = ["-data_date", "-created_at"]
        indexes = [
            models.Index(fields=["trend_type", "-data_date"]),
            models.Index(fields=["direction", "-change_percentage"]),
            models.Index(fields=["industry"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_trend_type_display()})"


class UserCareerGoal(TimeStampedModel, SoftDeleteModel):
    """
    Model for storing user career goals.
    """
    
    class GoalStatus(models.TextChoices):
        ACTIVE = "active", _("Active")
        IN_PROGRESS = "in_progress", _("In Progress")
        ACHIEVED = "achieved", _("Achieved")
        PAUSED = "paused", _("Paused")
        ABANDONED = "abandoned", _("Abandoned")
    
    class GoalPriority(models.IntegerChoices):
        LOW = 1, _("Low")
        MEDIUM = 2, _("Medium")
        HIGH = 3, _("High")
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="career_goals"
    )
    target_career = models.ForeignKey(
        CareerPath,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_goals",
        help_text=_("Target career path")
    )
    
    # Goal details
    title = models.CharField(
        max_length=255,
        help_text=_("Goal title")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Goal description")
    )
    status = models.CharField(
        max_length=20,
        choices=GoalStatus.choices,
        default=GoalStatus.ACTIVE,
        help_text=_("Current status")
    )
    priority = models.PositiveSmallIntegerField(
        choices=GoalPriority.choices,
        default=GoalPriority.MEDIUM,
        help_text=_("Priority level")
    )
    
    # Timeline
    target_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Target completion date")
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When goal was started")
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When goal was achieved")
    )
    
    # Progress tracking
    progress_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(100)],
        help_text=_("Progress percentage (0-100)")
    )
    milestones = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Goal milestones")
    )
    
    # AI-generated action plan
    action_plan = models.JSONField(
        default=list,
        blank=True,
        help_text=_("AI-generated action plan")
    )
    recommended_resources = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Recommended learning resources")
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes")
    )

    class Meta:
        db_table = "user_career_goals"
        verbose_name = _("User Career Goal")
        verbose_name_plural = _("User Career Goals")
        ordering = ["-priority", "-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["target_date"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class UserCareerBookmark(BaseModel):
    """
    Model for bookmarking career paths.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="career_bookmarks"
    )
    career_path = models.ForeignKey(
        CareerPath,
        on_delete=models.CASCADE,
        related_name="bookmarks"
    )
    notes = models.TextField(
        blank=True,
        help_text=_("User notes")
    )

    class Meta:
        db_table = "user_career_bookmarks"
        verbose_name = _("User Career Bookmark")
        verbose_name_plural = _("User Career Bookmarks")
        unique_together = ["user", "career_path"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} bookmarked {self.career_path.title}"


class CareerComparison(TimeStampedModel, SoftDeleteModel):
    """
    Model for comparing career paths.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="career_comparisons"
    )
    careers = models.ManyToManyField(
        CareerPath,
        related_name="comparisons"
    )
    
    # Comparison results
    comparison_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Detailed comparison data")
    )
    recommendation = models.TextField(
        blank=True,
        help_text=_("AI recommendation based on comparison")
    )
    recommended_career = models.ForeignKey(
        CareerPath,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recommended_in_comparisons",
        help_text=_("Recommended career from comparison")
    )
    
    # AI metadata
    model_used = models.CharField(
        max_length=100,
        blank=True
    )

    class Meta:
        db_table = "career_comparisons"
        verbose_name = _("Career Comparison")
        verbose_name_plural = _("Career Comparisons")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Career comparison for {self.user.email}"
