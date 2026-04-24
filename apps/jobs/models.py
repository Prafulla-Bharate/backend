"""
Jobs Models
===========
Database models for job postings, applications, and tracking.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class Company(TimeStampedModel):
    """Company model for job listings."""
    
    class CompanySize(models.TextChoices):
        STARTUP = "startup", "1-10 employees"
        SMALL = "small", "11-50 employees"
        MEDIUM = "medium", "51-200 employees"
        LARGE = "large", "201-1000 employees"
        ENTERPRISE = "enterprise", "1000+ employees"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    
    # Basic info
    website = models.URLField(blank=True)
    logo = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    size = models.CharField(
        max_length=20,
        choices=CompanySize.choices,
        blank=True
    )
    founded_year = models.PositiveIntegerField(null=True, blank=True)
    
    # Location
    headquarters = models.CharField(max_length=200, blank=True)
    locations = models.JSONField(default=list, blank=True)
    
    # Social
    linkedin_url = models.URLField(blank=True)
    glassdoor_url = models.URLField(blank=True)
    
    # Ratings
    glassdoor_rating = models.DecimalField(
        max_digits=2, decimal_places=1, null=True, blank=True
    )
    
    # Status
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Companies"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["industry"]),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class JobPosting(TimeStampedModel):
    """Job posting model."""
    
    class JobType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"
        FREELANCE = "freelance", "Freelance"
    
    class ExperienceLevel(models.TextChoices):
        ENTRY = "entry", "Entry Level"
        JUNIOR = "junior", "Junior (1-2 years)"
        MID = "mid", "Mid-Level (3-5 years)"
        SENIOR = "senior", "Senior (5-10 years)"
        LEAD = "lead", "Lead/Principal (10+ years)"
        EXECUTIVE = "executive", "Executive"
    
    class WorkArrangement(models.TextChoices):
        ONSITE = "onsite", "On-site"
        REMOTE = "remote", "Remote"
        HYBRID = "hybrid", "Hybrid"
    
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CLOSED = "closed", "Closed"
        FILLED = "filled", "Filled"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic info
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True)
    description = models.TextField()
    
    # Company
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="job_postings"
    )
    
    # Type and level
    job_type = models.CharField(
        max_length=20,
        choices=JobType.choices,
        default=JobType.FULL_TIME
    )
    experience_level = models.CharField(
        max_length=20,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.MID
    )
    work_arrangement = models.CharField(
        max_length=20,
        choices=WorkArrangement.choices,
        default=WorkArrangement.ONSITE
    )
    
    # Location
    location = models.CharField(max_length=200)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Salary
    salary_min = models.PositiveIntegerField(null=True, blank=True)
    salary_max = models.PositiveIntegerField(null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default="USD")
    salary_period = models.CharField(max_length=20, default="yearly")
    show_salary = models.BooleanField(default=True)
    
    # Requirements
    required_skills = models.JSONField(default=list, blank=True)
    preferred_skills = models.JSONField(default=list, blank=True)
    required_education = models.CharField(max_length=100, blank=True)
    required_experience_years = models.PositiveIntegerField(default=0)
    
    # Benefits
    benefits = models.JSONField(default=list, blank=True)
    
    # Application
    apply_url = models.URLField(blank=True)
    apply_email = models.EmailField(blank=True)
    
    # Related career
    career_path = models.ForeignKey(
        "career.CareerPath",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_postings"
    )
    
    # Source
    source = models.CharField(max_length=100, default="internal")
    external_id = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Statistics
    views_count = models.PositiveIntegerField(default=0)
    applications_count = models.PositiveIntegerField(default=0)
    
    # Matching
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["-is_featured", "-posted_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status", "posted_at"]),
            models.Index(fields=["job_type"]),
            models.Index(fields=["experience_level"]),
            models.Index(fields=["work_arrangement"]),
            models.Index(fields=["location"]),
        ]
    
    def __str__(self):
        return f"{self.title} at {self.company.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.title}-{self.company.name}")
            self.slug = f"{base_slug}-{str(self.id)[:8]}"
        super().save(*args, **kwargs)


class SavedJob(TimeStampedModel):
    """User's saved/bookmarked job."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_jobs"
    )
    job = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name="saves"
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ["user", "job"]
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.user.email} saved {self.job.title}"


