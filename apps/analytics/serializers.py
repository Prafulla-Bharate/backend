"""
Analytics Serializers
=====================
Serializers for analytics models and data.
"""

from rest_framework import serializers

from apps.analytics.models import (
    UserActivity,
    CareerAnalytics,
    LearningAnalytics,
    JobSearchAnalytics,
    InterviewAnalytics,
)


# ============================================================================
# User Activity Serializers
# ============================================================================

class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for user activities."""
    
    class Meta:
        model = UserActivity
        fields = [
            "id",
            "activity_type",
            "description",
            "resource_type",
            "resource_id",
            "resource_name",
            "path",
            "device_type",
            "browser",
            "metadata",
            "created_at",
        ]


class CreateActivitySerializer(serializers.Serializer):
    """Serializer for creating activity events."""
    
    activity_type = serializers.ChoiceField(
        choices=UserActivity.ActivityType.choices
    )
    resource_type = serializers.CharField(required=False, allow_blank=True)
    resource_id = serializers.UUIDField(required=False)
    resource_name = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)


class UserMetricsSummarySerializer(serializers.Serializer):
    """Summary serializer for user metrics."""
    
    total_page_views = serializers.IntegerField()
    total_sessions = serializers.IntegerField()
    total_time_spent_hours = serializers.DecimalField(
        max_digits=8, decimal_places=2
    )
    total_jobs_applied = serializers.IntegerField()
    total_learning_hours = serializers.DecimalField(
        max_digits=8, decimal_places=2
    )
    total_practice_sessions = serializers.IntegerField()
    current_streak = serializers.IntegerField()
    profile_completeness = serializers.IntegerField()


# ============================================================================
# Career Analytics Serializers
# ============================================================================

class CareerAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for career analytics."""
    
    career_path_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CareerAnalytics
        fields = [
            "id",
            "career_path",
            "career_path_name",
            "overall_progress",
            "skills_progress",
            "experience_progress",
            "education_progress",
            "total_skills",
            "acquired_skills",
            "in_progress_skills",
            "missing_skills",
            "strong_skills",
            "market_demand_score",
            "salary_percentile",
            "competition_level",
            "next_steps",
            "recommended_resources",
            "estimated_completion_date",
            "days_to_goal",
            "progress_history",
            "updated_at",
        ]
    
    def get_career_path_name(self, obj):
        return obj.career_path.name if obj.career_path else None


# ============================================================================
# Learning Analytics Serializers
# ============================================================================

class LearningAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for learning analytics."""
    
    class Meta:
        model = LearningAnalytics
        fields = [
            "id",
            "total_learning_time_hours",
            "total_resources_completed",
            "total_checkpoints_passed",
            "total_paths_started",
            "total_paths_completed",
            "current_streak_days",
            "longest_streak_days",
            "last_activity_date",
            "average_checkpoint_score",
            "completion_rate",
            "preferred_learning_time",
            "preferred_day_of_week",
            "average_session_length_minutes",
            "category_progress",
            "skills_acquired",
            "monthly_stats",
            "updated_at",
        ]


# ============================================================================
# Job Search Analytics Serializers
# ============================================================================

class JobSearchAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for job search analytics."""
    
    class Meta:
        model = JobSearchAnalytics
        fields = [
            "id",
            "total_applications",
            "applications_this_month",
            "applications_this_week",
            "pending_applications",
            "reviewed_applications",
            "interviews_scheduled",
            "offers_received",
            "rejections",
            "response_rate",
            "interview_rate",
            "offer_rate",
            "total_jobs_viewed",
            "total_jobs_saved",
            "average_time_per_application_days",
            "most_searched_keywords",
            "preferred_locations",
            "preferred_job_types",
            "salary_range_searched",
            "companies_applied",
            "companies_responded",
            "average_response_time_days",
            "average_time_to_interview_days",
            "weekly_stats",
            "updated_at",
        ]


# ============================================================================
# Interview Analytics Serializers
# ============================================================================

class InterviewAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for interview analytics."""
    
    class Meta:
        model = InterviewAnalytics
        fields = [
            "id",
            "total_practice_sessions",
            "total_questions_answered",
            "total_practice_time_hours",
            "average_score",
            "best_score",
            "improvement_rate",
            "scores_by_type",
            "questions_by_type",
            "scores_by_difficulty",
            "strongest_areas",
            "weakest_areas",
            "total_real_interviews",
            "real_interview_success_rate",
            "weekly_scores",
            "monthly_progress",
            "updated_at",
        ]


# ============================================================================
# Dashboard Serializers
# ============================================================================

class UserDashboardAnalyticsSerializer(serializers.Serializer):
    """Serializer for user dashboard analytics."""
    
    metrics_summary = UserMetricsSummarySerializer()
    career_analytics = CareerAnalyticsSerializer(required=False)
    learning_analytics = LearningAnalyticsSerializer(required=False)
    job_search_analytics = JobSearchAnalyticsSerializer(required=False)
    interview_analytics = InterviewAnalyticsSerializer(required=False)
    recent_activities = UserActivitySerializer(many=True)
