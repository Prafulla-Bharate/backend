"""
Interview URL Configuration
============================
URL patterns for interview-related endpoints.
"""

from django.urls import path

from apps.interview.views import (
    SessionViewSet,
    ResponseView,
    UpcomingSchedulesView,
    FeaturedTipsView,
    PracticeStatsView,
    InterviewRoundDetailView,
    InterviewRoundSubmitView,
    InterviewRoundFeedbackView,
    ConfidenceMetricsView,
)

app_name = "interview"

urlpatterns = [
    # Session lifecycle
    path("sessions/", SessionViewSet.as_view({"get": "list", "post": "create"}), name="session-list"),
    path("sessions/<uuid:pk>/start/", SessionViewSet.as_view({"post": "start"}), name="session-start"),
    path("sessions/<uuid:pk>/complete/", SessionViewSet.as_view({"post": "complete"}), name="session-complete"),
    path("sessions/<uuid:pk>/next_question/", SessionViewSet.as_view({"get": "next_question"}), name="session-next-question"),

    # Stats
    path("stats/", PracticeStatsView.as_view(), name="stats"),
    path("confidence-metrics/", ConfidenceMetricsView.as_view(), name="confidence-metrics"),

    # Response submit
    path(
        "responses/<uuid:response_id>/",
        ResponseView.as_view(),
        name="response-detail"
    ),

    # Schedules & tips
    path("schedules/upcoming/", UpcomingSchedulesView.as_view(), name="schedule-upcoming"),
    path("tips/featured/", FeaturedTipsView.as_view(), name="tips-featured"),

    # Interview rounds
    path("rounds/<uuid:round_id>/", InterviewRoundDetailView.as_view(), name="round-detail"),
    path("rounds/<uuid:round_id>/submit/", InterviewRoundSubmitView.as_view(), name="round-submit"),
    path("rounds/<uuid:round_id>/feedback/", InterviewRoundFeedbackView.as_view(), name="round-feedback"),
]