class JobApplication(TimeStampedModel):
    """User's job application."""
    
    class ApplicationStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        VIEWED = "viewed", "Viewed"
        SCREENING = "screening", "Screening"
        INTERVIEWING = "interviewing", "Interviewing"
        OFFER = "offer", "Offer Received"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_applications"
    )
    # For internally tracked job postings (optional — may be null for external apps)
    job = models.ForeignKey(
        JobPosting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications"
    )

    # For externally tracked applications (LinkedIn, Indeed, Glassdoor, etc.)
    is_external = models.BooleanField(default=False)
    external_company = models.CharField(max_length=255, blank=True)
    external_position = models.CharField(max_length=255, blank=True)
    external_url = models.URLField(blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.SUBMITTED
    )
    
    # Cover letter
    cover_letter = models.TextField(blank=True)
    cover_letter_ai_generated = models.BooleanField(default=False)
    
    # Additional info
    answers = models.JSONField(default=dict, blank=True)  # Custom questions
    
    # AI matching
    match_score = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )
    match_details = models.JSONField(default=dict, blank=True)
    
    # Timeline
    submitted_at = models.DateTimeField(null=True, blank=True)
    last_updated_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Soft delete
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["job", "status"]),
        ]
    
    def __str__(self):
        if self.is_external:
            return f"{self.user.email} applied to {self.external_position} at {self.external_company}"
        return f"{self.user.email} applied to {self.job.title if self.job else 'unknown'}"


class ApplicationActivity(TimeStampedModel):
    """Activity log for job applications."""
    
    class ActivityType(models.TextChoices):
        STATUS_CHANGE = "status_change", "Status Change"
        NOTE_ADDED = "note_added", "Note Added"
        RESUME_UPDATED = "resume_updated", "Resume Updated"
        COVER_LETTER_UPDATED = "cover_letter_updated", "Cover Letter Updated"
        INTERVIEW_SCHEDULED = "interview_scheduled", "Interview Scheduled"
        OFFER_RECEIVED = "offer_received", "Offer Received"
        FOLLOW_UP = "follow_up", "Follow Up"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="activities"
    )
    
    activity_type = models.CharField(
        max_length=30,
        choices=ActivityType.choices
    )
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name_plural = "Application activities"
        ordering = ["-created_at"]
    
    def __str__(self):
        job_title = self.application.job.title if self.application.job else "external application"
        return f"{job_title} - {self.activity_type}"


class JobAlert(TimeStampedModel):
    """Job alert subscription."""
    
    class Frequency(models.TextChoices):
        INSTANT = "instant", "Instant"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_alerts"
    )
    
    # Alert name
    name = models.CharField(max_length=100)
    
    # Filters
    keywords = models.JSONField(default=list, blank=True)
    job_types = models.JSONField(default=list, blank=True)
    experience_levels = models.JSONField(default=list, blank=True)
    locations = models.JSONField(default=list, blank=True)
    work_arrangements = models.JSONField(default=list, blank=True)
    salary_min = models.PositiveIntegerField(null=True, blank=True)
    companies = models.JSONField(default=list, blank=True)
    skills = models.JSONField(default=list, blank=True)
    
    # Frequency
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.DAILY
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.user.email} - {self.name}"


class JobRecommendation(TimeStampedModel):
    """AI-generated job recommendation."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_recommendations"
    )
    job = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name="recommendations"
    )
    
    # Recommendation metadata
    match_score = models.DecimalField(
        max_digits=4, decimal_places=2, default=0
    )
    reasons = models.JSONField(default=list, blank=True)
    skill_matches = models.JSONField(default=list, blank=True)
    skill_gaps = models.JSONField(default=list, blank=True)
    
    # Status
    is_viewed = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ["user", "job"]
        ordering = ["-match_score", "-created_at"]
    
    def __str__(self):
        return f"Rec for {self.user.email}: {self.job.title}"
