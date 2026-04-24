"""
Learning Models
===============
Database models for learning paths, resources, and progress tracking.
"""

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class LearningPath(TimeStampedModel):
    """Learning path model."""
    
    class DifficultyLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        EXPERT = "expert", "Expert"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    
    # Classification
    difficulty = models.CharField(
        max_length=20,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.BEGINNER
    )
    category = models.CharField(max_length=100, blank=True)
    tags = models.JSONField(default=list, blank=True)
    
    # Related career paths
    target_careers = models.ManyToManyField(
        "career.CareerPath",
        related_name="learning_paths",
        blank=True
    )
    
    # Skills taught
    skills_covered = models.JSONField(default=list, blank=True)
    prerequisites = models.JSONField(default=list, blank=True)
    
    # Duration
    estimated_hours = models.PositiveIntegerField(default=0)
    
    # Content
    thumbnail = models.URLField(blank=True)
    objectives = models.JSONField(default=list, blank=True)
    
    # AI generation
    is_ai_generated = models.BooleanField(default=False)
    ai_model_used = models.CharField(max_length=100, blank=True)
    # Persist the raw LLM string the instant it arrives so no LLM call is ever lost.
    # Even if phase/resource creation fails, this field lets us replay or debug without re-calling the API.
    raw_llm_response = models.TextField(
        blank=True,
        help_text="Raw JSON string returned by the LLM — saved immediately before any DB processing"
    )
    # Context snapshot used during generation (skill gap, user profile, options)
    skill_gap_analysis = models.JSONField(
        default=dict, blank=True,
        help_text="Skill gap analysis used to construct this path"
    )
    generation_context = models.JSONField(
        default=dict, blank=True,
        help_text="Full user context snapshot captured at generation time"
    )
    
    # Statistics
    enrollments_count = models.PositiveIntegerField(default=0)
    completions_count = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0
    )
    
    # Status
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["-is_featured", "-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["difficulty"]),
            models.Index(fields=["category"]),
            models.Index(fields=["is_published", "is_featured"]),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            # Append 8 hex chars from UUID to guarantee uniqueness across
            # repeated generations for the same user / career goal.
            unique_suffix = str(self.id).replace("-", "")[:8]
            self.slug = f"{base_slug}-{unique_suffix}"
        super().save(*args, **kwargs)


class LearningPhase(TimeStampedModel):
    """Phase/module within a learning path."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_path = models.ForeignKey(
        LearningPath,
        on_delete=models.CASCADE,
        related_name="phases"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    # Duration
    estimated_hours = models.PositiveIntegerField(default=0)
    
    # Skills
    skills_covered = models.JSONField(default=list, blank=True)
    
    # Adaptive learning fields
    # "After this phase you will be able to..." — surfaced in UI
    learning_objectives = models.JSONField(
        default=list, blank=True,
        help_text="What the learner will be able to do after completing this phase"
    )
    # What skills/knowledge must exist before starting this phase
    prerequisite_skills = models.JSONField(
        default=list, blank=True,
        help_text="Skills or knowledge required before starting this phase"
    )
    # Per-phase difficulty so the path can show a progression curve
    difficulty = models.CharField(
        max_length=20,
        choices=LearningPath.DifficultyLevel.choices,
        default=LearningPath.DifficultyLevel.BEGINNER,
        blank=True,
    )

    # ── Rich content fields (populated by LLM at generation time) ────────────
    # End-of-phase big project the learner must build to prove mastery
    capstone_project = models.JSONField(
        default=dict, blank=True,
        help_text="Capstone project details: title, description, deliverables, skills_demonstrated, github_search_query"
    )
    # Certifications recommended after completing this phase
    recommended_certifications = models.JSONField(
        default=list, blank=True,
        help_text="List of certs: name, platform, search_query, is_free, relevance"
    )
    # Specific YouTube search queries relevant to this phase
    youtube_queries = models.JSONField(
        default=list, blank=True,
        help_text="YouTube search queries to fetch relevant tutorial videos for this phase"
    )
    # External tutorial site topics for auto-generated Google links
    external_topics = models.JSONField(
        default=list, blank=True,
        help_text="List of {site, topic} pairs used to build site-specific Google search links"
    )

    # ── Deep-dive content (lazily generated on first phase-detail click) ─────
    # Stores the full Gemini-generated per-phase curriculum so subsequent
    # requests are served from cache without hitting the LLM again.
    deep_dive_content = models.JSONField(
        default=dict, blank=True,
        help_text="Lazily-generated deep-dive curriculum for this phase (topics, projects, interview Q&A, etc.)"
    )
    deep_dive_generated_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When deep_dive_content was last generated — used for cache invalidation"
    )
    # Core topic list (ordered): stored at path-generation time from LLM
    topics_covered = models.JSONField(
        default=list, blank=True,
        help_text="Ordered list of core topics covered in this phase"
    )
    # Interview Q&A for skills in this phase
    interview_questions = models.JSONField(
        default=list, blank=True,
        help_text="List of {question, answer, difficulty} objects for interview prep"
    )
    # Readiness checklist: 'you are ready for the next phase when...'
    readiness_checklist = models.JSONField(
        default=list, blank=True,
        help_text="Checklist of conditions that indicate readiness to proceed to next phase"
    )
    # Phase outcome: one-line summary of career impact of completing this phase
    phase_outcome = models.CharField(
        max_length=400, blank=True,
        help_text="Career-impact summary: what doing this phase unlocks for the learner"
    )

    class Meta:
        ordering = ["learning_path", "order"]
        unique_together = ["learning_path", "order"]
    
    def __str__(self):
        return f"{self.learning_path.title} - {self.title}"


class LearningResource(TimeStampedModel):
    """Learning resource (course, article, video, etc.)."""
    
    class ResourceType(models.TextChoices):
        COURSE = "course", "Course"
        VIDEO = "video", "Video"
        ARTICLE = "article", "Article"
        BOOK = "book", "Book"
        TUTORIAL = "tutorial", "Tutorial"
        DOCUMENTATION = "documentation", "Documentation"
        PRACTICE = "practice", "Practice Exercise"
        PROJECT = "project", "Project"
        QUIZ = "quiz", "Quiz"
        CERTIFICATION = "certification", "Certification"
    
    class Provider(models.TextChoices):
        INTERNAL = "internal", "Internal"
        COURSERA = "coursera", "Coursera"
        UDEMY = "udemy", "Udemy"
        EDEX = "edx", "edX"
        PLURALSIGHT = "pluralsight", "Pluralsight"
        LINKEDIN = "linkedin", "LinkedIn Learning"
        YOUTUBE = "youtube", "YouTube"
        MEDIUM = "medium", "Medium"
        GITHUB = "github", "GitHub"
        OTHER = "other", "Other"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    
    # Type and source
    resource_type = models.CharField(
        max_length=20,
        choices=ResourceType.choices,
        default=ResourceType.ARTICLE
    )
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.OTHER
    )
    
    # URL — optional; when blank a search_query-derived URL is used instead
    url = models.URLField(blank=True)
    # Provider-specific search query so the link stays fresh even if the video is re-uploaded
    search_query = models.CharField(
        max_length=300, blank=True,
        help_text="Search query to locate this resource on the provider platform"
    )
    thumbnail = models.URLField(blank=True)
    
    # Metadata
    author = models.CharField(max_length=200, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    difficulty = models.CharField(
        max_length=20,
        choices=LearningPath.DifficultyLevel.choices,
        default=LearningPath.DifficultyLevel.BEGINNER
    )
    
    # Classification
    skills = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    
    # Pricing
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_currency = models.CharField(max_length=3, default="USD")
    
    # Phase relationship (optional - resource can be standalone)
    phase = models.ForeignKey(
        LearningPhase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resources"
    )
    order_in_phase = models.PositiveIntegerField(default=0)
    
    # Statistics
    views_count = models.PositiveIntegerField(default=0)
    completions_count = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0
    )
    
    class Meta:
        ordering = ["phase", "order_in_phase", "-created_at"]
        indexes = [
            models.Index(fields=["resource_type"]),
            models.Index(fields=["provider"]),
            models.Index(fields=["is_free"]),
        ]
    
    def __str__(self):
        return self.title

    @property
    def effective_url(self) -> str:
        """Return a working URL — stored URL if present, otherwise a search URL built from search_query + provider."""
        if self.url:
            return self.url
        if self.search_query:
            from urllib.parse import quote_plus
            q = quote_plus(self.search_query)
            search_map = {
                self.Provider.YOUTUBE: f"https://www.youtube.com/results?search_query={q}",
                self.Provider.COURSERA: f"https://www.coursera.org/search?query={q}",
                self.Provider.UDEMY: f"https://www.udemy.com/courses/search/?q={q}",
                self.Provider.GITHUB: f"https://github.com/search?q={q}",
                self.Provider.MEDIUM: f"https://medium.com/search?q={q}",
                self.Provider.LINKEDIN: f"https://www.linkedin.com/learning/search?keywords={q}",
            }
            return search_map.get(self.provider, f"https://www.google.com/search?q={q}")
        return ""


class UserLearningPathEnrollment(TimeStampedModel):
    """User enrollment in a learning path."""
    
    class EnrollmentStatus(models.TextChoices):
        ENROLLED = "enrolled", "Enrolled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        DROPPED = "dropped", "Dropped"
        PAUSED = "paused", "Paused"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="learning_enrollments"
    )
    learning_path = models.ForeignKey(
        LearningPath,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED
    )
    progress_percentage = models.PositiveIntegerField(default=0)
    
    # Phases completed
    completed_phases = models.JSONField(default=list, blank=True)
    current_phase = models.ForeignKey(
        LearningPhase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_users"
    )
    
    # Time tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    total_time_spent_minutes = models.PositiveIntegerField(default=0)
    
    # Rating
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    review = models.TextField(blank=True)
    
    # Personalization
    personalized_for_career = models.ForeignKey(
        "career.CareerPath",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="personalized_enrollments"
    )
    
    class Meta:
        unique_together = ["user", "learning_path"]
        ordering = ["-last_activity_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["learning_path", "status"]),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.learning_path.title}"


class UserResourceProgress(TimeStampedModel):
    """User progress on a specific resource."""
    
    class ProgressStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resource_progress"
    )
    resource = models.ForeignKey(
        LearningResource,
        on_delete=models.CASCADE,
        related_name="user_progress"
    )
    enrollment = models.ForeignKey(
        UserLearningPathEnrollment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="resource_progress"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=ProgressStatus.choices,
        default=ProgressStatus.NOT_STARTED
    )
    progress_percentage = models.PositiveIntegerField(default=0)
    
    # Time tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_minutes = models.PositiveIntegerField(default=0)
    
    # Notes and bookmarks
    notes = models.TextField(blank=True)
    is_bookmarked = models.BooleanField(default=False)
    
    # Rating
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ["user", "resource"]
        ordering = ["-updated_at"]
    
    def __str__(self):
        return f"{self.user.email} - {self.resource.title}"


class KnowledgeCheckpoint(TimeStampedModel):
    """Knowledge assessment checkpoint."""
    
    class CheckpointType(models.TextChoices):
        QUIZ = "quiz", "Quiz"
        ASSESSMENT = "assessment", "Assessment"
        PROJECT = "project", "Project"
        EXERCISE = "exercise", "Exercise"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phase = models.ForeignKey(
        LearningPhase,
        on_delete=models.CASCADE,
        related_name="checkpoints"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Type
    checkpoint_type = models.CharField(
        max_length=20,
        choices=CheckpointType.choices,
        default=CheckpointType.QUIZ
    )
    
    # Questions (for quizzes)
    questions = models.JSONField(default=list, blank=True)
    
    # Passing criteria
    passing_score = models.PositiveIntegerField(default=70)
    max_attempts = models.PositiveIntegerField(default=3)
    
    # Time
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["phase", "order"]
    
    def __str__(self):
        return f"{self.phase.title} - {self.title}"


class UserCheckpointAttempt(TimeStampedModel):
    """User attempt at a knowledge checkpoint."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="checkpoint_attempts"
    )
    checkpoint = models.ForeignKey(
        KnowledgeCheckpoint,
        on_delete=models.CASCADE,
        related_name="attempts"
    )
    enrollment = models.ForeignKey(
        UserLearningPathEnrollment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="checkpoint_attempts"
    )
    
    # Attempt info
    attempt_number = models.PositiveIntegerField(default=1)
    
    # Answers
    answers = models.JSONField(default=dict, blank=True)
    
    # Results
    score = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    
    # Feedback
    feedback = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.user.email} - {self.checkpoint.title} (Attempt {self.attempt_number})"


