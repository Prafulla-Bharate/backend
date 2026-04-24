"""
Career URL Configuration
========================
URL patterns for career-related endpoints.
"""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.career.views import (
    CareerPredictionViewSet,
    RequestPredictionView,
    LatestPredictionView,
)

app_name = "career"

# Create router and register viewsets
router = SimpleRouter()
router.register(r"predictions", CareerPredictionViewSet, basename="prediction")

urlpatterns = [
    # Prediction endpoints
    path("predict/", RequestPredictionView.as_view(), name="predict"),  # Alias for frontend
    path(
        "predictions/latest/",
        LatestPredictionView.as_view(),
        name="latest-prediction"
    ),

    # ViewSet routes
    path("", include(router.urls)),
]
