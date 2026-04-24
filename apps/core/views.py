"""
Core Views
==========
System health and AI chat endpoints.
"""

import logging
from typing import Any, Dict
from uuid import uuid4

from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from services.ai.prompts import AIPromptsService

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """Health check endpoint for monitoring."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request) -> Response:
        health_status = self._check_health()
        if health_status["healthy"]:
            return Response(health_status, status=status.HTTP_200_OK)
        return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    def _check_health(self) -> Dict[str, Any]:
        checks: Dict[str, Dict[str, Any]] = {}
        overall_healthy = True

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks["database"] = {"status": "healthy"}
        except Exception as exc:
            checks["database"] = {"status": "unhealthy", "error": str(exc)}
            overall_healthy = False

        try:
            cache.set("health_check", "ok", timeout=10)
            if cache.get("health_check") == "ok":
                checks["cache"] = {"status": "healthy"}
            else:
                checks["cache"] = {"status": "unhealthy", "error": "Cache read failed"}
        except Exception as exc:
            checks["cache"] = {"status": "unhealthy", "error": str(exc)}

        return {
            "healthy": overall_healthy,
            "timestamp": timezone.now().isoformat(),
            "checks": checks,
        }


class ChatView(APIView):
    """AI chat endpoint powered by Gemini prompt service."""

    permission_classes = [IsAuthenticated]
    CONVERSATION_TTL = 3600
    MAX_HISTORY_LENGTH = 20

    def post(self, request) -> Response:
        message = request.data.get("message", "").strip()
        if not message:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        conversation_id = request.data.get("conversation_id") or str(uuid4())
        context = request.data.get("context", {})
        user_context = self._get_user_context(request.user)

        cache_key = f"chat:{request.user.id}:{conversation_id}"
        conversation_history = cache.get(cache_key, [])
        full_context = {**context, **user_context}

        try:
            ai_prompts = AIPromptsService()
            response_data = ai_prompts.chat_response(
                message=message,
                conversation_history=conversation_history,
                user_context=full_context,
            )

            if response_data and "error" not in response_data:
                ai_response = response_data.get("response", response_data.get("message", ""))
                suggestions = response_data.get("suggestions", [])
                actions = response_data.get("actions", [])
                related_topics = response_data.get("related_topics", [])
            else:
                ai_response = (
                    "I'm here to help you with your career journey! "
                    "You can ask me about career paths, resume tips, interview preparation, "
                    "skill development, and job search strategies."
                )
                suggestions = [
                    "What skills should I develop?",
                    "How can I improve my resume?",
                    "Help me prepare for interviews",
                ]
                actions = []
                related_topics = []

            conversation_history.append(
                {
                    "role": "user",
                    "content": message,
                    "timestamp": timezone.now().isoformat(),
                }
            )
            conversation_history.append(
                {
                    "role": "assistant",
                    "content": ai_response,
                    "timestamp": timezone.now().isoformat(),
                }
            )

            if len(conversation_history) > self.MAX_HISTORY_LENGTH * 2:
                conversation_history = conversation_history[-(self.MAX_HISTORY_LENGTH * 2):]

            cache.set(cache_key, conversation_history, self.CONVERSATION_TTL)

            return Response(
                {
                    "success": True,
                    "data": {
                        "message": ai_response,
                        "conversation_id": conversation_id,
                        "suggestions": suggestions,
                        "actions": actions,
                        "related_topics": related_topics,
                        "timestamp": timezone.now().isoformat(),
                    },
                }
            )
        except Exception as exc:
            logger.error("Chat error: %s", exc, exc_info=True)
            return Response(
                {
                    "success": False,
                    "error": "Failed to process message",
                    "message": "I'm having trouble responding right now. Please try again.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_user_context(self, user) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "user_name": user.first_name or user.email,
            "email": user.email,
            "location": getattr(user, "location", "") or "",
            "experience_level": getattr(user, "experience_level", "") or "",
        }

        try:
            from apps.profile.models import UserExperience, UserSkill

            skills = list(
                UserSkill.objects.filter(user=user)
                .select_related("skill")
                .values_list("skill__name", flat=True)[:20]
            )
            context["skills"] = [skill for skill in skills if skill]

            current_exp = UserExperience.objects.filter(user=user, is_current=True).first()
            if current_exp:
                context["current_role"] = current_exp.job_title
                context["current_company"] = current_exp.company_name
        except Exception as exc:
            logger.warning("Failed to build chat user context: %s", exc)

        return context