class RetentionQuizQuestion(TimeStampedModel):
    """
    Reusable global quiz-bank question used for pre-phase retention checks.

    Questions are shared across users and paths to keep storage small and avoid
    expensive per-user generation.
    """

    class DifficultyLevel(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=255)
    topic = models.CharField(max_length=120)
    subtopic = models.CharField(max_length=120, blank=True)
    difficulty = models.CharField(
        max_length=20,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.MEDIUM,
    )

    question_text = models.TextField()
    options = models.JSONField(default=list, blank=True)
    correct_answer = models.CharField(max_length=32)
    explanation = models.TextField(blank=True)

    tags = models.JSONField(default=list, blank=True)
    career_tracks = models.JSONField(default=list, blank=True)

    is_active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["topic", "difficulty", "-created_at"]
        indexes = [
            models.Index(fields=["is_active", "difficulty"]),
            models.Index(fields=["topic"]),
        ]

    def __str__(self):
        return f"{self.topic}: {self.title}"


class RetentionQuizAttempt(TimeStampedModel):
    """Stores each pre-phase retention quiz attempt and grading outcome."""

    class AttemptStatus(models.TextChoices):
        STARTED = "started", "Started"
        SUBMITTED = "submitted", "Submitted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="retention_quiz_attempts",
    )
    enrollment = models.ForeignKey(
        UserLearningPathEnrollment,
        on_delete=models.CASCADE,
        related_name="retention_quiz_attempts",
    )
    target_phase = models.ForeignKey(
        LearningPhase,
        on_delete=models.CASCADE,
        related_name="retention_quiz_attempts",
    )

    status = models.CharField(
        max_length=20,
        choices=AttemptStatus.choices,
        default=AttemptStatus.STARTED,
    )

    passing_score = models.PositiveIntegerField(default=70)
    questions_snapshot = models.JSONField(default=list, blank=True)
    answers = models.JSONField(default=dict, blank=True)

    score = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)
    weak_topics = models.JSONField(default=list, blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["enrollment", "target_phase"]),
        ]

    def __str__(self):
        return f"{self.user.email} - retention for {self.target_phase.title}"


