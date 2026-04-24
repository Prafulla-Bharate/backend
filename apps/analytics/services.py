"""
Analytics Services
==================
Business logic for analytics operations.
"""

import logging
from datetime import timedelta, date
from decimal import Decimal

from django.db import models
from django.db.models import Avg, Count, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


class ActivityService:
    """Service for tracking user activities."""
    
    @staticmethod
    def log_activity(
        user,
        activity_type: str,
        resource_type: str = "",
        resource_id=None,
        resource_name: str = "",
        description: str = "",
        request=None,
        metadata: dict = None
    ):
        """Log a user activity synchronously."""
        from apps.analytics.models import UserActivity
        try:
            fields = {
                "user_id": user.id if hasattr(user, 'id') else user,
                "activity_type": activity_type,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "resource_name": resource_name,
                "description": description,
                "metadata": metadata or {},
            }
            if request:
                fields.update({
                    "ip_address": ActivityService._get_client_ip(request),
                    "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
                    "referrer": request.META.get("HTTP_REFERER", "")[:200],
                    "path": request.path[:500],
                })
            UserActivity.objects.create(**fields)
        except Exception as e:
            logger.warning(f"Failed to log activity: {e}")
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
    
    @staticmethod
    def get_user_activities(
        user,
        activity_type: str = None,
        days: int = 30,
        limit: int = 50
    ):
        """Get user activities."""
        from apps.analytics.models import UserActivity
        
        cutoff = timezone.now() - timedelta(days=days)
        
        queryset = UserActivity.objects.filter(
            user=user,
            created_at__gte=cutoff
        )
        
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        return queryset.order_by("-created_at")[:limit]


