"""
Jobs URL Configuration
======================
URL patterns for job-related endpoints.
"""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.jobs.views import (
    JobSearchView,
    SavedJobViewSet,
    ApplicationViewSet,
    TrackExternalApplicationView,
)

app_name = "jobs"

# Create router and register viewsets
router = SimpleRouter()
router.register(r"saved", SavedJobViewSet, basename="saved")
router.register(r"applications", ApplicationViewSet, basename="application")

urlpatterns = [
    # Search
    path("search/", JobSearchView.as_view(), name="search"),

    # Track external applications (LinkedIn, Indeed, Glassdoor, etc.)
    path("applications/track/", TrackExternalApplicationView.as_view(), name="track-application"),
    
    # ViewSet routes
    path("", include(router.urls)),
]
