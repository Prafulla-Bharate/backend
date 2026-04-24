"""
Analytics URL Configuration
============================
URL patterns for actively used analytics endpoints.
"""

from django.urls import path

from apps.analytics.views import (
    UserDashboardView,
    LogActivityView,
    CareerAnalyticsView,
    LearningAnalyticsView,
    JobSearchAnalyticsView,
    InterviewAnalyticsView,
)

app_name = "analytics"

urlpatterns = [
    # User dashboard
    path("dashboard/", UserDashboardView.as_view(), name="dashboard"),

    # Log activity
    path("log/", LogActivityView.as_view(), name="log-activity"),

    # Specific analytics
    path("career/", CareerAnalyticsView.as_view(), name="career"),
    path("learning/", LearningAnalyticsView.as_view(), name="learning"),
    path("job-search/", JobSearchAnalyticsView.as_view(), name="job-search"),
    path("interview/", InterviewAnalyticsView.as_view(), name="interview"),
]
