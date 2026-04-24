"""
Learning Serializers
====================
Serializers for learning-related data.
"""

from rest_framework import serializers

from apps.learning.models import (
    LearningPath,
    LearningPhase,
    LearningResource,
    UserLearningPathEnrollment,
    UserResourceProgress,
    KnowledgeCheckpoint,
    UserCheckpointAttempt,
    RecommendedResource,
    PhaseInjection,
    ProjectSubmission,
    CertificateVerification,
    SkillRefresherQuiz,
    UserLearningStreak,
)


# ============================================================================
# Resource Serializers
# ============================================================================

class LearningResourceSerializer(serializers.ModelSerializer):
    """Full serializer for learning resources."""

    user_progress = serializers.SerializerMethodField()
    # Computed stable search URL — safe to use as href even if url field is blank
    effective_url = serializers.ReadOnlyField()

    class Meta:
        model = LearningResource
        fields = [
            "id", "title", "description", "resource_type", "provider",
            "url", "search_query", "effective_url",
            "thumbnail", "author", "duration_minutes", "difficulty",
            "skills", "tags", "is_free", "price", "price_currency",
            "views_count", "completions_count", "average_rating",
            "user_progress", "created_at"
        ]
    
    def get_user_progress(self, obj):
        """Get progress for current user."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            try:
                progress = UserResourceProgress.objects.get(
                    user=request.user,
                    resource=obj
                )
                return {
                    "status": progress.status,
                    "progress_percentage": progress.progress_percentage,
                    "is_bookmarked": progress.is_bookmarked
                }
            except UserResourceProgress.DoesNotExist:
                pass
        return None


class LearningResourceListSerializer(serializers.ModelSerializer):
    """List serializer for learning resources — includes URL fields for clickable links."""

    effective_url = serializers.ReadOnlyField()

    class Meta:
        model = LearningResource
        fields = [
            "id", "title", "resource_type", "provider", "thumbnail",
            "duration_minutes", "difficulty", "is_free", "average_rating",
            "url", "search_query", "effective_url",
        ]


# ============================================================================
# Checkpoint Serializers
# ============================================================================

class KnowledgeCheckpointSerializer(serializers.ModelSerializer):
    """Serializer for knowledge checkpoints."""
    
    user_best_score = serializers.SerializerMethodField()
    attempts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = KnowledgeCheckpoint
        fields = [
            "id", "title", "description", "checkpoint_type",
            "passing_score", "max_attempts", "time_limit_minutes",
            "order", "is_required", "user_best_score", "attempts_count"
        ]
    
    def get_user_best_score(self, obj):
        """Get best score for current user."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            best = UserCheckpointAttempt.objects.filter(
                user=request.user,
                checkpoint=obj
            ).order_by("-score").first()
            if best:
                return {"score": best.score, "passed": best.passed}
        return None
    
    def get_attempts_count(self, obj):
        """Get attempts count for current user."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return UserCheckpointAttempt.objects.filter(
                user=request.user,
                checkpoint=obj
            ).count()
        return 0


class CheckpointAttemptSerializer(serializers.ModelSerializer):
    """Serializer for checkpoint attempts."""
    
    class Meta:
        model = UserCheckpointAttempt
        fields = [
            "id", "checkpoint", "attempt_number", "score", "passed",
            "started_at", "completed_at", "time_taken_seconds",
            "feedback", "created_at"
        ]
        read_only_fields = [
            "id", "attempt_number", "score", "passed",
            "started_at", "completed_at", "time_taken_seconds",
            "feedback", "created_at"
        ]


class SubmitAnswersSerializer(serializers.Serializer):
    """Serializer for submitting checkpoint answers."""
    
    answers = serializers.DictField()


# ============================================================================
# Phase Serializers
# ============================================================================

class LearningPhaseSerializer(serializers.ModelSerializer):
    """Serializer for learning phases."""

    resources = LearningResourceListSerializer(many=True, read_only=True)
    checkpoints = KnowledgeCheckpointSerializer(many=True, read_only=True)
    is_completed = serializers.SerializerMethodField()
    # status is derived: completed / in_progress / not_started
    status = serializers.SerializerMethodField()

    class Meta:
        model = LearningPhase
        fields = [
            "id", "title", "description", "order", "estimated_hours",
            "difficulty", "skills_covered",
            "topics_covered", "phase_outcome",
            "readiness_checklist", "interview_questions",
            "learning_objectives", "prerequisite_skills",
            "resources", "checkpoints", "is_completed", "status",
        ]

    def _get_enrollment(self, obj):
        """Return the user's enrollment for this phase's path (cached on context)."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        cache_key = f"_enrollment_{obj.learning_path_id}"
        if cache_key not in self.context:
            self.context[cache_key] = UserLearningPathEnrollment.objects.filter(
                user=request.user, learning_path_id=obj.learning_path_id
            ).order_by("-created_at").first()
        return self.context[cache_key]

    def get_is_completed(self, obj):
        enrollment = self._get_enrollment(obj)
        if enrollment:
            return str(obj.id) in (enrollment.completed_phases or [])
        return False

    def get_status(self, obj):
        enrollment = self._get_enrollment(obj)
        if not enrollment:
            return "not_started"
        if str(obj.id) in (enrollment.completed_phases or []):
            return "completed"
        if enrollment.current_phase_id and str(enrollment.current_phase_id) == str(obj.id):
            return "in_progress"
        return "not_started"


