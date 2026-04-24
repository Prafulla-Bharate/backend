"""
CareerAI URL Configuration
==========================
Main URL routing for the CareerAI API.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# =============================================================================
# API URL Patterns
# =============================================================================
api_v1_patterns = [
    path("auth/", include("apps.users.urls")),
    path("profile/", include("apps.profile.urls")),
    path("career/", include("apps.career.urls")),
    path("learning/", include("apps.learning.urls")),
    path("jobs/", include("apps.jobs.urls")),
    path("interview/", include("apps.interview.urls")),
    path("analytics/", include("apps.analytics.urls")),
]

# =============================================================================
# Main URL Patterns
# =============================================================================
urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    
    # API v1
    path("api/", include(api_v1_patterns)),
    
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    
    # Health check (for Docker/Kubernetes)
    path("health/", include("apps.core.urls")),
    path("api/health/", include("apps.core.urls")),  # Duplicate for Docker healthcheck
]

# =============================================================================
# Debug Toolbar (Development Only)
# =============================================================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    try:
        import debug_toolbar
        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# =============================================================================
# Admin Site Configuration
# =============================================================================
admin.site.site_header = "CareerAI Administration"
admin.site.site_title = "CareerAI Admin Portal"
admin.site.index_title = "Welcome to CareerAI Admin Portal"