class MetricsService:
    """Service for user metrics operations."""

    @staticmethod
    def _get_effective_learning_minutes(user) -> int:
        """Return best-effort learning minutes even when explicit time tracking is sparse."""
        from apps.learning.models import UserLearningPathEnrollment, UserResourceProgress

        progress_qs = UserResourceProgress.objects.filter(user=user)
        tracked_minutes = progress_qs.aggregate(total=Sum("time_spent_minutes"))["total"] or 0
        if tracked_minutes > 0:
            return int(tracked_minutes)

        enrollment_minutes = UserLearningPathEnrollment.objects.filter(user=user).aggregate(
            total=Sum("total_time_spent_minutes")
        )["total"] or 0

        completed_duration_minutes = progress_qs.filter(status="completed").aggregate(
            total=Sum("resource__duration_minutes")
        )["total"] or 0

        return int(max(enrollment_minutes, completed_duration_minutes, 0))

    @staticmethod
    def _has_any_activity_on_date(user, target_date) -> bool:
        """Return whether the user had any meaningful tracked activity on a given day."""
        from apps.analytics.models import UserActivity, UserMetrics

        if UserMetrics.objects.filter(
            user=user,
            date=target_date,
        ).filter(
            models.Q(sessions__gt=0)
            | models.Q(page_views__gt=0)
            | models.Q(jobs_applied__gt=0)
            | models.Q(learning_time_minutes__gt=0)
            | models.Q(resources_completed__gt=0)
            | models.Q(practice_sessions__gt=0)
            | models.Q(questions_answered__gt=0)
        ).exists():
            return True

        start_dt = timezone.make_aware(timezone.datetime.combine(target_date, timezone.datetime.min.time()))
        end_dt = start_dt + timedelta(days=1)
        return UserActivity.objects.filter(
            user=user,
            created_at__gte=start_dt,
            created_at__lt=end_dt,
        ).exists()
    
    @staticmethod
    def get_or_create_daily_metrics(user, for_date: date = None):
        """Get or create metrics for a date."""
        from apps.analytics.models import UserMetrics
        
        if for_date is None:
            for_date = timezone.now().date()
        
        metrics, _ = UserMetrics.objects.get_or_create(
            user=user,
            date=for_date
        )
        return metrics
    
    @staticmethod
    def update_metrics(user, for_date: date = None, **updates):
        """Update metrics for a user."""
        from apps.analytics.models import UserMetrics
        
        if for_date is None:
            for_date = timezone.now().date()
        
        metrics, _ = UserMetrics.objects.get_or_create(
            user=user,
            date=for_date
        )
        
        for field, value in updates.items():
            if hasattr(metrics, field):
                if isinstance(value, (int, float)):
                    # Increment the value
                    current = getattr(metrics, field) or 0
                    setattr(metrics, field, current + value)
                else:
                    setattr(metrics, field, value)
        
        metrics.save()
        return metrics
    
    @staticmethod
    def get_metrics_summary(user, days: int = 30) -> dict:
        """Get summary of user metrics."""
        from apps.analytics.models import UserMetrics
        
        cutoff = timezone.now().date() - timedelta(days=days)
        
        metrics = UserMetrics.objects.filter(
            user=user,
            date__gte=cutoff
        ).aggregate(
            total_page_views=Sum("page_views"),
            total_sessions=Sum("sessions"),
            total_time_minutes=Sum("time_spent_minutes"),
            total_jobs_applied=Sum("jobs_applied"),
            total_learning_minutes=Sum("learning_time_minutes"),
            total_practice_sessions=Sum("practice_sessions"),
        )
        
        # Get current streak
        streak = MetricsService._calculate_streak(user)
        
        # Get profile completeness
        latest = UserMetrics.objects.filter(user=user).first()
        profile_completeness = latest.profile_completeness if latest else 0
        
        effective_learning_minutes = max(
            metrics["total_learning_minutes"] or 0,
            MetricsService._get_effective_learning_minutes(user),
        )

        return {
            "total_page_views": metrics["total_page_views"] or 0,
            "total_sessions": metrics["total_sessions"] or 0,
            "total_time_spent_hours": round(
                (metrics["total_time_minutes"] or 0) / 60, 2
            ),
            "total_jobs_applied": metrics["total_jobs_applied"] or 0,
            "total_learning_hours": round(
                effective_learning_minutes / 60, 2
            ),
            "total_practice_sessions": metrics["total_practice_sessions"] or 0,
            "current_streak": streak,
            "profile_completeness": profile_completeness,
        }
    
    @staticmethod
    def _calculate_streak(user) -> int:
        """Calculate current activity streak."""
        today = timezone.now().date()
        streak = 0
        current_date = today
        
        while True:
            if MetricsService._has_any_activity_on_date(user, current_date):
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        return streak


