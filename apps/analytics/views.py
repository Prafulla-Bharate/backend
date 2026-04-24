"""
Analytics Views
===============
API views for analytics endpoints.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.serializers import (
    UserActivitySerializer,
    CreateActivitySerializer,
    CareerAnalyticsSerializer,
    LearningAnalyticsSerializer,
    JobSearchAnalyticsSerializer,
    InterviewAnalyticsSerializer,
    UserDashboardAnalyticsSerializer,
)
from apps.analytics.services import (
    ActivityService,
    MetricsService,
    CareerAnalyticsService,
    LearningAnalyticsService,
    JobSearchAnalyticsService,
    InterviewAnalyticsService,
)


# ============================================================================
# User Analytics Views
# ============================================================================

class UserDashboardView(APIView):
    """Get comprehensive analytics dashboard for user."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get dashboard analytics."""
        user = request.user
        
        # Get all analytics — always refresh so counts are never stale
        metrics_summary = MetricsService.get_metrics_summary(user)

        career = CareerAnalyticsService.get_or_create_career_analytics(user)
        CareerAnalyticsService.refresh_analytics(career)

        learning = LearningAnalyticsService.get_or_create_learning_analytics(user)
        LearningAnalyticsService.refresh_analytics(learning)

        job_search = JobSearchAnalyticsService.get_or_create_job_analytics(user)
        JobSearchAnalyticsService.refresh_analytics(job_search)

        interview = InterviewAnalyticsService.get_or_create_interview_analytics(user)
        InterviewAnalyticsService.refresh_analytics(interview)

        recent_activities = ActivityService.get_user_activities(user, days=84, limit=500)
        
        data = {
            "metrics_summary": metrics_summary,
            "career_analytics": career,
            "learning_analytics": learning,
            "job_search_analytics": job_search,
            "interview_analytics": interview,
            "recent_activities": recent_activities,
        }
        
        serializer = UserDashboardAnalyticsSerializer(data)
        return Response(serializer.data)


class LogActivityView(APIView):
    """Log a user activity."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Log activity."""
        serializer = CreateActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        activity = ActivityService.log_activity(
            user=request.user,
            request=request,
            **serializer.validated_data
        )
        
        return Response(
            UserActivitySerializer(activity).data,
            status=status.HTTP_201_CREATED
        )


# ============================================================================
# Career Analytics Views
# ============================================================================

class CareerAnalyticsView(APIView):
    """View for career analytics."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get career analytics."""
        career_path_id = request.query_params.get("career_path")
        
        career_path = None
        if career_path_id:
            from apps.career.models import CareerPath
            try:
                career_path = CareerPath.objects.get(id=career_path_id)
            except CareerPath.DoesNotExist:
                pass
        
        analytics = CareerAnalyticsService.get_or_create_career_analytics(
            request.user, career_path
        )
        CareerAnalyticsService.refresh_analytics(analytics)
        serializer = CareerAnalyticsSerializer(analytics)
        return Response(serializer.data)


# ============================================================================
# Learning Analytics Views
# ============================================================================

class LearningAnalyticsView(APIView):
    """View for learning analytics."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get learning analytics."""
        analytics = LearningAnalyticsService.get_or_create_learning_analytics(
            request.user
        )
        LearningAnalyticsService.refresh_analytics(analytics)
        serializer = LearningAnalyticsSerializer(analytics)
        return Response(serializer.data)


# ============================================================================
# Job Search Analytics Views
# ============================================================================

class JobSearchAnalyticsView(APIView):
    """View for job search analytics."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get job search analytics."""
        analytics = JobSearchAnalyticsService.get_or_create_job_analytics(
            request.user
        )
        JobSearchAnalyticsService.refresh_analytics(analytics)
        serializer = JobSearchAnalyticsSerializer(analytics)
        return Response(serializer.data)


# ============================================================================
# Interview Analytics Views
# ============================================================================

class InterviewAnalyticsView(APIView):
    """View for interview analytics."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get interview analytics."""
        analytics = InterviewAnalyticsService.get_or_create_interview_analytics(
            request.user
        )
        InterviewAnalyticsService.refresh_analytics(analytics)
        serializer = InterviewAnalyticsSerializer(analytics)
        return Response(serializer.data)
