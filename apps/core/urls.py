"""
Core URL Configuration
======================
Health check, system status, and AI chat endpoints.
"""

from django.urls import path

from apps.core.views import (
    HealthCheckView,
    ChatView,
)

urlpatterns = [
    # Health
    path("", HealthCheckView.as_view(), name="health-check"),
    
    # AI Chat endpoint
    path("chat/", ChatView.as_view(), name="chat"),
]