class CareerAnalyticsService:
    """Service for career analytics."""
    
    @staticmethod
    def get_or_create_career_analytics(user, career_path=None):
        """Get or create career analytics for user."""
        from apps.analytics.models import CareerAnalytics
        
        analytics, created = CareerAnalytics.objects.get_or_create(
            user=user,
            career_path=career_path
        )
        
        if created:
            CareerAnalyticsService.refresh_analytics(analytics)
        
        return analytics
    
    @staticmethod
    def refresh_analytics(analytics):
        """Refresh career analytics."""
        user = analytics.user
        
        # Calculate skills progress
        skills_data = CareerAnalyticsService._analyze_skills(user)
        analytics.total_skills = skills_data["total"]
        analytics.acquired_skills = skills_data["acquired"]
        analytics.in_progress_skills = skills_data["in_progress"]
        analytics.missing_skills = skills_data["missing"]
        analytics.strong_skills = skills_data["strong"]
        analytics.skills_progress = skills_data["progress"]
        
        # Calculate overall progress
        analytics.overall_progress = CareerAnalyticsService._calculate_overall_progress(
            skills_progress=float(analytics.skills_progress),
            experience_progress=float(analytics.experience_progress),
            education_progress=float(analytics.education_progress)
        )
        
        # Generate next steps
        analytics.next_steps = CareerAnalyticsService._generate_next_steps(
            analytics
        )
        
        # Save progress history
        history = analytics.progress_history or []
        history.append({
            "date": timezone.now().date().isoformat(),
            "overall": float(analytics.overall_progress),
            "skills": float(analytics.skills_progress),
        })
        # Keep last 90 days
        analytics.progress_history = history[-90:]
        
        analytics.save()
        return analytics
    
    @staticmethod
    def _analyze_skills(user) -> dict:
        """Analyze user's skills."""
        from apps.profile.models import UserSkill
        
        skills = UserSkill.objects.filter(user=user).select_related("skill")
        
        strong = []
        in_progress = []
        
        for user_skill in skills:
            if user_skill.proficiency_level in ["advanced", "expert"]:
                strong.append(user_skill.skill.name)
            elif user_skill.proficiency_level in ["beginner", "intermediate"]:
                in_progress.append(user_skill.skill.name)
        
        total = skills.count()
        acquired = len(strong)
        
        return {
            "total": total,
            "acquired": acquired,
            "in_progress": len(in_progress),
            "missing": [],  # Would require career path skills comparison
            "strong": strong[:10],
            "progress": Decimal(acquired / total * 100) if total else Decimal(0)
        }
    
    @staticmethod
    def _calculate_overall_progress(
        skills_progress: float,
        experience_progress: float,
        education_progress: float
    ) -> Decimal:
        """Calculate weighted overall progress."""
        weights = {
            "skills": 0.4,
            "experience": 0.4,
            "education": 0.2
        }
        
        return Decimal(
            skills_progress * weights["skills"] +
            experience_progress * weights["experience"] +
            education_progress * weights["education"]
        )
    
    @staticmethod
    def _generate_next_steps(analytics) -> list:
        """Generate recommended next steps."""
        steps = []
        
        if analytics.skills_progress < 50:
            steps.append({
                "type": "skills",
                "title": "Develop key skills",
                "description": "Focus on acquiring skills needed for your target career.",
                "priority": "high"
            })
        
        if len(analytics.missing_skills) > 0:
            steps.append({
                "type": "learning",
                "title": f"Learn {analytics.missing_skills[0]}",
                "description": "This skill is commonly required for your target role.",
                "priority": "medium"
            })
        
        return steps[:5]