class LearningPhaseListSerializer(serializers.ModelSerializer):
    """List serializer for learning phases."""

    resources_count = serializers.SerializerMethodField()

    class Meta:
        model = LearningPhase
        fields = [
            "id", "title", "order", "estimated_hours",
            "difficulty", "resources_count"
        ]
    
    def get_resources_count(self, obj):
        return obj.resources.count()


# ============================================================================
# Learning Path Serializers
# ============================================================================

class LearningPathSerializer(serializers.ModelSerializer):
    """Full serializer for learning paths."""
    
    phases = LearningPhaseSerializer(many=True, read_only=True)
    enrollment = serializers.SerializerMethodField()
    
    class Meta:
        model = LearningPath
        fields = [
            "id", "title", "slug", "description", "short_description",
            "difficulty", "category", "tags", "skills_covered",
            "prerequisites", "estimated_hours", "thumbnail", "objectives",
            "is_ai_generated", "enrollments_count", "completions_count",
            "average_rating", "is_featured", "phases", "enrollment",
            # New adaptive fields
            "skill_gap_analysis", "generation_context",
            "created_at"
        ]
    
    def get_enrollment(self, obj):
        """Get enrollment info for current user."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            try:
                enrollment = UserLearningPathEnrollment.objects.get(
                    user=request.user,
                    learning_path=obj
                )
                return {
                    "status": enrollment.status,
                    "progress_percentage": enrollment.progress_percentage,
                    "started_at": enrollment.started_at,
                    "current_phase_id": str(enrollment.current_phase_id)
                        if enrollment.current_phase else None
                }
            except UserLearningPathEnrollment.DoesNotExist:
                pass
        return None


class LearningPathListSerializer(serializers.ModelSerializer):
    """List serializer for learning paths."""
    
    phases_count = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()
    
    class Meta:
        model = LearningPath
        fields = [
            "id", "title", "slug", "short_description", "difficulty",
            "category", "estimated_hours", "thumbnail", "is_featured",
            "enrollments_count", "average_rating", "phases_count",
            "is_enrolled"
        ]
    
    def get_phases_count(self, obj):
        return obj.phases.count()
    
    def get_is_enrolled(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return UserLearningPathEnrollment.objects.filter(
                user=request.user,
                learning_path=obj
            ).exists()
        return False


class LearningPathCreateSerializer(serializers.Serializer):
    """Serializer for AI-generated learning path request."""

    target_career_id = serializers.UUIDField(required=False)
    # Free-text career title — used when the career comes from a Gemini prediction
    # and we don't have a DB UUID yet.
    target_career_title = serializers.CharField(required=False, allow_blank=True)
    target_skills = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    current_skills = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    time_commitment_hours_per_week = serializers.IntegerField(
        min_value=1, max_value=40, default=10
    )
    preferred_difficulty = serializers.ChoiceField(
        choices=LearningPath.DifficultyLevel.choices,
        required=False
    )
    weekly_hours = serializers.IntegerField(min_value=1, max_value=40, required=False)
    timeline_weeks = serializers.IntegerField(min_value=1, max_value=52, required=False)
    learning_style = serializers.CharField(required=False, allow_blank=True)
    preferred_resource_types = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


# ============================================================================
# Enrollment Serializers
# ============================================================================

class EnrollmentSerializer(serializers.ModelSerializer):
    """Full enrollment serializer — includes full path with phases and resources."""

    learning_path = LearningPathSerializer(read_only=True)
    current_phase = LearningPhaseListSerializer(read_only=True)
    career_goal = serializers.SerializerMethodField()

    class Meta:
        model = UserLearningPathEnrollment
        fields = [
            "id", "learning_path", "career_goal", "status", "progress_percentage",
            "completed_phases", "current_phase", "started_at",
            "completed_at", "last_activity_at", "total_time_spent_minutes",
            "rating", "review", "created_at"
        ]

    def get_career_goal(self, obj):
        """Return the accepted career title this enrollment was personalized for."""
        if obj.personalized_for_career:
            return obj.personalized_for_career.title
        # Fall back: derive from path title ('Path to X' or 'Personalized Path for ...')
        title = obj.learning_path.title if obj.learning_path else ""
        for prefix in ("Path to ", "Personalized Path for "):
            if title.startswith(prefix):
                return title[len(prefix):]
        return title


class EnrollmentListSerializer(serializers.ModelSerializer):
    """List serializer for enrollments."""
    
    learning_path_title = serializers.CharField(
        source="learning_path.title",
        read_only=True
    )
    learning_path_slug = serializers.CharField(
        source="learning_path.slug",
        read_only=True
    )
    learning_path_thumbnail = serializers.URLField(
        source="learning_path.thumbnail",
        read_only=True
    )
    
    class Meta:
        model = UserLearningPathEnrollment
        fields = [
            "id", "learning_path_title", "learning_path_slug",
            "learning_path_thumbnail", "status", "progress_percentage",
            "last_activity_at"
        ]


# ============================================================================
# Progress Serializers
# ============================================================================

class ResourceProgressSerializer(serializers.ModelSerializer):
    """Serializer for resource progress."""
    
    resource = LearningResourceListSerializer(read_only=True)
    
    class Meta:
        model = UserResourceProgress
        fields = [
            "id", "resource", "status", "progress_percentage",
            "started_at", "completed_at", "time_spent_minutes",
            "notes", "is_bookmarked", "rating", "updated_at"
        ]


class ResourceProgressUpdateSerializer(serializers.Serializer):
    """Serializer for updating resource progress."""
    
    status = serializers.ChoiceField(
        choices=UserResourceProgress.ProgressStatus.choices,
        required=False
    )
    progress_percentage = serializers.IntegerField(
        min_value=0, max_value=100, required=False
    )
    time_spent_minutes = serializers.IntegerField(min_value=0, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    is_bookmarked = serializers.BooleanField(required=False)
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)


# ============================================================================
# Recommendation Serializers
# ============================================================================

class RecommendedResourceSerializer(serializers.ModelSerializer):
    """Serializer for recommended resources."""
    
    resource = LearningResourceListSerializer(read_only=True)
    
    class Meta:
        model = RecommendedResource
        fields = [
            "id", "resource", "reason", "relevance_score",
            "for_skill", "is_viewed", "created_at"
        ]


# ============================================================================
# Dashboard Serializers
# ============================================================================

class LearningDashboardSerializer(serializers.Serializer):
    """Serializer for learning dashboard."""
    
    active_enrollments = EnrollmentListSerializer(many=True)
    completed_count = serializers.IntegerField()
    total_time_spent_hours = serializers.IntegerField()
    skills_learned = serializers.ListField(child=serializers.CharField())
    recommendations = RecommendedResourceSerializer(many=True)
    recent_activity = serializers.ListField(child=serializers.DictField())


class LearningStatsSerializer(serializers.Serializer):
    """Serializer for learning statistics."""

    total_enrollments = serializers.IntegerField()
    completed = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    total_hours = serializers.IntegerField()
    resources_completed = serializers.IntegerField()
    checkpoints_passed = serializers.IntegerField()
    average_score = serializers.FloatField()


# ============================================================================
# Adaptive / Async Feature Serializers
# ============================================================================

class PhaseInjectionSerializer(serializers.ModelSerializer):
    """Serializer for adaptive PhaseInjection records."""

    class Meta:
        model = PhaseInjection
        fields = [
            "id",
            "injection_type",
            "title",
            "reason",
            "weak_concepts",
            "injected_resources",
            "verification_quiz",
            "is_completed",
            "priority",
            "created_at",
        ]
        read_only_fields = fields


class CompleteInjectionSerializer(serializers.Serializer):
    """Input for completing a phase injection (optional quiz answers)."""

    quiz_answers = serializers.DictField(
        child=serializers.CharField(), required=False, default=dict
    )


class ProjectSubmitSerializer(serializers.Serializer):
    """Input for submitting a project."""

    title = serializers.CharField(max_length=255)
    description = serializers.CharField()
    project_url = serializers.URLField()
    live_demo_url = serializers.URLField(required=False, allow_blank=True, default="")
    phase_id = serializers.UUIDField(required=False, allow_null=True)
    enrollment_id = serializers.UUIDField(required=False, allow_null=True)
    technologies = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    skills_demonstrated = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )


class ProjectSubmissionSerializer(serializers.ModelSerializer):
    """Output serializer for a ProjectSubmission."""

    class Meta:
        model = ProjectSubmission
        fields = [
            "id",
            "title",
            "description",
            "project_url",
            "live_demo_url",
            "technologies",
            "skills_demonstrated",
            "status",
            "overall_score",
            "ai_review",
            "created_at",
        ]
        read_only_fields = fields


class CertificateSubmitSerializer(serializers.Serializer):
    """Input for submitting a certificate."""

    course_name = serializers.CharField(max_length=255)
    platform = serializers.CharField(max_length=100)
    certificate_url = serializers.URLField(required=False, allow_blank=True, default="")
    certificate_image = serializers.CharField(required=False, allow_blank=True, default="")
    completion_date = serializers.DateField(required=False, allow_null=True)
    certificate_id = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    skills_covered = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    resource_id = serializers.UUIDField(required=False, allow_null=True)
    enrollment_id = serializers.UUIDField(required=False, allow_null=True)


class CertificateVerificationSerializer(serializers.ModelSerializer):
    """Output serializer for a CertificateVerification."""

    class Meta:
        model = CertificateVerification
        fields = [
            "id",
            "course_name",
            "platform",
            "certificate_url",
            "status",
            "verification_method",
            "skills_covered",
            "confidence_score",
            "created_at",
        ]
        read_only_fields = fields


class SkillRefresherSerializer(serializers.ModelSerializer):
    """Serializer for a SkillRefresherQuiz (questions without answers)."""

    questions_without_answers = serializers.SerializerMethodField()

    class Meta:
        model = SkillRefresherQuiz
        fields = [
            "id",
            "skill_name",
            "questions_without_answers",
            "status",
            "expires_at",
            "mastery_before",
            "created_at",
        ]
        read_only_fields = fields

    def get_questions_without_answers(self, obj):
        """Strip correct_answer from question objects for the client."""
        questions = obj.questions or []
        return [
            {
                "id": q.get("id"),
                "question": q.get("question"),
                "topic": q.get("topic", ""),
                "options": q.get("options", []),
            }
            for q in questions
        ]


class UserStreakSerializer(serializers.Serializer):
    """Serializer for UserLearningStreak."""

    current_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()
    last_activity_date = serializers.DateField(allow_null=True)
    total_active_days = serializers.IntegerField()
    streak_history = serializers.SerializerMethodField()

    def get_streak_history(self, obj):
        """Return last 7 days of streak history."""
        history = obj.streak_history or []
        return history[-7:]


class ComprehensiveStatsSerializer(serializers.Serializer):
    """Full adaptive stats — extends LearningStatsSerializer."""

    # Core stats
    total_enrollments = serializers.IntegerField()
    completed = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    total_hours = serializers.IntegerField()
    resources_completed = serializers.IntegerField()
    checkpoints_passed = serializers.IntegerField()
    average_score = serializers.FloatField()

    # Skilled extended
    skills = serializers.DictField()          # SkillMasteryService.get_skill_summary()
    projects = serializers.DictField()        # counts + avg score
    certificates = serializers.DictField()   # counts + verified count
    adaptive_learning = serializers.DictField()  # injections resolved / pending
    skill_refreshers = serializers.DictField()   # pending / completed counts
    streak = serializers.DictField(allow_null=True)  # current streak info
