"""
Profile URL Configuration
========================
URL patterns for profile-related endpoints.
"""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.profile.views import (
    ProfileView,
    ProfilePictureView,
    ResumeParsePreviewView,
    ProfileCompletenessView,
    UserEducationViewSet,
    UserExperienceViewSet,
    UserCertificationViewSet,
    UserProjectViewSet,
    UserLanguageViewSet,
    UserSocialLinkViewSet,
)

app_name = "profile"

# Create router and register viewsets
router = SimpleRouter()
router.register(r"education", UserEducationViewSet, basename="education")
router.register(r"experience", UserExperienceViewSet, basename="experience")
router.register(r"certifications", UserCertificationViewSet, basename="certifications")
router.register(r"projects", UserProjectViewSet, basename="projects")
router.register(r"languages", UserLanguageViewSet, basename="languages")
router.register(r"social-links", UserSocialLinkViewSet, basename="social-links")

urlpatterns = [
    # Main profile endpoints
    path("", ProfileView.as_view(), name="profile"),
    path("picture/", ProfilePictureView.as_view(), name="profile-picture"),
    path("parse-resume/", ResumeParsePreviewView.as_view(), name="parse-resume"),
    
    # Profile completeness
    path("completeness/", ProfileCompletenessView.as_view(), name="completeness"),
    
    # ViewSet routes
    path("", include(router.urls)),
]