class LearningAnalyticsService:
    """Service for learning analytics."""
    
    @staticmethod
    def get_or_create_learning_analytics(user):
        """Get or create learning analytics."""
        from apps.analytics.models import LearningAnalytics
        
        analytics, created = LearningAnalytics.objects.get_or_create(user=user)
        
        if created:
            LearningAnalyticsService.refresh_analytics(analytics)
        
        return analytics
    
    @staticmethod
    def refresh_analytics(analytics):
        """Refresh learning analytics."""
        from apps.learning.models import UserLearningPathEnrollment, UserResourceProgress
        
        user = analytics.user
        
        # Calculate total learning time
        progress_records = UserResourceProgress.objects.filter(user=user)
        enrollments = UserLearningPathEnrollment.objects.filter(user=user)
        
        tracked_minutes = progress_records.aggregate(total=Sum("time_spent_minutes"))["total"] or 0
        enrollment_minutes = enrollments.aggregate(total=Sum("total_time_spent_minutes"))["total"] or 0
        completed_duration_minutes = progress_records.filter(status="completed").aggregate(
            total=Sum("resource__duration_minutes")
        )["total"] or 0

        effective_minutes = tracked_minutes or max(enrollment_minutes, completed_duration_minutes, 0)

        analytics.total_learning_time_hours = Decimal(effective_minutes / 60)
        analytics.total_resources_completed = progress_records.filter(
            status="completed"
        ).count()
        analytics.total_paths_started = enrollments.exclude(status="dropped").count()
        analytics.total_paths_completed = enrollments.filter(status="completed").count()

        if analytics.total_paths_started > 0:
            analytics.completion_rate = Decimal(
                analytics.total_paths_completed / analytics.total_paths_started * 100
            )
        else:
            analytics.completion_rate = Decimal(0)

        avg_session = progress_records.filter(
            time_spent_minutes__gt=0
        ).aggregate(avg=Avg("time_spent_minutes"))["avg"] or 0
        if not avg_session:
            avg_session = progress_records.filter(status="completed").aggregate(
                avg=Avg("resource__duration_minutes")
            )["avg"] or 0
        analytics.average_session_length_minutes = int(round(avg_session))

        completed_skills = set()
        for record in progress_records.filter(status="completed").select_related("resource"):
            completed_skills.update(getattr(record.resource, "skills", []) or [])
        analytics.skills_acquired = sorted(completed_skills)[:50]
        
        # Calculate streak
        LearningAnalyticsService._update_streak(analytics)
        
        # Calculate category progress
        analytics.category_progress = LearningAnalyticsService._get_category_progress(user)
        
        analytics.save()
        return analytics
    
    @staticmethod
    def _update_streak(analytics):
        """Update learning streak."""
        from apps.analytics.models import UserMetrics
        from apps.learning.models import UserCheckpointAttempt, UserLearningPathEnrollment, UserResourceProgress
        
        today = timezone.now().date()
        current_date = today
        streak = 0
        
        while True:
            has_learning = UserMetrics.objects.filter(
                user=analytics.user,
                date=current_date,
            ).filter(
                models.Q(learning_time_minutes__gt=0) |
                models.Q(resources_completed__gt=0)
            ).exists()

            if not has_learning:
                start_dt = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.min.time()))
                end_dt = start_dt + timedelta(days=1)

                has_learning = (
                    UserResourceProgress.objects.filter(
                        user=analytics.user,
                    ).filter(
                        models.Q(updated_at__gte=start_dt, updated_at__lt=end_dt)
                        | models.Q(completed_at__gte=start_dt, completed_at__lt=end_dt)
                        | models.Q(started_at__gte=start_dt, started_at__lt=end_dt)
                    ).exists()
                    or UserCheckpointAttempt.objects.filter(
                        user=analytics.user,
                        created_at__gte=start_dt,
                        created_at__lt=end_dt,
                    ).exists()
                    or UserLearningPathEnrollment.objects.filter(
                        user=analytics.user,
                        last_activity_at__gte=start_dt,
                        last_activity_at__lt=end_dt,
                    ).exists()
                )
            
            if has_learning:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        analytics.current_streak_days = streak
        if streak > analytics.longest_streak_days:
            analytics.longest_streak_days = streak
        analytics.last_activity_date = today if streak > 0 else None
    
    @staticmethod
    def _get_category_progress(user) -> dict:
        """Get progress by category."""
        from apps.learning.models import UserResourceProgress
        
        progress = UserResourceProgress.objects.filter(
            user=user
        ).select_related("resource", "resource__phase", "resource__phase__learning_path")
        
        categories = {}
        for p in progress:
            resource = getattr(p, "resource", None)
            if not resource:
                cat = "general"
            else:
                cat = (
                    getattr(getattr(getattr(resource, "phase", None), "learning_path", None), "category", "")
                    or getattr(resource, "resource_type", "")
                    or "general"
                )
            if cat not in categories:
                categories[cat] = {"completed": 0, "total": 0}
            categories[cat]["total"] += 1
            if p.status == "completed":
                categories[cat]["completed"] += 1
        
        return {
            cat: round(
                data["completed"] / data["total"] * 100
            ) if data["total"] else 0
            for cat, data in categories.items()
        }


