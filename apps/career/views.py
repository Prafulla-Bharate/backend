"""
Career Views
============
API views for active career prediction endpoints.
"""

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.career.models import CareerPrediction
from apps.career.serializers import (
    CareerPredictionSerializer,
    CareerPredictionRequestSerializer,
    transform_prediction_for_frontend,
)
from apps.career.services import CareerPredictionService

logger = logging.getLogger(__name__)


class CareerPredictionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing and acting on career predictions."""

    permission_classes = [IsAuthenticated]
    serializer_class = CareerPredictionSerializer
    ordering = "-created_at"

    def get_queryset(self):
        """Return predictions for current user."""
        return CareerPrediction.objects.filter(
            user=self.request.user,
            deleted_at__isnull=True,
        ).order_by("-created_at")

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Accept a career prediction and optionally store feedback."""
        try:
            prediction = self.get_object()
        except CareerPrediction.DoesNotExist:
            return Response({"detail": "Prediction not found."}, status=status.HTTP_404_NOT_FOUND)

        feedback = request.data.get("feedback", "")
        accepted_title = request.data.get("accepted_career_title", "").strip()
        if not accepted_title and prediction.recommended_careers:
            first = prediction.recommended_careers[0]
            accepted_title = first.get("title", "")

        prediction.user_feedback = feedback
        prediction.is_accepted = True
        prediction.accepted_career_title = accepted_title
        prediction.save(update_fields=["user_feedback", "is_accepted", "accepted_career_title"])

        try:
            prefs = request.user.preferences
            prefs.accepted_career_title = accepted_title
            prefs.save(update_fields=["accepted_career_title"])
        except Exception as exc:
            logger.warning("Could not update user preferences with accepted career: %s", exc)

        return Response(
            {
                "detail": "Career prediction accepted.",
                "id": str(prediction.id),
                "accepted_career_title": accepted_title,
            }
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a career prediction with optional feedback."""
        try:
            prediction = self.get_object()
        except CareerPrediction.DoesNotExist:
            return Response({"detail": "Prediction not found."}, status=status.HTTP_404_NOT_FOUND)

        feedback = request.data.get("feedback", "")
        prediction.user_feedback = feedback
        prediction.is_accepted = False
        prediction.save(update_fields=["user_feedback", "is_accepted"])

        return Response({"detail": "Feedback recorded."})

    @action(detail=True, methods=["get"])
    def insights(self, request, pk=None):
        """Get detailed insights for a specific prediction."""
        try:
            prediction = self.get_object()
        except CareerPrediction.DoesNotExist:
            return Response({"detail": "Prediction not found."}, status=status.HTTP_404_NOT_FOUND)

        career_title = request.query_params.get("career_title", "").strip()
        all_careers = prediction.recommended_careers or []

        if career_title:
            recommended = next(
                (c for c in all_careers if (c.get("title") or "").lower() == career_title.lower()),
                all_careers[0] if all_careers else {},
            )
        else:
            recommended = all_careers[0] if all_careers else {}

        salary = recommended.get("salary_range", {})
        if not isinstance(salary, dict):
            salary = {}
        sal_min = float(salary.get("min", 0) or 0)
        sal_max = float(salary.get("max", 0) or 0)

        sp = recommended.get("salary_progression", {})
        if not isinstance(sp, dict):
            sp = {}
        sp_entry = float(sp.get("entry", sal_min or 400000))
        sp_mid = float(sp.get("mid", (sal_min + sal_max) / 2 if sal_max else sal_min * 1.5 or 900000))
        sp_senior = float(sp.get("senior", sal_max or sp_entry * 3 or 2000000))
        sp_growth_pct = int(((sp_senior - sp_entry) / sp_entry * 100)) if sp_entry else 300

        raw_ms = recommended.get("match_score", 0) or 0
        match_pct = int(float(raw_ms) * 100) if float(raw_ms) <= 1.0 else int(float(raw_ms))

        cpr = recommended.get("career_path_roles", {})
        if not isinstance(cpr, dict):
            cpr = {}
        flat_path = recommended.get("career_path", [])
        n = len(flat_path)
        entry_roles = cpr.get("entry_roles", flat_path[: max(1, n // 3)])
        mid_roles = cpr.get("mid_roles", flat_path[max(1, n // 3) : max(2, 2 * n // 3)])
        senior_roles = cpr.get("senior_roles", flat_path[max(2, 2 * n // 3) :])
        time_to_senior = cpr.get("time_to_senior", "5-8 years")

        user_profile = prediction.input_data.get("user_profile", {}) if prediction.input_data else {}
        matching_skills = recommended.get("skills_matched") or user_profile.get("skills", [])[:5]

        matching_experience = []
        current_role = user_profile.get("current_role")
        experience_years = user_profile.get("experience_years", 0)
        industry = user_profile.get("industry")
        if current_role:
            entry = current_role
            if experience_years:
                entry += " (%s yrs)" % experience_years
            matching_experience.append(entry)
        if industry and industry != current_role:
            matching_experience.append("%s industry background" % industry)
        if not matching_experience and experience_years:
            matching_experience.append("%s years of professional experience" % experience_years)

        matching_education = []
        for edu in user_profile.get("education", []):
            degree = edu.get("degree_name") or edu.get("degree_type", "")
            field = edu.get("field_of_study", "")
            institution = edu.get("institution_name", "")
            parts = [p for p in [degree, field] if p]
            label = " in ".join(parts) if len(parts) == 2 else (parts[0] if parts else "")
            if institution:
                label += " - %s" % institution if label else institution
            if label:
                matching_education.append(label)

        insights = {
            "profile_match": {
                "matching_skills": matching_skills,
                "matching_experience": matching_experience,
                "matching_education": matching_education,
                "match_percentage": match_pct,
            },
            "market_data": {
                "job_openings": recommended.get("job_openings", 0) or 0,
                "avg_salary": int(sal_max or sal_min or sp_mid),
                "salary_range": {"min": int(sal_min), "max": int(sal_max)},
                "top_companies": recommended.get("top_companies", []),
                "top_locations": recommended.get("top_locations", []),
                "demand_trend": recommended.get("demand_trend", "rising"),
            },
            "trends": {
                "current_trend": (recommended.get("trends") or {}).get("current", ""),
                "future_outlook": (recommended.get("trends") or {}).get("future", ""),
                "emerging_technologies": (recommended.get("trends") or {}).get("technologies", []),
                "industry_growth": recommended.get("industry_growth", 0) or 0,
            },
            "career_path": {
                "entry_roles": entry_roles,
                "mid_roles": mid_roles,
                "senior_roles": senior_roles,
                "time_to_senior": time_to_senior,
            },
            "salary_progression": {
                "entry": int(sp_entry),
                "mid": int(sp_mid),
                "senior": int(sp_senior),
                "growth_percentage": sp_growth_pct,
            },
            "success_factors": recommended.get("success_factors", []),
            "challenges": recommended.get("challenges", []),
            "day_in_life": recommended.get("day_in_life", ""),
        }

        return Response(insights)


class RequestPredictionView(APIView):
    """Request a new career prediction."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create new prediction request with detailed logging."""
        logger.info("[Prediction] Incoming request data from frontend: %s", request.data)
        serializer = CareerPredictionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logger.info("[Prediction] Validated data for prediction: %s", serializer.validated_data)
        prediction = CareerPredictionService.request_prediction(
            user=request.user,
            **serializer.validated_data,
        )
        frontend_data = transform_prediction_for_frontend(prediction)
        logger.info("[Prediction] Data generated by backend for frontend: %s", frontend_data)
        return Response(frontend_data, status=status.HTTP_201_CREATED)


class LatestPredictionView(APIView):
    """Get latest career prediction."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get most recent prediction with logging."""
        prediction = CareerPredictionService.get_latest_prediction(request.user)
        if not prediction:
            logger.info("[Prediction] No prediction found for user %s", request.user)
            return Response(
                {"detail": "No prediction found. Request one first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        frontend_data = transform_prediction_for_frontend(prediction)
        logger.info(
            "[Prediction] Latest prediction sent to frontend: prediction_id=%s status=%s",
            frontend_data.get("prediction_id"),
            frontend_data.get("status"),
        )
        return Response(frontend_data)
