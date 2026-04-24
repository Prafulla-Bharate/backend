"""
Learning URL Configuration
==========================
URL patterns for learning-related endpoints.
"""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.learning.views import (
    GenerateLearningPathView,
    EnrollmentViewSet,
    ResourceProgressView,
    BookmarkedResourcesView,
    SubmitCheckpointView,
    RecommendationsView,
    LearningDashboardView,
    LearningStatsView,
    PhaseDetailView,
    StartRetentionQuizView,
    SubmitRetentionQuizView,
    # Adaptive / new views
    PhaseInjectionsView,
    CompleteInjectionView,
    ProjectSubmitView,
    ProjectListView,
    CertificateSubmitView,
    CertificateListView,
    PendingRefreshersView,
    UserStreakView,
    ComprehensiveStatsView,
)

app_name = "learning"

router = SimpleRouter()
router.register(r"enrollments", EnrollmentViewSet, basename="enrollment")

urlpatterns = [
    # Dashboard & Stats
    path("dashboard/", LearningDashboardView.as_view(), name="dashboard"),
    path("stats/", LearningStatsView.as_view(), name="stats"),
    path("stats/comprehensive/", ComprehensiveStatsView.as_view(), name="stats-comprehensive"),

    # Generate personalized path
    path("generate/", GenerateLearningPathView.as_view(), name="generate"),

    # Resource progress
    path(
        "resources/<uuid:resource_id>/progress/",
        ResourceProgressView.as_view(),
        name="resource-progress",
    ),

    # Bookmarks
    path("bookmarks/", BookmarkedResourcesView.as_view(), name="bookmarks"),

    # Checkpoints
    path(
        "checkpoints/<uuid:checkpoint_id>/submit/",
        SubmitCheckpointView.as_view(),
        name="checkpoint-submit",
    ),

    # Recommendations
    path("recommendations/", RecommendationsView.as_view(), name="recommendations"),

    # Phase detail (enriched: resources + YouTube + external links + certs + capstone)
    path("phases/<uuid:phase_id>/detail/", PhaseDetailView.as_view(), name="phase-detail"),
    path("phases/<uuid:phase_id>/retention-quiz/start/", StartRetentionQuizView.as_view(), name="retention-quiz-start"),
    path("phases/<uuid:phase_id>/retention-quiz/submit/", SubmitRetentionQuizView.as_view(), name="retention-quiz-submit"),

    # Adaptive Content — Phase Injections
    path(
        "enrollments/<uuid:enrollment_id>/injections/",
        PhaseInjectionsView.as_view(),
        name="phase-injections",
    ),
    path(
        "injections/<uuid:injection_id>/complete/",
        CompleteInjectionView.as_view(),
        name="complete-injection",
    ),

    # Projects
    path("projects/submit/", ProjectSubmitView.as_view(), name="project-submit"),
    path("projects/", ProjectListView.as_view(), name="project-list"),

    # Certificates
    path("certificates/submit/", CertificateSubmitView.as_view(), name="certificate-submit"),
    path("certificates/", CertificateListView.as_view(), name="certificate-list"),

    # Skill Refreshers
    path("refreshers/", PendingRefreshersView.as_view(), name="refresher-list"),

    # Streak
    path("streak/", UserStreakView.as_view(), name="user-streak"),

    # ViewSet routes
    path("", include(router.urls)),
]