class RecommendedResource(TimeStampedModel):
    """AI-recommended resources for a user."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommended_resources"
    )
    resource = models.ForeignKey(
        LearningResource,
        on_delete=models.CASCADE,
        related_name="recommendations"
    )
    
    # Recommendation metadata
    reason = models.TextField(blank=True)
    relevance_score = models.DecimalField(
        max_digits=4, decimal_places=3, default=0
    )
    
    # Related goal/career
    for_career = models.ForeignKey(
        "career.CareerPath",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    for_skill = models.CharField(max_length=100, blank=True)
    
    # Status
    is_dismissed = models.BooleanField(default=False)
    is_viewed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["-relevance_score", "-created_at"]
        unique_together = ["user", "resource"]
    
    def __str__(self):
        return f"Rec for {self.user.email}: {self.resource.title}"


# =============================================================================
# ADAPTIVE LEARNING MODELS - Dynamic Path Updates & Skill Mastery
# =============================================================================

class UserSkillMastery(TimeStampedModel):
    """
    Track user's mastery level for each skill over time.
    Supports skill decay and reinforcement tracking.
    """
    
    class MasteryLevel(models.TextChoices):
        NOVICE = "novice", "Novice (0-20%)"
        BEGINNER = "beginner", "Beginner (21-40%)"
        INTERMEDIATE = "intermediate", "Intermediate (41-60%)"
        PROFICIENT = "proficient", "Proficient (61-80%)"
        EXPERT = "expert", "Expert (81-100%)"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="skill_masteries"
    )
    skill_name = models.CharField(max_length=100)
    
    # Mastery tracking
    mastery_score = models.PositiveIntegerField(default=0)  # 0-100
    mastery_level = models.CharField(
        max_length=20,
        choices=MasteryLevel.choices,
        default=MasteryLevel.NOVICE
    )
    
    # Verification history
    last_verified_at = models.DateTimeField(null=True, blank=True)
    verification_count = models.PositiveIntegerField(default=0)
    verification_history = models.JSONField(default=list, blank=True)
    # Format: [{"date": "...", "type": "quiz|project|cert", "score": 85, "source": "..."}]
    
    # Decay tracking
    decay_rate = models.FloatField(default=0.5)  # Points lost per week of inactivity
    days_since_practice = models.PositiveIntegerField(default=0)
    
    # Learning source
    learned_from = models.JSONField(default=list, blank=True)
    # Format: [{"path_id": "...", "phase_id": "...", "resource_id": "..."}]
    
    class Meta:
        unique_together = ["user", "skill_name"]
        ordering = ["-mastery_score", "skill_name"]
        indexes = [
            models.Index(fields=["user", "skill_name"]),
            models.Index(fields=["mastery_level"]),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.skill_name} ({self.mastery_score}%)"
    
    def update_mastery_level(self):
        """Update mastery level based on score."""
        if self.mastery_score <= 20:
            self.mastery_level = self.MasteryLevel.NOVICE
        elif self.mastery_score <= 40:
            self.mastery_level = self.MasteryLevel.BEGINNER
        elif self.mastery_score <= 60:
            self.mastery_level = self.MasteryLevel.INTERMEDIATE
        elif self.mastery_score <= 80:
            self.mastery_level = self.MasteryLevel.PROFICIENT
        else:
            self.mastery_level = self.MasteryLevel.EXPERT
    
    def apply_decay(self, days_inactive: int):
        """Apply skill decay based on inactivity."""
        decay_amount = int(days_inactive * self.decay_rate / 7)  # Weekly decay
        self.mastery_score = max(0, self.mastery_score - decay_amount)
        self.days_since_practice = days_inactive
        self.update_mastery_level()
    
    def record_verification(self, verification_type: str, score: int, source: str = ""):
        """Record a skill verification event."""
        from django.utils import timezone
        
        self.verification_history.append({
            "date": timezone.now().isoformat(),
            "type": verification_type,
            "score": score,
            "source": source
        })
        self.last_verified_at = timezone.now()
        self.verification_count += 1
        self.days_since_practice = 0
        
        # Update mastery based on verification
        # Weighted average: 70% current + 30% new score
        self.mastery_score = int(self.mastery_score * 0.7 + score * 0.3)
        self.update_mastery_level()


class PhaseInjection(TimeStampedModel):
    """
    Represents additional content injected into a learning phase
    based on user performance (remedial content, advanced content, etc.)
    """
    
    class InjectionType(models.TextChoices):
        REMEDIAL = "remedial", "Remedial (Fill knowledge gaps)"
        REINFORCEMENT = "reinforcement", "Reinforcement (Practice weak areas)"
        ADVANCED = "advanced", "Advanced (Extra challenge)"
        PRACTICAL = "practical", "Practical (Hands-on project)"
        REFRESHER = "refresher", "Refresher (Skill decay prevention)"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        UserLearningPathEnrollment,
        on_delete=models.CASCADE,
        related_name="phase_injections"
    )
    target_phase = models.ForeignKey(
        LearningPhase,
        on_delete=models.CASCADE,
        related_name="injections"
    )
    
    # Injection details
    injection_type = models.CharField(
        max_length=20,
        choices=InjectionType.choices,
        default=InjectionType.REMEDIAL
    )
    title = models.CharField(max_length=200)
    reason = models.TextField()  # Why this was injected
    
    # Weak areas that triggered this
    weak_concepts = models.JSONField(default=list, blank=True)
    # Format: ["List Comprehensions", "Lambda Functions"]
    
    # Resources to complete
    injected_resources = models.JSONField(default=list, blank=True)
    # Format: [{"title": "...", "url": "...", "type": "video", "duration_minutes": 30}]
    
    # Optional quiz for verification
    verification_quiz = models.JSONField(default=dict, blank=True)
    # Format: {"questions": [...], "passing_score": 70}
    
    # Status
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_score = models.PositiveIntegerField(null=True, blank=True)
    
    # Priority (higher = do first)
    priority = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ["-priority", "created_at"]
    
    def __str__(self):
        return f"{self.injection_type} for {self.enrollment.user.email} - {self.title}"


class ProjectSubmission(TimeStampedModel):
    """
    User project submissions for practical skill validation.
    Projects are reviewed by AI (Gemini) for feedback and scoring.
    """
    
    class SubmissionStatus(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        REVIEWED = "reviewed", "Reviewed"
        APPROVED = "approved", "Approved"
        NEEDS_REVISION = "needs_revision", "Needs Revision"
        REJECTED = "rejected", "Rejected"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_submissions"
    )
    
    # What this is for
    phase = models.ForeignKey(
        LearningPhase,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="project_submissions"
    )
    enrollment = models.ForeignKey(
        UserLearningPathEnrollment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="project_submissions"
    )
    
    # Project details
    title = models.CharField(max_length=200)
    description = models.TextField()
    project_url = models.URLField()  # GitHub, GitLab, CodePen, etc.
    live_demo_url = models.URLField(blank=True)
    
    # Technologies used
    technologies = models.JSONField(default=list, blank=True)
    skills_demonstrated = models.JSONField(default=list, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.SUBMITTED
    )
    
    # AI Review (Gemini)
    ai_review = models.JSONField(default=dict, blank=True)
    # Format: {
    #   "overall_score": 85,
    #   "code_quality": {"score": 80, "feedback": "..."},
    #   "documentation": {"score": 90, "feedback": "..."},
    #   "functionality": {"score": 85, "feedback": "..."},
    #   "best_practices": {"score": 80, "feedback": "..."},
    #   "strengths": ["...", "..."],
    #   "improvements": ["...", "..."],
    #   "detailed_feedback": "..."
    # }
    
    # Scores
    overall_score = models.PositiveIntegerField(null=True, blank=True)
    
    # Review metadata
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_notes = models.TextField(blank=True)  # Admin notes if manual review
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["phase", "status"]),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.title}"


class CertificateVerification(TimeStampedModel):
    """
    Track certificates uploaded by users to verify course completion.
    Supports OCR extraction and manual verification.
    """
    
    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"
        MANUAL_REVIEW = "manual_review", "Manual Review Required"
    
    class VerificationMethod(models.TextChoices):
        OCR = "ocr", "OCR Extraction"
        API = "api", "Platform API"
        MANUAL = "manual", "Manual Verification"
        URL_CHECK = "url_check", "URL Verification"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certificate_verifications"
    )
    
    # Related resource (if applicable)
    resource = models.ForeignKey(
        LearningResource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="certificate_verifications"
    )
    enrollment = models.ForeignKey(
        UserLearningPathEnrollment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="certificate_verifications"
    )
    
    # Certificate details
    certificate_url = models.URLField(blank=True)  # If hosted online
    certificate_image = models.URLField(blank=True)  # Uploaded image URL
    
    # Extracted/provided info
    course_name = models.CharField(max_length=300)
    platform = models.CharField(max_length=100)  # Coursera, Udemy, etc.
    completion_date = models.DateField(null=True, blank=True)
    certificate_id = models.CharField(max_length=100, blank=True)  # Platform's cert ID
    
    # Skills covered by this certificate
    skills_covered = models.JSONField(default=list, blank=True)
    
    # Verification
    status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    verification_method = models.CharField(
        max_length=20,
        choices=VerificationMethod.choices,
        blank=True
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # OCR data (if used)
    ocr_extracted_data = models.JSONField(default=dict, blank=True)
    
    # Verification result
    verification_notes = models.TextField(blank=True)
    confidence_score = models.FloatField(null=True, blank=True)  # 0-1, how confident we are
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["platform"]),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.course_name} ({self.status})"


class SkillRefresherQuiz(TimeStampedModel):
    """
    Periodic quizzes sent to users to prevent skill decay.
    Triggered when skills haven't been practiced in X days.
    """
    
    class QuizStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent to User"
        COMPLETED = "completed", "Completed"
        EXPIRED = "expired", "Expired"
        SKIPPED = "skipped", "Skipped by User"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refresher_quizzes"
    )
    skill_mastery = models.ForeignKey(
        UserSkillMastery,
        on_delete=models.CASCADE,
        related_name="refresher_quizzes"
    )
    
    # Quiz content
    skill_name = models.CharField(max_length=100)
    questions = models.JSONField(default=list)
    # Format: [{"question": "...", "options": [...], "correct_answer": "...", "explanation": "..."}]
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=QuizStatus.choices,
        default=QuizStatus.PENDING
    )
    
    # Timing
    sent_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    answers = models.JSONField(default=dict, blank=True)
    score = models.PositiveIntegerField(null=True, blank=True)
    passed = models.BooleanField(default=False)
    
    # Impact on mastery
    mastery_before = models.PositiveIntegerField(default=0)
    mastery_after = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"Refresher for {self.user.email} - {self.skill_name}"


class LearningPathUpdate(TimeStampedModel):
    """
    Track all dynamic updates/modifications to a user's learning path.
    Provides audit trail of how the path evolved based on performance.
    """
    
    class UpdateType(models.TextChoices):
        INJECTION_ADDED = "injection_added", "Remedial Content Added"
        DIFFICULTY_ADJUSTED = "difficulty_adjusted", "Difficulty Adjusted"
        RESOURCE_REPLACED = "resource_replaced", "Resource Replaced"
        PHASE_REORDERED = "phase_reordered", "Phase Order Changed"
        SKILL_FOCUS_CHANGED = "skill_focus_changed", "Skill Focus Updated"
        TIMELINE_EXTENDED = "timeline_extended", "Timeline Extended"
        ADVANCED_CONTENT = "advanced_content", "Advanced Content Unlocked"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        UserLearningPathEnrollment,
        on_delete=models.CASCADE,
        related_name="path_updates"
    )
    
    # Update details
    update_type = models.CharField(
        max_length=30,
        choices=UpdateType.choices
    )
    description = models.TextField()
    
    # What triggered this update
    trigger_source = models.CharField(max_length=50)  # "quiz_failure", "project_review", etc.
    trigger_data = models.JSONField(default=dict, blank=True)
    # Format: {"quiz_id": "...", "score": 45, "weak_topics": ["..."]}
    
    # Changes made
    changes = models.JSONField(default=dict, blank=True)
    # Format: {"added": [...], "removed": [...], "modified": [...]}
    
    # AI reasoning (if Gemini was involved)
    ai_reasoning = models.TextField(blank=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.update_type} for {self.enrollment.user.email}"


class UserLearningStreak(TimeStampedModel):
    """
    Tracks a user's daily learning activity streak.
    Updated via Django signal whenever a resource is completed.
    Replaces every hardcoded streak value in the frontend.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="learning_streak"
    )

    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)

    # Total days with at least one learning activity
    total_active_days = models.PositiveIntegerField(default=0)

    # Streak history for gamification display
    streak_history = models.JSONField(default=list, blank=True)
    # Format: [{"date": "2026-02-23", "resources_completed": 3, "minutes_spent": 45}]

    class Meta:
        verbose_name = "User Learning Streak"

    def __str__(self):
        return f"{self.user.email} — streak {self.current_streak}d"

    def record_activity(self, resources_completed: int = 1, minutes_spent: int = 0):
        """Call when a user completes a resource. Updates streak logic."""
        from django.utils import timezone as tz
        today = tz.now().date()

        if self.last_activity_date == today:
            # Already active today — just update today's history entry
            if self.streak_history and self.streak_history[-1].get("date") == str(today):
                self.streak_history[-1]["resources_completed"] += resources_completed
                self.streak_history[-1]["minutes_spent"] += minutes_spent
            return

        yesterday = today - timedelta(days=1)
        if self.last_activity_date == yesterday:
            # Consecutive day — extend streak
            self.current_streak += 1
        else:
            # Streak broken (or first activity)
            self.current_streak = 1

        self.longest_streak = max(self.longest_streak, self.current_streak)
        self.last_activity_date = today
        self.total_active_days += 1
        self.streak_history.append({
            "date": str(today),
            "resources_completed": resources_completed,
            "minutes_spent": minutes_spent,
        })
        # Keep only last 90 days of history
        self.streak_history = self.streak_history[-90:]


class SkillTutorialCache(TimeStampedModel):
    """
    Caches tutorial ordering heuristics per (skill, level) to avoid
    repeated LLM calls on GET /tutorials/skill/<name>/.
    Cache is valid for 24 hours. No LLM involved — pure ordering logic stored here.
    """
    skill_name = models.CharField(max_length=100)
    level = models.CharField(max_length=20, default="beginner")
    ordered_video_ids = models.JSONField(default=list)
    # Format: ["videoId1", "videoId2", ...]  (YouTube video IDs in heuristic order)
    learning_tips = models.JSONField(default=list)
    prerequisite_topics = models.JSONField(default=list)
    expires_at = models.DateTimeField()

    class Meta:
        unique_together = [("skill_name", "level")]
        verbose_name = "Skill Tutorial Cache"

    def __str__(self):
        return f"{self.skill_name} ({self.level})"

    @property
    def is_expired(self) -> bool:
        from django.utils import timezone as tz
        return tz.now() >= self.expires_at