class JobSearchAnalyticsService:
    """Service for job search analytics."""
    
    @staticmethod
    def get_or_create_job_analytics(user):
        """Get or create job search analytics."""
        from apps.analytics.models import JobSearchAnalytics
        
        analytics, created = JobSearchAnalytics.objects.get_or_create(user=user)
        
        if created:
            JobSearchAnalyticsService.refresh_analytics(analytics)
        
        return analytics
    
    @staticmethod
    def refresh_analytics(analytics):
        """Refresh job search analytics."""
        from apps.jobs.models import JobApplication, SavedJob
        
        user = analytics.user
        
        # Application counts
        applications = JobApplication.objects.filter(
            user=user,
            is_deleted=False
        )
        
        analytics.total_applications = applications.count()
        
        # This month
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        analytics.applications_this_month = applications.filter(
            submitted_at__gte=month_start
        ).count()
        
        # This week
        week_start = timezone.now() - timedelta(days=7)
        analytics.applications_this_week = applications.filter(
            submitted_at__gte=week_start
        ).count()
        
        # Status breakdown
        status_counts = applications.values("status").annotate(
            count=Count("id")
        )
        
        for item in status_counts:
            if item["status"] == "applied":
                analytics.pending_applications = item["count"]
            elif item["status"] == "reviewed":
                analytics.reviewed_applications = item["count"]
            elif item["status"] == "interview":
                analytics.interviews_scheduled = item["count"]
            elif item["status"] == "offer":
                analytics.offers_received = item["count"]
            elif item["status"] == "rejected":
                analytics.rejections = item["count"]
        
        # Calculate rates
        total = analytics.total_applications or 1
        analytics.response_rate = Decimal(
            (analytics.reviewed_applications + analytics.interviews_scheduled + 
             analytics.offers_received) / total * 100
        )
        analytics.interview_rate = Decimal(
            (analytics.interviews_scheduled + analytics.offers_received) / total * 100
        )
        analytics.offer_rate = Decimal(
            analytics.offers_received / total * 100
        )
        
        # Views and saves
        analytics.total_jobs_viewed = 0  # JobView model not implemented yet
        analytics.total_jobs_saved = SavedJob.objects.filter(
            user=user
        ).count()
        
        analytics.save()
        return analytics


class InterviewAnalyticsService:
    """Service for interview analytics."""
    
    @staticmethod
    def get_or_create_interview_analytics(user):
        """Get or create interview analytics."""
        from apps.analytics.models import InterviewAnalytics
        
        analytics, created = InterviewAnalytics.objects.get_or_create(user=user)
        
        if created:
            InterviewAnalyticsService.refresh_analytics(analytics)
        
        return analytics
    
    @staticmethod
    def refresh_analytics(analytics):
        """Refresh interview analytics."""
        from apps.interview.models import InterviewResponse, InterviewSchedule, InterviewSession
        
        user = analytics.user
        
        # Session stats
        sessions = InterviewSession.objects.filter(
            user=user,
            is_deleted=False,
        )
        
        analytics.total_practice_sessions = sessions.count()
        
        # Total time
        total_duration = sessions.aggregate(
            total=Sum("duration_minutes")
        )["total"] or 0
        response_time_seconds = InterviewResponse.objects.filter(
            session__user=user,
            session__is_deleted=False,
            completed_at__isnull=False,
        ).aggregate(total=Sum("time_taken_seconds"))["total"] or 0
        effective_total_minutes = max(total_duration, response_time_seconds / 60)
        analytics.total_practice_time_hours = Decimal(effective_total_minutes / 60)
        
        # Response stats
        responses = InterviewResponse.objects.filter(
            session__user=user,
            session__is_deleted=False,
            ai_score__isnull=False
        )
        
        analytics.total_questions_answered = responses.count()
        
        scores = responses.aggregate(
            avg=Avg("ai_score"),
            best=models.Max("ai_score")
        )
        analytics.average_score = scores["avg"]
        analytics.best_score = scores["best"]
        
        # Scores by type
        type_scores = responses.values(
            "question__question_type"
        ).annotate(avg=Avg("ai_score"))
        
        analytics.scores_by_type = {
            item["question__question_type"]: float(item["avg"])
            for item in type_scores if item["question__question_type"]
        }
        
        # Identify strengths and weaknesses
        sorted_types = sorted(
            analytics.scores_by_type.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        analytics.strongest_areas = [t[0] for t in sorted_types[:3]]
        analytics.weakest_areas = [t[0] for t in sorted_types[-3:]]

        real_interviews = InterviewSchedule.objects.filter(
            user=user,
            is_deleted=False,
            status="completed",
        )
        analytics.total_real_interviews = real_interviews.count()
        
        analytics.save()
        return analytics
